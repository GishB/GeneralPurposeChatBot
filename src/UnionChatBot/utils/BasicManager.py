import json
import os


class BasicManager:
    """Базовые возможности менеджера запросов к YandexGPTAPI.

    Args:
        temperature: температура с которой генерируются ответы модели.
        stream: необходимость возвращать ответ посимвольно.
        maxTokens: ограничение на кол-во токенов для модели суммарно генерация + ответ.
        folder_id: секрет принадлежащий сервисному аккаунту Yandex GPT API.
        api_key: секрет принадлежащий сервисному аккаунту Yandex GPT API.
        url: ссылка на YandexGPTAPI inference.
        model_name: модель используемая для генерации ответа.
    """

    url = os.getenv(
        "YANDEXGPT_API",
        "https://llm.api.cloud.yandex.net/foundationModels/v1/completion",
    )
    folder_id = os.getenv("FOLDER_ID", None)
    api_key = os.getenv("API_KEY", None)

    def __init__(
        self,
        model_name: str,
        maxTokens: str = "8000",
        stream: bool = False,
        temperature: float = 0.3,
        **kwargs,
    ):
        self.stream = stream
        self.temperature = temperature
        self.model_name = model_name
        self.maxTokens = maxTokens

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

    @staticmethod
    def read_prompt(prompt_file: str, prompt_dir: str) -> str:
        with open(prompt_dir + "/" + prompt_file, "r", encoding="utf-8") as file:
            return file.read()
