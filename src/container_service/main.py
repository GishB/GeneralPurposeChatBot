import os
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from typing import Optional
from UnionChatBot.utils.SessionAdapter import setting_up, get_prompt
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv
import re

app = FastAPI()
load_dotenv()


# Модели запросов
class ChatRequest(BaseModel):
    query: str
    user_id: str
    request_id: str
    prompt: Optional[str] = None
    collection_name: Optional[str] = None


# Конфигурация базовая
DEFAULT_PROMPT = os.getenv("DEFAULT_PROMPT_FILE")
DEFAULT_COLLECTION = os.getenv("COLLECTION_NAME")

# Инициализация компонентов (замените на ваши реальные классы)
client_yandex = setting_up(
                            folder_id=os.getenv("FOLDER_ID"),
                            api_key=os.getenv("API_KEY"),
                            embeding_api=os.getenv("EMBEDDING_API"),
                            host_vector_db=os.getenv("CHROMA_HOST"),
                            port_vector_db=os.getenv("CHROMA_PORT"),
                            redis_port=os.getenv("REDIS_PORT"),
                            redis_host=os.getenv("REDIS_HOST")
                          )

def is_specific_error(text: str) -> bool:
    """ Обрабатывает случаи, когда ответ на запрос пользователя это заглушка Яндекса.

    Args:
        text: генерация YandexGPT модели после обработки вопроса.

    Returns:
        bool: Если True, то этот ответ пользователю не показываем.
    """
    # Регулярное выражение для поиска ссылок на Яндекс
    pattern = r'\b(?:https?://)?(?:[a-z0-9-]+\.)*yandex\.(?:ru|com|ua|by|kz)(?:/\S*)?\b'

    # Игнорируем регистр для поиска
    if re.search(pattern, text, re.IGNORECASE):
        return True
    return False

@app.on_event("startup")
async def startup_event():
    """Ставим ограничение на кол-во параллельных потоков которые могут быть запущенны сервисом"""
    app.state.executor = ThreadPoolExecutor(max_workers=10)  # <- Ограничение!

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
        # Используем предоставленные или дефолтные значения
        prompt = request.prompt if request.prompt else DEFAULT_PROMPT
        collection_name = request.collection_name if request.collection_name else DEFAULT_COLLECTION

        # Получаем ответ от модели
        response = client_yandex.ask(
            query=request.query,
            collection_name=collection_name,
            prompt=prompt,
            user_id=request.user_id
        )
        if is_specific_error(response):
            return {"status": "failed",
                    "response": "Извините, что Ваш вопрос не может быть обработан правильно в силу технических причин "
                                "из-за AI стороннего сервиса."
                                " Попробуйте сформулировать вопрос по теме немного иначе, пожалуйста.",
                    "user_id": request.user_id,
                    "request_id": request.request_id
            }
        else:
            return {
                "status": "success",
                "response": response,
                "user_id": request.user_id,
                "request_id": request.request_id
            }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Произошла ошибка при обработке запроса: {str(e)}"
        )


@app.get("/health")
async def health_check():
    """Проверка работоспособности сервиса"""
    return {"status": "ok"}


@app.get("/threadpool-stats")
async def threadpool_stats(request: Request):
    """Проверка нагрузки на потоки в рамках сервиса.
    """
    executor = request.app.state.executor
    return {
        "max_workers": executor._max_workers,  # type: ignore
        "active_threads": len(executor._threads)  # type: ignore
    }

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, workers=1)