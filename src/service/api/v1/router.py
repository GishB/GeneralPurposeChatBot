"""
Ядро для работы с endpoints.
"""

import uuid
from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from langchain_openai import ChatOpenAI

from service.context import APP_CTX
from service.config import APP_CONFIG

from . import schemas
from .schemas import ChatRequest, ChatResponse, ResetRequest, FailedDependecyResponse, YandexGPTAPITestResponse
from .utils import common_headers
from service.exceptions import AgentInternalError
from agents.profkom_consultant import workflow

router = APIRouter()
logger = APP_CTX.get_logger()

@router.post("/test_invoke",
             status_code=status.HTTP_200_OK,
             response_model=YandexGPTAPITestResponse,
             responses=\
                     {
                        status.HTTP_424_FAILED_DEPENDENCY: \
                        {
                         "description": "Ошибка при попытке обратиться к YandexGPTAPI",
                         "model": schemas.FailedDependecyResponse
                        },
                    },
             )
async def yandex_gptapi_test(
        request: schemas.YandexGPTAPITestRequest,
        headers: dict = Depends(common_headers),
        yandexgpt_base_params = Depends(APP_CTX.get_yandexgpt_base_params),
):
        yandexgpt_client = ChatOpenAI(**yandexgpt_base_params)
        logger.info(f"Generation an answer based on the givern question... "
                    f"for {headers.get('header_x_user_id')}")
        try:
            answer = yandexgpt_client.invoke(request.question)
            logger.info(f"Generated answer: {answer}")
        except Exception as e:
            logger.error(f"Generation an answer failed with exception: {e}")
            return JSONResponse(
                status_code=status.HTTP_424_FAILED_DEPENDENCY,
                content=FailedDependecyResponse(error_description=str(e)).model_dump(),
            )
        return schemas.YandexGPTAPITestResponse(answer=answer.content)