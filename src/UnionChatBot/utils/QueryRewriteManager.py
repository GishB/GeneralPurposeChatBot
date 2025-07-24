import json
import os
from typing import Tuple

import requests

from UnionChatBot.utils.BasicManager import BasicManager
from UnionChatBot.utils.ChatHistoryManager import ChatHistoryManager


class QueryRewriteManager(BasicManager, ChatHistoryManager):
    path_to_prompt = os.getenv("PROMPT_PATH", "./prompts")
    filter_prompt = os.getenv("ASSISTANT_PROMPT_NAME", "assistant_prompt.txt")

    def __init__(
        self,
        model_name: str = "yandexgpt",
        maxTokens: int = 4000,
        temperature: float = 0.9,
        redis_db=1,
        **kwargs,
    ):
        super().__init__(
            maxTokens=maxTokens,
            model_name=model_name,
            temperature=temperature,
            redis_db=redis_db,
            **kwargs,
        )

    def add_history_info(self, prompt: str, user_id: str) -> str:
        history = self.get_formatted_history(user_id=user_id)
        return prompt + history

    def rewrite(self, query: str, user_id: str) -> Tuple[str, int]:
        """Переписываем запрос исходя из контекста истории и настроек модели.

        Arg:
            query: запрос пользователя в сыром виде.
            user_id: уникальный идентификатор пользователя.

        Return:
            Модифицированный запрос пользователя исходя из логики модели.
        """
        prompt = self.read_prompt(
            prompt_dir=self.path_to_prompt, prompt_file=self.filter_prompt
        )
        prompt = self.add_history_info(prompt=prompt, user_id=user_id)

        response = requests.post(
            url=self.url,
            headers=self.setup_header(),
            data=self.setup_data(text=query, prompt=prompt),
        )

        if response.status_code == 200:
            dict_response = json.loads(response.content)
            out = (
                dict_response.get("result")
                .get("alternatives")[0]
                .get("message")
                .get("text")
            )
        else:
            out = (
                f"Код ответа {response.status_code}. Попробуйте задать вопрос позднее."
            )
        return out, response.status_code
