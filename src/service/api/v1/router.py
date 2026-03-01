"""
Ядро для работы с endpoints.
"""

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from langchain_openai import ChatOpenAI

# from langgraph.checkpoint.memory import MemorySaver
from agents.profkom_consultant import AgentStatus, build_builder
from service.config import APP_CONFIG
from service.context import APP_CTX

from . import schemas
from .schemas import AgentChatRequest, AgentChatResponse, FailedDependecyResponse, YandexGPTAPITestResponse
from .utils import common_headers

router = APIRouter()
logger = APP_CTX.get_logger()


@router.post(
    "/test_invoke",
    status_code=status.HTTP_200_OK,
    response_model=YandexGPTAPITestResponse,
    responses={
        status.HTTP_424_FAILED_DEPENDENCY: {
            "description": "Ошибка при попытке обратиться к YandexGPTAPI",
            "model": schemas.FailedDependecyResponse,
        },
    },
)
async def yandex_gptapi_test(
    request: schemas.YandexGPTAPITestRequest,
    headers: dict = Depends(common_headers),
    yandexgpt_base_params=Depends(APP_CTX.get_yandexgpt_base_params),
):
    yandexgpt_client = ChatOpenAI(**yandexgpt_base_params)
    logger.debug(f"Generation an answer based on the givern question... for {headers.get('header_x_user_id')}")
    try:
        answer = yandexgpt_client.invoke(request.question)
        logger.debug(f"Generated answer: {answer}")
    except Exception as e:
        logger.error(f"Generation an answer failed with exception: {e}")
        return JSONResponse(
            status_code=status.HTTP_424_FAILED_DEPENDENCY,
            content=FailedDependecyResponse(error_description=str(e)).model_dump(),
        )
    return schemas.YandexGPTAPITestResponse(answer=answer.content)


@router.post("/chat", status_code=status.HTTP_200_OK, response_model=AgentChatResponse)
async def chat(
    request: AgentChatRequest,
    headers: dict = Depends(common_headers),
):
    """Обработка входящих запросов к API агента.

    Args:
        request: Входящий запрос от пользователя с полезной нагрузкой;
        headers: Заголовок запроса с системной информацией;
    """
    rate_limiter = await APP_CTX.get_ratelimiter()
    allowed, current = rate_limiter.check_and_increment(user_id=headers.get("x-user-id"))
    if allowed:
        logger.debug(f"Длина запроса на входе: {len(request.text)}")

        agent_payload = {
            "user_id": headers.get("x-user-id"),
            "text": request.organisation + " | " + request.text,
            "status": AgentStatus.ACTIVE,
        }
        try:
            client = await APP_CTX.get_postgres_client()
            async with client.get_user_checkpointer() as checkpointer:
                agent_graph = build_builder(agent=APP_CTX.get_agent(), checkpointer=checkpointer)

                langfuse = await APP_CTX.get_langfuse()

                config = {
                    "configurable": {"thread_id": headers.get("x-user-id")},
                    "callbacks": [langfuse.handler],
                    "metadata": {
                        "stage": APP_CONFIG.app.stage,
                        "langfuse_session_id": headers.get("x-trace-id"),
                        "langfuse_user_id": headers.get("x-user-id"),
                    },
                }

                result = await agent_graph.ainvoke(
                    input=agent_payload,
                    config=config,
                )
                logger.debug(f"Ответ сгенерирован. Его длина {len(result['final_answer'])} символов")
            return AgentChatResponse(response=result["final_answer"])

        except Exception as e:
            logger.critical(
                f"""Ошибка агента:
                     [user_id={headers.get("x-user-id")}],
                     [session_id = {headers.get("x-trace-id")}]
                     [source_id = {headers.get("x-source-id")}]
                     {e}
                    """
            )
    else:
        ttl = rate_limiter.ttl(user_id=headers.get("x-user-id"))
        return AgentChatResponse(
            response=f""" Вы превысили свой лимит обращений к профсоюзному консультанту. \n
            Возврашайтесь снова через {ttl} секунд.
            """
        )
