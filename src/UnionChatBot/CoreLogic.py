import json
import os
import logging
from typing import Optional

import requests

from UnionChatBot.utils.BasicManager import BasicManager
from UnionChatBot.utils.EmbeddingAPI import MyEmbeddingFunction
from UnionChatBot.utils.ChromaAdapter import ChromaAdapter
from UnionChatBot.utils.RedisAdapters import SemanticRedisCache
from UnionChatBot.utils.ChatHistoryManager import ChatHistoryManager
from UnionChatBot.utils.QueryRewriteManager import QueryRewriteManager

# Настройка логгера модуля
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(name)s - %(message)s"
)
logger = logging.getLogger(__name__)


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
    maxTokens = int(os.getenv("MAX_TOKENS_DEFAULT_API", 10000))

    def __init__(
        self,
        temperature: float = 0.3,
        stream: bool = False,
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
            maxTokens=self.maxTokens,
            **kwargs,
        )

        self.embedding_function = embedding_function
        self.redis_cache = redis_cache
        self.chroma_adapter = chroma_adapter
        self.chat_manager = chat_manager
        self.query_rewriter = query_rewriter
        logger.info(f"CoreQueryProcessor initialized with model {model_name}")

    def modify_system_prompt(self, prompt: str, data: dict, user_id: str) -> str:
        """Модифицируем системный промт исходя из данных из базы и истории пользователя.

        Args:
            prompt: системный промт по умолчанию.
            data: словарь с релевантной информацией из БД.
            user_id: уникальный идентификатор пользователя.

        Returns:
            Модифицированный системный промт.
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
                    + info[1].get(list(info[1].keys())[0], "нет источника")
                    + " </Источник>"
                    + "</Информация> \n"
                    for idx, info in enumerate(
                        zip(data.get("documents", []), data.get("metadatas", []))
                    )
                ]
            )
            + "</RAG>"
        )

        prompt += " " + context + history_data
        logger.debug(f"System prompt after modification for user {user_id}: {prompt}")
        return prompt

    def ask(self, query: str, collection_name: str, user_id: str) -> str:
        """Инициализация диалога с чат-ботом.

        Args:
            query: вопрос пользователя & сообщение.
            collection_name: название коллекции к которой необходимо обратиться в ChromaDB.
            user_id: уникальный идентификатор пользователя.

        Returns:
            Текстовый ответ модели для пользователя.
        """
        logger.debug(f"User {user_id} - init query: {query}")
        query_embedding = self.embedding_function(query)
        logger.debug(f"User {user_id} - query embedding generated")

        system_prompt = self.read_prompt(
            prompt_file=self.core_prompt_file, prompt_dir=self.core_prompt_dir
        )
        logger.debug(f"User {user_id} - system prompt loaded: {system_prompt[:100]}...")

        cached = self.redis_cache.get(query, query_embedding)
        if cached:
            logger.info(f"User {user_id} - cache hit for query")
            self.chat_manager.add_message_to_history(
                user_id=user_id, message=cached["response"]
            )
            return cached["response"]

        if self.query_rewriter:
            query, status = self.query_rewriter.rewrite(query=query, user_id=user_id)
            if status != 200:
                logger.warning(
                    f"User {user_id} - query rewrite failed with status {status}: {query}"
                )
                return query
            logger.debug(f"User {user_id} - query after rewrite: {query}")

        data = self.chroma_adapter.get_info(
            query=query, collection_name=collection_name
        )
        logger.debug(f"User {user_id} - chroma_adapter returned data: {data}")

        new_prompt = self.modify_system_prompt(
            prompt=system_prompt, data=data, user_id=user_id
        )
        logger.debug(f"User {user_id} - new prompt generated")

        try:
            response = requests.post(
                url=self.url,
                headers=self.setup_header(),
                data=self.setup_data(text=query, prompt=new_prompt),
            )
            logger.debug(
                f"User {user_id} - request sent, response status: {response.status_code}"
            )
        except Exception as e:
            logger.error(f"User {user_id} - exception during request: {e}")
            return "Произошла ошибка при обращении к сервису. Пожалуйста, попробуйте позже."

        if response.status_code == 200:
            dict_response = json.loads(response.content)
            answer = (
                dict_response.get("result", {})
                .get("alternatives", [{}])[0]
                .get("message", {})
                .get("text", "")
            )
            logger.info(f"User {user_id} - API response received successfully")
            self.redis_cache.set(query, query_embedding, answer)
            self.chat_manager.add_message_to_history(user_id=user_id, message=answer)
        else:
            answer = (
                f"Код ответа {response.status_code}. Попробуйте задать вопрос позднее."
            )
            logger.error(
                f"User {user_id} - API returned error status: {response.status_code}"
            )

        return answer
