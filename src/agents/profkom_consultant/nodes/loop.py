import re

from langchain_core.prompts import ChatPromptTemplate

from ..states import AgentState, AgentStatus


class ThinkTwiceNodes:
    """Класс свойств умного размышления для агента."""

    MAX_LOOP_GENERATION = 3

    async def check_user_answer(self, state: AgentState) -> AgentState:
        """Проверяет, покрыт ли исходный вопрос (text) в final_answer.

        Args:
            state: Текущее состояние.

        Returns:
            Dict с обновлённым status и counter_loop.
            - status="DONE" если final_answer релевантен text.
            - status="AGAIN" + counter_loop +=1 если нет (max 3).
        """
        async with self._node_span("check_user_answer", state) as span:
            prompt = self.langfuse_client.get_prompt("check_user_answer").get_langchain_prompt()
            prompt = ChatPromptTemplate.from_template(prompt)
            chain = prompt | self.llm
            response = await chain.ainvoke(
                {
                    "question": state["text"],
                    "parts": state.get("parts", "[]"),
                    "history_questions": state.get("user_history", "[]"),
                    "answer": state["final_answer"],
                },
                config=self._llm_config(span),
            )
            response = "DONE" in response.content.strip().upper()

            if response:
                state["status"] = AgentStatus.DONE
                state["counter_loop"] = 0
                state["additional_info"] = ""
            else:
                counter = state.get("counter_loop", 0)
                if counter >= self.MAX_LOOP_GENERATION:
                    state["status"] = AgentStatus.DONE
                    state["counter_loop"] = 0
                    state["additional_info"] = ""
                else:
                    if not state.get("counter_loop"):
                        state["counter_loop"] = 0

                    state["counter_loop"] += 1
                    state["additional_info"] = state["final_answer"]
                    state["status"] = AgentStatus.AGAIN
            return state

    async def generate_additional_questions(self, state) -> AgentState:
        """Генерируем новые вопросы чтобы ответить на вопрос пользователя.

        Note:
            Идея в том, чтобы LLM сгенерировал новые вопросы если ответ на запрос пользователя не дали.
            Новые вопросы затем будут обработанны в цикле через part_async (если речь об UnionAgent).

        Return:
            Новый список вопросов.
        """
        async with self._node_span("generate_additional_questions", state) as span:
            prompt = self.langfuse_client.get_prompt("generate_additional_questions").get_langchain_prompt()
            prompt = ChatPromptTemplate.from_template(prompt)
            chain = prompt | self.llm
            response = await chain.ainvoke(
                {
                    "question": state["text"],
                    "history_questions": state.get("user_history", "[]"),
                    "answer": state["final_answer"],
                    "parts": state.get("parts", "[]"),
                },
                config=self._llm_config(span),
            )

            response = response.content.strip()

            content = re.search(r"<ЗАДАЧИ.*?>(.*?)</ЗАДАЧИ>", response, re.IGNORECASE | re.DOTALL)
            content = content.group(1) if content else response

            data = {"parts": [p.strip() for p in content.split("<PART>") if p.strip()]}
            return data
