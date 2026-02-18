"""
Здесь расположены Pydantic модели для описания ответов, тел запросов, возвращаемых ошибок и т.д.
"""

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    query: str = Field(
        ...,
        min_length=4,
        max_length=500,
        examples=[
            "Я ваСя ПупкИН! Привет! Мне нравится работать. Как долго действует коллективный договор на предприятии?"
        ],
    )
    user_id: str = Field(..., examples=["0", "123124214"])
    request_id: str = Field(..., examples=["a1b2c3d4e5f67890"])
    source_name: str = Field(..., examples=["telegram", "www.profkom-nevazot.ru"])

    class Config:
        extra = "forbid"


class ChatResponse(BaseModel):
    response: str = Field(..., examples=["Привет Вася Пупкин! Долго действует!"])
    request_id: str = Field(..., examples=["a1b2c3d4e5f67890"])
    status: str = Field(..., examples=["success", "failed"])
    user_id: str = Field(..., examples=["0", "123124214"])

    class Config:
        extra = "forbid"


class ResetRequest(BaseModel):
    user_id: str

    class Config:
        extra = "forbid"

class FailedDependecyResponse(BaseModel):
    error_description: str = Field(
        description="Описание возникшей ошибки.",
        examples=["YandexGPT service temporary unavailable."]
    )

class YandexGPTAPITestResponse(BaseModel):
    """
    Ответ для роута /test_invoke
    """
    answer: str = Field(
        description="Ответ от YandexGPTAPI на вопрос пользователя"
    )

class YandexGPTAPITestRequest(BaseModel):
    question: str = Field(
        description="Вопрос к GigaChat от пользователя",
        min_length=4,
        max_length=500,
        examples=["Кто ты воин?"]
    )

    generation_params: dict | None = Field(
        description="Параметры для генерации ответа YandexGPTAPI.",
        default={},
        examples=[
            {
                "model": "yandexgpt",
                "temperature": 0.32,
                "max_tokens": 2048,
                "top_p": 0.16,
                "repetition_penalty": 0.8,
            }
        ]
    )