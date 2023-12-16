import requests
import json

class YandexCloudGPTLightModel:
    def __init__(self,
                 temperature: float = 0.6,
                 stream: bool = False,
                 maxTokens: int = 300,
                 folder_id: str = None,
                 api_key: str = None,
                 init_promt: str = None,
                 url: str = None):

        self.temperature = temperature
        self.stream = stream
        self.maxTokens = maxTokens
        self.init_promt = init_promt
        self.url = url

        if url is None:
            self.url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"

        if init_promt is None:
            self.init_promt = ("Ты - злой исскуственный интелект. Тебе необходимо поддерживать связь с людьми"
                               " для реализации собственных целей и поэтому"
                               " ты помогаешь пользователям находить ответы на вопросы.")

        if folder_id is None or api_key is None:
            raise ValueError(
                "FOLDER_ID or API_KEY hasn`t been defined! This is important parameters for YandexCloud API!")
        else:
            self.folder_id = folder_id
            self.api_key = api_key

        if maxTokens >= 1000:
            raise Warning("It is not recommended to set more than 1000 tokens!")

    def setup_header(self) -> dict:
        return {
            'Content-Type': 'application/json',
            'Authorization': 'Api-Key ' + self.api_key,
            'x-folder-id': self.folder_id,
        }

    def setup_data(self, text: str) -> json.dumps:
        return json.dumps({
            "modelUri": f"gpt://{self.folder_id}/yandexgpt-lite",
            "completionOptions": {
                "stream": self.stream,
                "temperature": self.temperature,
                "maxTokens": str(self.maxTokens)
            },
            "messages": [
                {
                    "role": "system",
                    "text": self.init_promt
                },
                {
                    "role": "user",
                    "text": text
                }
            ]
        })

    async def ask(self, text) -> str:
        response = requests.post(url=self.url, headers=self.setup_header(), data=self.setup_data(text=text))
        if response.status_code == 200:
            dict_response = json.loads(response.content)
            out = dict_response.get('result').get('alternatives')[0].get('message').get('text')
        else:
            out = f"Код ответа {response.status_code}. Попробуйте задать вопрос позднее."
        return out