"""
Здесь можно организовать бизнес-логику, специфичную для конкретного сервиса.
"""
import uuid
from fastapi import APIRouter, Depends, status

from service.context import APP_CTX
from service.config import APP_CONFIG

from . import schemas
from .utils import common_headers
from modules.postgres_ext import PostgreSaver
from modules.langfuse_ext import AsyncLangfuseClient
from agents.profkom_consultant import workflow
from service.exceptions import AgentInternalError

router = APIRouter()
logger = APP_CTX.get_logger()


@router.post(
    "/chat",
    status_code=status.HTTP_200_OK,
    response_model=schemas.ChatResponse,
    responses={
        status.HTTP_424_FAILED_DEPENDENCY: {
            "description": "Ошибка при взаимодействии с внешней системой"
        },
    },
)
async def chat(
        request: schemas.ChatRequest,
        headers: dict = Depends(common_headers),
        postgre: PostgreSaver = Depends(lambda: APP_CTX.postgre),
        langfuse: AsyncLangfuseClient = Depends(lambda: APP_CTX.langfuse),
):
    """
    Главный endpoint диалога с профсоюзным агентом.

    Args:
        request: Сообщение пользователя (полезная загрузка);
        headers: Заголовки запроса с метаданными (x-user-id; x-client-id и так далее);
        postgre: Экземпляр класса для работы базой данных;
        langfuse: Экземпляр класса для работы с Langfuse для трассировки;

    Returns:
         Ответ от агента в формате.
    """
    logger.info(f"Запрос к агенту от user_id: {headers.get('user_id')}")

    callbacks = []
    try:
        if langfuse and langfuse.client:
            trace_name = APP_CONFIG.app.app_name
            langfuse_callback = langfuse.get_cb_handler(trace_name)
            callbacks.append(langfuse_callback)
        else:
            logger.error("Langfuse клиент недоступен")
            raise AgentInternalError("Система трассировки недоступна")
    except Exception as trace_error:
        logger.error(f"Ошибка Langfuse callback: {trace_error}")
        raise AgentInternalError("Ошибка инициализации трассировки")

    try:
        langfuse_trace_id = uuid.uuid64().hex[:32]
        async with postgre.get_user_checkpointer() as checkpointer:
            agent_graph = await workflow.graph_builder(checkpointer)

            config = \
            {
                "configurable": \
                {
                    "thread_id": headers["x-user-id"]
                },
                "callbacks": callbacks,
                "run_id": langfuse_trace_id,
                "metadata": \
                {
                    "stage": APP_CONFIG.langfuse.stage,
                    "langfuse_user_id": headers["x-user-id"],
                    "langfuse_session_id": headers["x-session-id"],
                    "client_id": headers["x-client-id"],
                    "endpoint": "/chat"
                },
            }

            result = await agent_graph.ainvoke\
            (
                {"user_question": request.message},
                config=config,
            )

            logger.info(f"Ответ сгенерирован: {len(result['final_answer'])} символов")
            return schemas.ChatResponse\
                (
                response=result['final_answer'],
                langfuse_trace_id=langfuse_trace_id,
                **headers,
                )

    except Exception as error:
        logger.critical \
            (
                f"Ошибка агента [user_id={headers['x-user-id']}, session_id={headers['x-session-id']}: error: {error}]",
                exc_info=True,
            )
        raise AgentInternalError("Неожиданная ошибка агента")
