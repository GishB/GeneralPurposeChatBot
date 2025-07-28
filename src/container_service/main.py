import os
from fastapi import FastAPI, HTTPException, Request
from UnionChatBot.utils.SessionAdapter import setting_up
from UnionChatBot.utils.RedisAdapters import UserRateLimiter
from UnionChatBot.utils.PostgresAdapter import AuditLogger
from UnionChatBot.schemas.services import ChatRequest, ChatResponse
from UnionChatBot.utils.timers import ExecutionTimer
from UnionChatBot.utils.error_handlers import is_specific_error
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv

from src.UnionChatBot.schemas.services import ResetRequest

app = FastAPI()
load_dotenv()

# Инициализация компонентов
client_yandex = setting_up()
rate_limiter = UserRateLimiter()
audit_logger = AuditLogger(os.getenv("POSTGRES_DSN"))


@app.on_event("startup")
async def startup_event():
    """Ставим ограничение на кол-во параллельных потоков которые могут быть запущенны сервисом"""
    app.state.executor = ThreadPoolExecutor(
        max_workers=int(os.environ["MAX_FASTAPI_THREADS"])
        if int(os.environ["MAX_FASTAPI_THREADS"])
        else 10
    )


@app.post("/reset")
def reset_limits(request: ResetRequest):
    try:
        rate_limiter.reset_counter(request.user_id)
        return {"status": "ok", "user_id": request.user_id}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Произошла ошибка при обработке запроса: {str(e)}"
        )


@app.post("/chat", response_model=ChatResponse)
def chat_with_bot(request: ChatRequest):
    """
    Основной эндпоинт для взаимодействия с чат-ботом

    Параметры:
    - query: вопрос пользователя (обязательный)
    - user_id: идентификатор пользователя (обязательный)
    """
    timer = ExecutionTimer()
    time_in = timer.format_european_time(timer.get_msk_time())
    try:
        allowed, current = rate_limiter.check_and_increment(request.user_id)
        if allowed:
            response = client_yandex.ask(
                query=request.query,
                collection_name=os.getenv("COLLECTION_NAME"),
                user_id=request.user_id,
            )
            if is_specific_error(response):
                out = {
                    "status": "error",
                    "response": "Извините, что Ваш вопрос не может быть обработан правильно в силу технических причин "
                    "из-за AI стороннего сервиса. \n"
                    " Попробуйте сформулировать вопрос по теме немного иначе, пожалуйста.",
                    "user_id": request.user_id,
                    "request_id": request.request_id,
                }
            else:
                out = {
                    "status": "success",
                    "response": response,
                    "user_id": request.user_id,
                    "request_id": request.request_id,
                }
        else:
            out = {
                "status": "success",
                "response": f"Вы достигли лимита запросов к сервису в течении суток. За последние сутки Вы обращались к боту: {current} раз. \n"
                f" Общее ограничение для каждого пользователя: {int(os.getenv('USER_QUERY_LIMIT_N', 10))} сообщений в сутки. \n"
                f" Повторите свой вопрос позднее, пожалуйста, или обратитесь в профсоюзную организацию напрямую.",
                "user_id": request.user_id,
                "request_id": request.request_id,
            }
        audit_logger.log(
            time_in=time_in,
            time_out=timer.format_european_time(timer.get_msk_time()),
            user_id=request.user_id,
            source_name=request.source_name,
            request_id=request.request_id,
            query_in=request.query,
            response_out=out.get("response"),
            status=out.get("status"),
            execution_time=timer.time(),
        )
        return out

    except Exception as e:
        audit_logger.log(
            time_in=time_in,
            time_out=timer.format_european_time(timer.get_msk_time()),
            user_id=request.user_id,
            source_name=request.source_name,
            request_id=request.request_id,
            query_in=request.query,
            response_out=str(e),
            status="failed",
            execution_time=timer.time(),
        )
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
