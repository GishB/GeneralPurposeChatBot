import json
import os
from typing import Optional

import requests

from UnionChatBot.utils.EmbeddingAPI import MyEmbeddingFunction
from UnionChatBot.utils.ChromaAdapter import ChromaAdapter
from UnionChatBot.utils.RedisAdapters import SemanticRedisCache
from UnionChatBot.utils.ChatHistoryManager import ChatHistoryManager


class MyYandexModel:
    """Центральный класс позволяющий реализовать логику работы чат-бота.

    Args:
        temperature: температура с которой генерируются ответы модели.
        stream: необходимость возвращать ответ посимвольно.
        maxTokens: ограничение на кол-во токенов для модели суммарно генерация + ответ.
        folder_id: секрет принадлежащий сервисному аккаунту Yandex GPT API.
        api_key: секрет принадлежащий сервисному аккаунту Yandex GPT API.
        url: ссылка на YandexGPTAPI inference.
        model_name: модель используемая для генерации ответа.
        embedding_function: объект класса отвечающий за векторизацию текста.
        chroma_adapter: объект класса отвечающий за взаимодействие с векторной БД.
        redis_cache: объект класса отвечающий за взаимодействие с горячей БД Redis.
        chat_manager: объект класса отвечающий за контроль истории пользователя при общении с чат-ботом.
    """

    def __init__(
        self,
        temperature: float = 0.3,
        stream: bool = False,
        maxTokens: int = 2000,
        folder_id: Optional[str] = None,
        api_key: Optional[str] = None,
        url: Optional[str] = None,
        model_name: str = "deepseek-r1-distill-qwen-32b",
        embedding_function: MyEmbeddingFunction = None,
        chroma_adapter: ChromaAdapter = None,
        redis_cache: SemanticRedisCache = None,
        chat_manager: ChatHistoryManager = None,
    ):
        self.temperature = temperature
        self.stream = stream
        self.maxTokens = maxTokens
        self.model_name = model_name
        self.embedding_function = embedding_function
        self.redis_cache = redis_cache
        self.chroma_adapter = chroma_adapter
        self.chat_manager = chat_manager

        self.url = url if url else os.environ["YANDEXGPT_API"]
        self.folder_id = folder_id if folder_id else os.environ["FOLDER_ID"]
        self.api_key = api_key if api_key else os.environ["API_KEY"]

        if self.folder_id is None or self.api_key is None:
            raise ValueError(
                "FOLDER_ID or API_KEY hasn`t been defined at ENV! This is important parameters for YandexCloud API!"
            )

        if self.url is None:
            raise ValueError(
                "YANDEXGPT_API url hasn`t been defined at ENV! How you are going to inference at all???"
            )

        if maxTokens >= 8001:
            raise Warning("It is not recommended to set more than 8000 tokens!")

        if maxTokens >= 32000:
            raise Warning(
                "You set limited maxTokens rate based on YandexAPI docs at 2025!"
            )

    def setup_header(self) -> dict:
        """Генерируем классический Header запроса.

        Return:
            Требуемого вида JSON объект в виде словаря, для корректной аунтификации на endpoint.
        """
        return {
            "Content-Type": "application/json",
            "Authorization": "Api-Key " + self.api_key,
            "x-folder-id": self.folder_id,
            "x-data-logging-enabled": "false",
        }

    def setup_data(self, text: str, prompt: str) -> json.dumps:
        """Генерируем полное тело запроса для последующей генерации ответа модели.

        Args:
            text: Запрос пользователя (может быть в сыром виде);
            prompt: Дополнительная информация для генерации правильного ответа моделью.

        Return:
            Полное тело запроса для Yandex GPT endpoint.
        """
        return json.dumps(
            {
                "modelUri": f"gpt://{self.folder_id}/{self.model_name}",
                "completionOptions": {
                    "stream": self.stream,
                    "temperature": self.temperature,
                    "maxTokens": str(self.maxTokens),
                },
                "messages": [
                    {"role": "system", "text": prompt},
                    {"role": "user", "text": text},
                ],
            }
        )

    def modify_system_prompt(
        self, query: str, prompt: str, data: dict, history_data: str
    ) -> str:
        """Модифицируем системный промт исходя из ответов из базы данных.

        Args:
            query: вопрос пользователя.
            prompt: системый промт по умолчанию.
            history_data: история диалога для текущего пользователя.
            data: словарь с релевантной информацией из БД.

        Return:
            Модифицированный системный промт исходя из дополнительной информации из БД и истории диалога.
        """
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

    def ask(self, query: str, collection_name: str, prompt: str, user_id: str) -> str:
        """Инициализация диалога с чат-ботом.

        Args:
            query: вопрос пользователя & сообщение.
            collection_name: название коллекции к которой необходимо обратиться в ChromaDB.
            prompt: Системный промт, который определит поведение модели по умолчанию.
            user_id: уникальный идентификатор пользователя.

        Return:
            Текстовый ответ модели для пользователя.
        """
        query_embedding = (
            self.embedding_function(query) if self.embedding_function else None
        )

        if self.redis_cache and query_embedding is not None:
            cached = self.redis_cache.get(query, query_embedding)
            if cached:
                self.chat_manager.add_message_to_history(
                    user_id=user_id, message=cached["response"]
                )
                return cached["response"]

        data = self.chroma_adapter.get_info(
            query=query, collection_name=collection_name
        )
        history_data = self.chat_manager.get_formatted_history(user_id=user_id)
        new_prompt = self.modify_system_prompt(
            query=query, prompt=prompt, data=data, history_data=history_data
        )
        response = requests.post(
            url=self.url,
            headers=self.setup_header(),
            data=self.setup_data(text=query, prompt=new_prompt),
        )

        if response.status_code == 200:
            dict_response = json.loads(response.content)
            out = (
                dict_response.get("result")
                .get("alternatives")[0]
                .get("message")
                .get("text")
            )

            # Сохраняем в кэш
            if self.redis_cache and query_embedding is not None:
                self.redis_cache.set(query, query_embedding, out)
                self.chat_manager.add_message_to_history(user_id=user_id, message=out)
        else:
            out = (
                f"Код ответа {response.status_code}. Попробуйте задать вопрос позднее."
            )

        return out
