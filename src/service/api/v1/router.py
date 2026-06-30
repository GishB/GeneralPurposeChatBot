"""
Ядро для работы с endpoints.
"""

import asyncio
import time

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import JSONResponse

# from langgraph.checkpoint.memory import MemorySaver
from agents.profkom_consultant import AgentStatus, build_builder
from modules.llm_ext import FallbackChatOpenAI
from service.config import APP_CONFIG
from service.context import APP_CTX
from service.logger.context_vars import current_trace

from . import schemas
from .schemas import (
    AgentChatRequest,
    AgentChatResponse,
    ChatJobAccepted,
    ChatJobStatusResponse,
    FailedDependecyResponse,
    LLMAPITestResponse,
)
from .utils import common_headers

router = APIRouter()
logger = APP_CTX.get_logger()

# Множество для удержания ссылок на фоновые задачи генерации.
_BG_TASKS: set = set()


def _progress_message(elapsed_ms: int) -> str:
    """Человекочитаемое сообщение о прогрессе генерации."""
    sec = elapsed_ms // 1000
    if sec < 15:
        return "Анализирую ваш вопрос…"
    if sec < 45:
        return "Подбираю информацию по вашей организации…"
    return "Формирую развёрнутый ответ, это занимает чуть больше времени…"


async def _run_generation_inline(body: AgentChatRequest, headers: dict) -> str:
    """Синхронная генерация ответа агентом.

    Args:
        body: Тело запроса пользователя.
        headers: Системные заголовки.

    Returns:
        Текст финального ответа.

    Raises:
        Exception: Любая ошибка агента пробрасывается наружу.
    """
    agent_payload = {
        "user_id": headers.get("x-user-id"),
        "text": body.organisation + " | " + body.text,
        "status": AgentStatus.ACTIVE,
        "job_id": headers.get("x-trace-id"),
    }

    client = await APP_CTX.get_postgres_client()
    async with client.get_user_checkpointer() as checkpointer:
        agent_graph = build_builder(agent=APP_CTX.get_agent(), checkpointer=checkpointer)

        langfuse = await APP_CTX.get_langfuse()
        trace = langfuse.client.trace(
            name="chat",
            user_id=headers.get("x-user-id"),
            session_id=headers.get("x-trace-id"),
            input={
                "user_id": headers.get("x-user-id"),
                "organisation": body.organisation,
                "text": body.text,
                "headers": {
                    "x-trace-id": headers.get("x-trace-id"),
                    "x-request-time": headers.get("x-request-time"),
                    "x-source-name": headers.get("x-source-id"),
                    "x-user-id": headers.get("x-user-id"),
                },
            },
            metadata={
                "stage": APP_CONFIG.app.stage,
                "source": headers.get("x-source-id"),
                "request_time": headers.get("x-request-time"),
                "organisation": body.organisation,
            },
            tags=[APP_CONFIG.app.stage, headers.get("x-source-id") or "unknown"],
        )
        current_trace.set(trace)

        config = {
            "configurable": {"thread_id": headers.get("x-user-id")},
            "metadata": {
                "stage": APP_CONFIG.app.stage,
                "langfuse_session_id": headers.get("x-trace-id"),
                "langfuse_user_id": headers.get("x-user-id"),
            },
        }

        try:
            result = await agent_graph.ainvoke(
                input=agent_payload,
                config=config,
            )
            final_answer = result["final_answer"]
            trace.update(output={"response": final_answer})
            logger.debug(f"Ответ сгенерирован. Его длина {len(final_answer)} символов")
            return final_answer
        except Exception as e:
            trace.update(
                output={"error": str(e)},
                metadata={"error_type": e.__class__.__name__},
            )
            raise
        finally:
            current_trace.set(None)


async def _run_generation_bg(job_id: str, body: AgentChatRequest, headers: dict) -> None:
    """Фоновая корутина генерации: пишет в Redis терминальный статус."""
    job_store = await APP_CTX.get_job_store()
    try:
        answer = await asyncio.wait_for(
            _run_generation_inline(body, headers),
            timeout=APP_CONFIG.app.chat_max_generation_seconds,
        )
        await job_store.set_done(job_id, answer)
        logger.info(f"Chat job {job_id} completed")
    except asyncio.TimeoutError:
        logger.warning(f"Chat job {job_id} timed out")
        await job_store.set_error(job_id, "TIMEOUT", "Генерация превысила лимит времени.")
    except Exception as e:
        logger.error(f"Chat job {job_id} failed: {e}")
        await job_store.set_error(job_id, "GENERATION_FAILED", str(e))


