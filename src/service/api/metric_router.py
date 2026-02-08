import uuid

from fastapi import APIRouter, Header, status

from service.context import APP_CTX

from . import schemas

router = APIRouter()
logger = APP_CTX.get_logger()


@router.get(
    "/like",
    status_code=status.HTTP_200_OK,
    response_model=schemas.RateResponse,
)
async def like(
    # pylint: disable=C0103,W0613
    header_x_trace_id: str = Header(uuid.uuid4(), alias="x-trace-id"),
):
    logger.metric(
        metric_name="service_likes_total",
        metric_value=1,
    )
    return {"rating_result": "like recorded"}


@router.get(
    "/dislike",
    status_code=status.HTTP_200_OK,
    response_model=schemas.RateResponse,
)
async def dislike(
    # pylint: disable=C0103,W0613
    header_x_trace_id: str = Header(uuid.uuid4(), alias="x-trace-id"),
):
    logger.metric(
        metric_name="service_dislikes_total",
        metric_value=1,
    )
    return {"rating_result": "dislike recorded"}
