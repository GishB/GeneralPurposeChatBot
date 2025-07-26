import os
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from UnionChatBot.utils.SessionAdapter import setting_up
from UnionChatBot.utils.RedisAdapters import UserRateLimiter
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv
from pydantic import Field
import re

app = FastAPI()
load_dotenv()


# Модели запросов
class ChatRequest(BaseModel):
    query: str = Field(
        ...,
        min_length=2,
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


# Инициализация компонентов
client_yandex = setting_up()
rate_limiter = UserRateLimiter()
DEFAULT_COLLECTION = os.getenv("COLLECTION_NAME")


def is_specific_error(text: str) -> bool:
    """Обрабатывает случаи, когда ответ на запрос пользователя это заглушка Яндекса.

    Args:
        text: генерация YandexGPT модели после обработки вопроса.

    Returns:
        bool: Если True, то этот ответ пользователю не показываем.
    """
    # Регулярное выражение для поиска ссылок на Яндекс
    pattern = r"\b(?:https?://)?(?:[a-z0-9-]+\.)*yandex\.(?:ru|com|ua|by|kz)(?:/\S*)?\b"

    # Игнорируем регистр для поиска
    if re.search(pattern, text, re.IGNORECASE):
        return True
    return False


@app.on_event("startup")
async def startup_event():
    """Ставим ограничение на кол-во параллельных потоков которые могут быть запущенны сервисом"""
    app.state.executor = ThreadPoolExecutor(
        max_workers=int(os.environ["MAX_FASTAPI_THREADS"])
        if int(os.environ["MAX_FASTAPI_THREADS"])
        else 4
    )


@app.post("/chat")
def chat_with_bot(request: ChatRequest):
    """
    Основной эндпоинт для взаимодействия с чат-ботом

    Параметры:
    - query: вопрос пользователя (обязательный)
    - user_id: идентификатор пользователя (обязательный)
    - prompt: промт (опциональный, будет использован дефолтный)
    - collection_name: имя коллекции (опциональное, будет использовано дефолтное)
    """
    try:
        allowed, current = rate_limiter.check_and_increment(request.user_id)
        if allowed:
            collection_name = (
                request.collection_name
                if request.collection_name
                else DEFAULT_COLLECTION
            )

            # Получаем ответ от модели
            response = client_yandex.ask(
                query=request.query,
                collection_name=collection_name,
                user_id=request.user_id,
            )
            if is_specific_error(response):
                return {
                    "status": "failed",
                    "response": "Извините, что Ваш вопрос не может быть обработан правильно в силу технических причин "
                    "из-за AI стороннего сервиса. \n"
                    " Попробуйте сформулировать вопрос по теме немного иначе, пожалуйста.",
                    "user_id": request.user_id,
                    "request_id": request.request_id,
                }
            else:
                return {
                    "status": "success",
                    "response": response,
                    "user_id": request.user_id,
                    "request_id": request.request_id,
                }
        else:
            return {
                "status": "success",
                "response": f"Вы достигли лимита запросов к сервису в течении суток. За последние сутки Вы обращались к боту: {current} раз. \n"
                f" Общее ограничение для каждого пользователя: {int(os.getenv('USER_QUERY_LIMIT_N', 10))} сообщений в сутки. \n"
                f" Повторите свой вопрос позднее, пожалуйста, или обратитесь в профсоюзную организацию напрямую.",
                "user_id": request.user_id,
                "request_id": request.request_id,
            }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Произошла ошибка при обработке запроса: {str(e)}"
        )


@app.get("/health")
async def health_check():
    """Проверка работоспособности сервиса"""
    return {"status": "ok"}


@app.get("/threadpool-stats")
async def threadpool_stats(request: Request):
    """Проверка нагрузки на потоки в рамках сервиса."""
    executor = request.app.state.executor
    return {
        "max_workers": executor._max_workers,  # type: ignore
        "active_threads": len(executor._threads),  # type: ignore
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=32000, workers=1)