@router.post(
    "/test_invoke",
    status_code=status.HTTP_200_OK,
    response_model=LLMAPITestResponse,
    responses={
        status.HTTP_424_FAILED_DEPENDENCY: {
            "description": "Ошибка при попытке обратиться к LLM API",
            "model": schemas.FailedDependecyResponse,
        },
    },
)
async def llm_api_test(
    request: schemas.LLMAPITestRequest,
    headers: dict = Depends(common_headers),
    llm_base_params=Depends(APP_CTX.get_llm_base_params),
):
    llm_client = FallbackChatOpenAI(
        primary_params=llm_base_params,
        fallback_params=APP_CONFIG.llm.fallback_params,
        logger=logger,
    )
    logger.debug(f"Generation an answer based on the givern question... for {headers.get('header_x_user_id')}")
    try:
        answer = llm_client.invoke(request.question)
        logger.debug(f"Generated answer: {answer}")
    except Exception as e:
        logger.error(f"Generation an answer failed with exception: {e}")
        return JSONResponse(
            status_code=status.HTTP_424_FAILED_DEPENDENCY,
            content=FailedDependecyResponse(error_description=str(e)).model_dump(),
        )
    return schemas.LLMAPITestResponse(answer=answer.content)


@router.post("/chat", status_code=status.HTTP_200_OK, response_model=AgentChatResponse)
async def chat(
    request: Request,
    body: AgentChatRequest,
    headers: dict = Depends(common_headers),
):
    """Обработка входящих запросов к API агента.

    Args:
        request: HTTP-запрос FastAPI;
        body: Входящий запрос от пользователя с полезной нагрузкой;
        headers: Заголовок запроса с системной информации.
    """
    rate_limiter = await APP_CTX.get_ratelimiter()
    allowed, current = rate_limiter.check_and_increment(user_id=headers.get("x-user-id"))
    if not allowed:
        ttl = rate_limiter.ttl(user_id=headers.get("x-user-id"))
        return AgentChatResponse(
            response=f""" Вы превысили свой лимит обращений к профсоюзному консультанту. \n
            Возврашайтесь снова через {ttl} секунд.
            """
        )

    logger.debug(f"Длина запроса на входе: {len(body.text)}")

    wants_async = request.headers.get("prefer", "").lower() == "respond-async"
    if not wants_async:
        # Синхронный путь для обратной совместимости.
        try:
            final_answer = await _run_generation_inline(body, headers)
            return AgentChatResponse(response=final_answer)
        except Exception as e:
            logger.critical(
                f"""Ошибка агента:
                     [user_id={headers.get("x-user-id")}],
                     [session_id = {headers.get("x-trace-id")}]
                     [source_id = {headers.get("x-source-id")}]
                     {e}
                    """
            )
            raise

    # Асинхронный путь: создаём фоновую задачу и сразу возвращаем 202.
    job_id = headers.get("x-trace-id")
    if not job_id:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"status": "error", "code": "MISSING_TRACE_ID", "message": "x-trace-id обязателен"},
        )

    job_store = await APP_CTX.get_job_store()
    created = await job_store.create(
        job_id,
        user_id=headers.get("x-user-id"),
        organisation=body.organisation,
    )
    if created:
        task = asyncio.create_task(_run_generation_bg(job_id, body, headers))
        _BG_TASKS.add(task)
        task.add_done_callback(_BG_TASKS.discard)
        logger.info(f"Chat job {job_id} started async")
    else:
        logger.info(f"Chat job {job_id} already exists, returning existing processing status")

    return JSONResponse(
        status_code=status.HTTP_202_ACCEPTED,
        content=ChatJobAccepted(job_id=job_id, status="processing").model_dump(),
    )


@router.get("/chat/{job_id}")
async def chat_status(job_id: str, headers: dict = Depends(common_headers)):
    """Опрос статуса асинхронной задачи генерации."""
    job_store = await APP_CTX.get_job_store()
    job = await job_store.get(job_id)
    if job is None:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=ChatJobStatusResponse(status="not_found", job_id=job_id).model_dump(),
        )

    elapsed_ms = int((time.time() - job["created_at"]) * 1000)
    max_gen_ms = (APP_CONFIG.app.chat_max_generation_seconds + 30) * 1000

    if job["status"] == "processing" and elapsed_ms > max_gen_ms:
        return ChatJobStatusResponse(
            status="error",
            job_id=job_id,
            code="TIMEOUT",
            error="Генерация не завершилась вовремя.",
        ).model_dump()

    if job["status"] == "processing":
        step_message = job.get("current_step_message") or _progress_message(elapsed_ms)
        return ChatJobStatusResponse(
            status="processing",
            job_id=job_id,
            elapsed_ms=elapsed_ms,
            message=step_message,
            current_step=job.get("current_step"),
        ).model_dump()

    if job["status"] == "done":
        return ChatJobStatusResponse(
            status="done",
            job_id=job_id,
            response=job.get("response"),
            current_step=job.get("current_step"),
        ).model_dump()

    return ChatJobStatusResponse(
        status="error",
        job_id=job_id,
        code=job.get("code"),
        error=job.get("error"),
        current_step=job.get("current_step"),
    ).model_dump()
