"""
Здесь расположены Pydantic модели для описания ответов, тел запросов, возвращаемых ошибок и т.д.
"""

from typing import Literal

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


class ChatJobAccepted(BaseModel):
    """Ответ на асинхронный запрос создания задачи генерации."""

    job_id: str = Field(..., description="Идентификатор задачи, равен x-trace-id")
    status: Literal["processing"] = Field(default="processing")


class ChatJobStatusResponse(BaseModel):
    """Текущий статус асинхронной задачи генерации."""

    status: Literal["processing", "done", "error", "not_found"]
    job_id: str | None = Field(default=None)
    elapsed_ms: int | None = Field(default=None)
    message: str | None = Field(default=None)
    response: str | None = Field(default=None)
    code: str | None = Field(default=None)
    error: str | None = Field(default=None)


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
