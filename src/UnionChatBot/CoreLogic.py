import json
import os
from typing import Optional

import requests

from UnionChatBot.utils.BasicManager import BasicManager
from UnionChatBot.utils.EmbeddingAPI import MyEmbeddingFunction
from UnionChatBot.utils.ChromaAdapter import ChromaAdapter
from UnionChatBot.utils.RedisAdapters import SemanticRedisCache
from UnionChatBot.utils.ChatHistoryManager import ChatHistoryManager
from UnionChatBot.utils.QueryRewriteManager import QueryRewriteManager


class CoreQueryProcessor(BasicManager):
    """Центральный класс позволяющий реализовать логику работы чат-бота.

    Args:
        embedding_function: объект класса отвечающий за векторизацию текста.
        chroma_adapter: объект класса отвечающий за взаимодействие с векторной БД.
        redis_cache: объект класса отвечающий за взаимодействие с горячей БД Redis.
        chat_manager: объект класса отвечающий за контроль истории пользователя при общении с чат-ботом.
    """

    core_prompt_file = os.getenv("DEFAULT_PROMPT_FILE", "default_prompt.txt")
    core_prompt_dir = os.getenv("DEFAULT_DIR_PROMPT", "./prompts")

    def __init__(
        self,
        temperature: float = 0.3,
        stream: bool = False,
        maxTokens: int = 2000,
        model_name: str = "deepseek-r1-distill-qwen-32b",
        embedding_function: MyEmbeddingFunction = None,
        chroma_adapter: ChromaAdapter = None,
        redis_cache: SemanticRedisCache = None,
        chat_manager: ChatHistoryManager = None,
        query_rewriter: Optional[QueryRewriteManager] = None,
        **kwargs,
    ):
        super().__init__(
            model_name=model_name,
            temperature=temperature,
            stream=stream,
            maxTokens=maxTokens,
            **kwargs,
        )

        self.embedding_function = embedding_function
        self.redis_cache = redis_cache
        self.chroma_adapter = chroma_adapter
        self.chat_manager = chat_manager
        self.query_rewriter = query_rewriter

    def modify_system_prompt(self, prompt: str, data: dict, user_id: str) -> str:
        """Модифицируем системный промт исходя из ответов из базы данных.

        Args:
            prompt: системый промт по умолчанию.
            data: словарь с релевантной информацией из БД.
            user_id: уникальный индетефикатор пользователя.

        Return:
            Модифицированный системный промт исходя из дополнительной информации из БД и истории диалога.
        """
        history_data = self.chat_manager.get_formatted_history(user_id=user_id)
        prompt += "<RAG>"
        context = (
            " ".join(
                [
                    "№"
                    + str(idx)
                    + " <Информация>: "
                    + info[0]
                    + " "
                    + "<Источник>: "
                    + info[1].get(list(info[1].keys())[0])
                    + " </Источник> <Файл> "
                    + list(info[1].keys())[0]
                    + "</Файл>"
                    + "</Информация> \n"
                    for idx, info in enumerate(
                        zip(data.get("documents"), data.get("metadatas"))
                    )
                ]
            )
            + "</RAG>"
        )
        prompt += " " + context + history_data
        return prompt

    def ask(self, query: str, collection_name: str, user_id: str) -> str:
        """Инициализация диалога с чат-ботом.

        Args:
            query: вопрос пользователя & сообщение.
            collection_name: название коллекции к которой необходимо обратиться в ChromaDB.
            user_id: уникальный идентификатор пользователя.

        Return:
            Текстовый ответ модели для пользователя.
        """
        query_embedding = self.embedding_function(query)

        system_prompt = self.read_prompt(
            prompt_file=self.core_prompt_file, prompt_dir=self.core_prompt_dir
        )

        cached = self.redis_cache.get(query, query_embedding)
        if cached:
            self.chat_manager.add_message_to_history(
                user_id=user_id, message=cached["response"]
            )
            return cached["response"]

        if self.query_rewriter:
            query, status = self.query_rewriter.rewrite(query=query, user_id=user_id)
            if status != 200:
                return query

        data = self.chroma_adapter.get_info(
            query=query, collection_name=collection_name
        )
        new_prompt = self.modify_system_prompt(
            prompt=system_prompt, data=data, user_id=user_id
        )
        response = requests.post(
            url=self.url,
            headers=self.setup_header(),
            data=self.setup_data(text=query, prompt=new_prompt),
        )

        if response.status_code == 200:
            dict_response = json.loads(response.content)
            answer = (
                dict_response.get("result")
                .get("alternatives")[0]
                .get("message")
                .get("text")
            )
            self.redis_cache.set(query, query_embedding, answer)
            self.chat_manager.add_message_to_history(user_id=user_id, message=answer)
        else:
            answer = (
                f"Код ответа {response.status_code}. Попробуйте задать вопрос позднее."
            )
        return answer
