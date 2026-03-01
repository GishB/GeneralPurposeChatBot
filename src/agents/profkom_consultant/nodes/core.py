import asyncio
import re
from typing import Any

from langchain_core.prompts import ChatPromptTemplate

from agents.profkom_consultant.states import AgentState
from service.logger import LoggerConfigurator

from .base import BaseAgentNodes
from .loop import ThinkTwiceNodes


class UnionAgent(BaseAgentNodes, ThinkTwiceNodes):
    r"""Класс профсоюзного агента.

    Note:
        1. Реализован для сложных ответов с учетом базы знаний профсоюза (RAG);
        2. Можете переписывать вопросы пользователя;
        3. Кеширует вопросы\ответы в каждой из нод;

    """

    def __init__(self, logger: LoggerConfigurator, llms: dict, cache, langfuse_client, chroma_client, **kwargs):
        self.logger = logger
        self.logger.info(f"Initializing {__name__}")
        self.llm = llms.get("default")
        self.logger.info(f"LLM keys {llms.keys()}")

        self.cache = cache
        self.langfuse_client = langfuse_client
        self.chorma_client = chroma_client

        self.HISTORY_LIMIT = kwargs.get("HISTORY_LIMIT", 10)
        self.COLLECTION_NAME = kwargs.get("COLLECTION_NAME", "PRODUCTION_PROFKOM")

        self.logger.info(f"HISTORY_LIMIT: {self.HISTORY_LIMIT}")
        self.logger.info(f"COLLECTION_NAME: {self.COLLECTION_NAME}")

    async def _detect_topics_for_question(self, question: str) -> str:
        """Detects topics based on question.

        Args:
            question: specific user simple question.

        Returns:
            Relevant topic.
        """
        prompt = self.langfuse_client.get_prompt("topic_choose_router").get_langchain_prompt()
        prompt = ChatPromptTemplate.from_template(prompt)
        chain = prompt | self.llm
        response = await chain.ainvoke({"question": question})
        return response.content.strip()

    async def decompose_question(self, state: AgentState) -> None | dict[str, Any] | dict[str, list[Any]]:
        """Декомпозируем предложение пользователя на отдельные задачи.

        Note:
            1. Сложный вопрос пользователя превращается в несколько простых для улучшения ответа агента.
            2. Кешируем вопрос по конкретному пользователю только.

        Example:
            Вопрос: "Привет! Расскажи, пожалуйста, как вступить в профсоюз?"
            Ответ: "Как вступить в профсоюз?; Где находится профсоюзная организация?; Какие документы нужны для вступления в профсоюз?;

        Return:
            Словарь простых вопросов пользователя.
        """
        question = state["text"]
        try:
            cached_result = self.cache.get(meta_info="decompose_question_" + state["user_id"], query=question)
            if cached_result:
                return {"parts": cached_result.get("json").get("parts")}
            else:
                prompt = self.langfuse_client.get_prompt("decompose_question").get_langchain_prompt()
                prompt = ChatPromptTemplate.from_template(prompt)
                chain = prompt | self.llm
                response = await chain.ainvoke(
                    {"user_question": question, "user_history": state.get("user_history", "")}
                )
                response = response.content.strip()

                content = re.search(r"<ЗАДАЧИ.*?>(.*?)</ЗАДАЧИ>", response, re.IGNORECASE | re.DOTALL)
                content = content.group(1) if content else response

                cache_data = {"parts": [p.strip() for p in content.split("<PART>") if p.strip()]}
                self.cache.save(
                    meta_info="decompose_question_" + state["user_id"], query=question, output="", json_data=cache_data
                )
                return cache_data
        except Exception as e:
            print(f"Error at decompose_question: {e}")

    async def answer_parts_async(self, state: AgentState, max_concurrent: int = 8) -> AgentState:
        """Генерируем асинхронные ответы на список вопросов.

        Note:
            Создаем семафор для генерации асинхронных ответов на список простых вопросов из сложного.

        Returns:
            Список простых ответов на глобальный вопрос пользователя.
        """
        state["answers"] = []
        semaphore = asyncio.Semaphore(max_concurrent)

        prompt = self.langfuse_client.get_prompt("query_worker").get_langchain_prompt()
        prompt = ChatPromptTemplate.from_template(prompt)
        # TO DO: CHECK что мы умеем работать с данными RAG
        chain = prompt | self.llm

        async def call_llm(part: str) -> str:
            self.logger.info(f"Calling {part}")
            async with semaphore:
                cached_result = self.cache.get(meta_info="answer_parts_async", query=part)
                if cached_result:
                    return cached_result.get("json").get("answer")
                else:
                    topic = await self._detect_topics_for_question(part)
                    self.logger.info(f"Topic: {topic}")
                    retrived_data = await asyncio.to_thread(
                        self.chorma_client.get_info, query=part, collection_name=self.COLLECTION_NAME, topics=[topic]
                    )
                    html_data = retrived_data.to_html()
                    result = await chain.ainvoke({"text": part, "rag": html_data})
                    cache_data = {"answer": result.content.strip()}
                    self.cache.save(meta_info="answer_parts_async", query=part, output="", json_data=cache_data)
                    return cache_data.get("answer")

        if state.get("parts"):
            tasks = [asyncio.create_task(call_llm(part)) for part in state["parts"]]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            state["answers"] = [str(r) if not isinstance(r, Exception) else f"Error: {r}" for r in results]
        return state

    async def collect_final_answer(self, state: AgentState) -> AgentState:
        """Собираем итоговый ответ на вопрос пользователя.

        Note:
            1. Смотрим на данные из истории вопросов пользователя;
            2. Смотрим на текущие ответы пользователю на предыдущие вопросы;
            3. Смотрим на текущий вопрос пользователя

        Return:
            Итоговый текст ответа пользователю на вопрос.
        """
        question = state["text"]
        if state.get("answers"):
            answers_text = "\n".join(f"{i + 1}. {ans}" for i, ans in enumerate(state["answers"]) if ans)
            prompt = self.langfuse_client.get_prompt("summary_response").get_langchain_prompt()
            prompt = ChatPromptTemplate.from_template(prompt)
            chain = prompt | self.llm
            # TO DO: CHECK что у нас огромный промпт не ломает ответ
            response = await chain.ainvoke(
                {
                    "task_responses": answers_text,
                    "user_history": state.get("user_history", "Нет истории запросов."),
                    "original_question": question,
                    "model_answers": state.get("model_answers", "Нет истории ответов от модели"),
                    "additional_info": state.get(
                        "additional_info", "Нет дополнительной информации по предыдущим ответам."
                    ),
                }
            )
            response = response.content.strip()
            state["final_answer"] = response
        else:
            state["final_answer"] = "Нет данных для итогового ответа."
        return state
