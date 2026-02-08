"""
Основное ядро API co всеми endpoint-ми.
"""
from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse

from service.context import APP_CTX

from . import schemas
from .schemas import FailedDependencyResponse
from .utils import common_headers

router = APIRouter()
logger = APP_CTX.get_logger()


@router.post(
    "/test_invoke",
    status_code=status.HTTP_200_OK,
    response_model=schemas.GigachatTestInvokeResponse,
    responses={
        status.HTTP_424_FAILED_DEPENDENCY: {
            "description": "Ошибка при взаимодействии с внешней системой",
            "model": schemas.FailedDependencyResponse,
        },
    },
)
async def gigachat_test_invoke(
        # pylint: disable=C0103,W0613,R0914,R0917
        request: schemas.GigachatTestInvokeRequest,
        headers: dict = Depends(common_headers),
        gigachat_base_params=Depends(APP_CTX.get_gigachat_base_params),
):
    """
    Простой пример эндпоинта, в котором можно задать вопрос к GigaChat методом invoke из библитеки langchain.
    """
    gigachat = GigaChat(**gigachat_base_params, **request.generation_params)
    logger.info("Generating an answer based on the given question...")
    try:
        answer = gigachat.invoke(request.question)
        logger.info(f"Generated answer: {answer}")
    except Exception as e:
        # pylint: disable=no-member
        logger.error(f"Request failed: {e.args[0]}", exception=str(e))
        return JSONResponse(
            status_code=status.HTTP_424_FAILED_DEPENDENCY,
            content=FailedDependencyResponse(error_description=str(e)).model_dump(),
        )
    logger.info("Got response from GigaChat")
    return schemas.GigachatTestInvokeResponse(answer=answer.content)


@router.post(
    "/test_embeddings",
    status_code=status.HTTP_200_OK,
    response_model=schemas.GigachatTestEmbeddingsResponse,
    responses={
        status.HTTP_424_FAILED_DEPENDENCY: {
            "description": "Ошибка при взаимодействии с внешней системой",
            "model": schemas.FailedDependencyResponse,
        },
    },
)
async def gigachat_test_embeddings(
        # pylint: disable=C0103,W0613,R0914,R0917
        request: schemas.GigachatTestEmbeddingsRequest,
        headers: dict = Depends(common_headers),
        gigachat_embeddings=Depends(APP_CTX.get_gigachat_embeddings),
):
    """
    Простой пример эндпоинта, в котором можно получить эмбеддинги с помощью GigaChat
    методом embed_query из библитеки langchain.
    """
    logger.info("Performing request for making embeddings...")
    try:
        embeddings = gigachat_embeddings.embed_query(request.query)
        logger.info("Embeddings successfully received.")
    except Exception as e:
        # pylint: disable=no-member
        logger.error(f"Request failed: {e.args[1]} for {e.args[0]}", exception=str(e))
        return JSONResponse(
            status_code=status.HTTP_424_FAILED_DEPENDENCY,
            content=FailedDependencyResponse(error_description=str(e)).model_dump(),
        )
    logger.info("Got response from GigaChat Embeddings")
    return schemas.GigachatTestEmbeddingsResponse(embeddings=embeddings)
