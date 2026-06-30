"""
Здесь расположены Pydantic модели для описания ответов, тел запросов, возвращаемых ошибок и т.д.
"""

from pydantic import BaseModel, Field


class AgentChatRequest(BaseModel):
    """
    Стандартная схема на вход от пользователя.
    """

    text: str = Field(
        ...,
        min_length=4,
        max_length=512,
        examples=["Как вступить в профсоюз?"],
    )
    organisation: str = Field(..., min_length=2, max_length=256, examples=["ППО Невинномысский Азот"])

    class Config:
        extra = "forbid"


class AgentChatResponse(BaseModel):
    """
    Стандартная схема ответа на вопрос пользователя
    """

    response: str = Field(
        ..., min_length=4, max_length=2048, examples=["Для того, чтобы вступить в профсоюз вам необходимо всеголишь..."]
    )

    class Config:
        extra = "forbid"


class FailedDependecyResponse(BaseModel):
    error_description: str = Field(
        description="Описание возникшей ошибки.", examples=["YandexGPT service temporary unavailable."]
    )


class LLMAPITestResponse(BaseModel):
    """
    Ответ для роута /test_invoke
    """

    answer: str = Field(description="Ответ от LLM API на вопрос пользователя")


class LLMAPITestRequest(BaseModel):
    question: str = Field(
        description="Вопрос к LLM от пользователя", min_length=4, max_length=500, examples=["Кто ты воин?"]
    )

    generation_params: dict | None = Field(
        description="Параметры для генерации ответа LLM API.",
        default={},
        examples=[
            {
                "model": "deepseek/deepseek-chat",
                "temperature": 0.32,
                "max_tokens": 2048,
                "top_p": 0.16,
                "repetition_penalty": 0.8,
            }
        ],
    )
