"""
Здесь расположены Pydantic модели для описания ответов, тел запросов, возвращаемых ошибок и т.д.
"""

from typing import Optional

from pydantic import BaseModel, Field


class FailedDependencyResponse(BaseModel):
    """
    Реализация текущего запроса может зависеть от успешности выполнения другой операции.
    Если она не выполнена и из-за этого нельзя выполнить текущий запрос, то сервер вернёт этот код.
    """

    error_description: str = Field(
        description="Описание возникшей ошибки.",
        examples=["GigaChat aigw_service temporary unavailable."],
    )


class GigachatTestInvokeResponse(BaseModel):
    """Ответ для роута /test_invoke"""

    answer: str = Field(
        description="Ответ от GigaChat на вопрос пользователя с применением LangChain.",
    )


class GigachatTestInvokeRequest(BaseModel):
    """Тело запроса для роута /test_invoke"""

    question: str = Field(
        description="Вопрос к GigaChat от пользователя с применением LangChain.",
        min_length=4,
        examples=["Какой год основания Москвы?"],
    )
    generation_params: Optional[dict] = Field(
        description=(
            "Параметры для генерации ответа GigaChat. Подробнее о возможных параметрах: "
            "https://developers.sber.ru/docs/ru/gigachat/api/reference/rest/post-chat"
        ),
        default={},
        examples=[
            {
                "model": "GigaChat",
                "temperature": 1.0,
                "max_tokens": 1024,
                "top_p": 0.5,
                "repetition_penalty": 1.0,
            }
        ],
    )


class GigachatTestEmbeddingsResponse(BaseModel):
    """Ответ для роута /test_embeddings"""

    embeddings: list[float] = Field(
        description="Эмбеддинги, полученные с помощью GigaChatEmbeddings из LangChain.",
    )


class GigachatTestEmbeddingsRequest(BaseModel):
    """Тело запроса для роута /test_embeddings"""

    query: str = Field(
        description="Текст для получения эмбеддингов с помощью GigaChatEmbeddings из LangChain.",
        min_length=4,
        examples=["Привет!"],
    )

class LisaSearchRequest(BaseModel):
    """ Схема для запроса из мессенджера Лисы.
    """
    ucpkb_id: Optional[str] = Field(
        description="ID клиента (ЕПК ID)",
    )
    industry_qualifier_name: Optional[str] = Field(
        description="Отрасль по ОКК",
    )
    inn: Optional[str] = Field(
        description_name="ИНН клиента"
    )

class LisaSearchResponse(BaseModel):
    text: str = Field(..., description="Варианты ответа для пользователя по сценарию 1 и 2")

class PartnerSearchRequest(BaseModel):
    text: str = Field(..., description="Любое текстовое сообщение от пользователя")

class PartnerSearchResponse(BaseModel):
    text: str = Field(..., description="Любой ответ от модели текстом")