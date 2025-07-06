import json
import requests

from UnionChatBot.utils.EmbeddingAPI import MyEmbeddingFunction
from UnionChatBot.utils.ChromaAdapter import ChromaAdapter
from UnionChatBot.utils.RedisAdapters import SemanticRedisCache
from UnionChatBot.utils.ChatHistoryManager import ChatHistoryManager

class MyYandexModel:
    def __init__(self,
                 temperature: float = 0.3,
                 stream: bool = False,
                 maxTokens: int = 2000,
                 folder_id: str = None,
                 api_key: str = None,
                 url: str = None,
                 model_name: str = "deepseek-r1-distill-qwen-32b",
                 embedding_function: MyEmbeddingFunction = None,
                 chroma_adapter: ChromaAdapter = None,
                 redis_cache: SemanticRedisCache = None,
                 chat_manager: ChatHistoryManager = None):

        self.temperature = temperature
        self.stream = stream
        self.maxTokens = maxTokens
        self.url = url
        self.model_name = model_name
        self.embedding_function = embedding_function
        self.redis_cache = redis_cache
        self.chroma_adapter = chroma_adapter
        self.chat_manager = chat_manager

        if url is None:
            self.url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"

        if folder_id is None or api_key is None:
            raise ValueError(
                "FOLDER_ID or API_KEY hasn`t been defined! This is important parameters for YandexCloud API!")
        else:
            self.folder_id = folder_id
            self.api_key = api_key

        if maxTokens >= 8001:
            raise Warning("It is not recommended to set more than 8000 tokens!")

        if maxTokens >= 32001:
            raise Warning("You set limited maxTokens rate based on YandexAPI")

    def setup_header(self) -> dict:
        return {
            'Content-Type': 'application/json',
            'Authorization': 'Api-Key ' + self.api_key,
            'x-folder-id': self.folder_id,
            'x-data-logging-enabled': 'false'
        }

    def setup_data(self, text: str, prompt: str) -> json.dumps:
        return json.dumps({
            "modelUri": f"gpt://{self.folder_id}/{self.model_name}",
            "completionOptions": {
                "stream": self.stream,
                "temperature": self.temperature,
                "maxTokens": str(self.maxTokens)
            },
            "messages": [
                {
                    "role": "system",
                    "text": prompt
                },
                {
                    "role": "user",
                    "text": text
                }
            ]
        })

    def modify_system_prompt(self, query: str, prompt: str, data: dict, history_data: str) -> str:
        """ Apply modification for system prompt based on DB info.

        Note:
            This function based on query to modify prompt.
        """
        context = " ".join(
            [
                "№" + str(idx) + " <Информация>: " + info[0] + " " + "<Источник>: " + info[1].get(
                    list(info[1].keys())[0]) + " </Источник> <Файл> " + list(info[1].keys())[
                    0] + "</Файл>" + "</Информация> \n"
                for idx, info in enumerate(zip(data.get("documents"), data.get("metadatas")))
            ]) + \
                  "</RAG>"
        prompt += " " + context + history_data
        return prompt

    def ask(self, query: str, collection_name: str, prompt: str, user_id: str) -> str:
        query_embedding = self.embedding_function(query) if self.embedding_function else None

        if self.redis_cache and query_embedding is not None:
            cached = self.redis_cache.get(query, query_embedding)
            if cached:
                self.chat_manager.add_message_to_history(user_id=user_id, message=cached['response'])
                return cached['response']

        data = self.chroma_adapter.get_info(query=query, collection_name=collection_name)
        history_data = self.chat_manager.get_formatted_history(user_id=user_id)
        new_prompt = self.modify_system_prompt(query=query, prompt=prompt, data=data, history_data=history_data)
        response = requests.post(url=self.url, headers=self.setup_header(),
                                 data=self.setup_data(text=query, prompt=new_prompt))

        if response.status_code == 200:
            dict_response = json.loads(response.content)
            out = dict_response.get('result').get('alternatives')[0].get('message').get('text')

            # Сохраняем в кэш
            if self.redis_cache and query_embedding is not None:
                self.redis_cache.set(query, query_embedding, out)
                self.chat_manager.add_message_to_history(user_id=user_id, message=out)
        else:
            out = f"Код ответа {response.status_code}. Попробуйте задать вопрос позднее."

        return out