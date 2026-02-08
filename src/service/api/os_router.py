from importlib.metadata import distribution

from fastapi import APIRouter, status

from . import schemas

router = APIRouter()


@router.get(
    "/health",
    status_code=status.HTTP_200_OK,
    response_model=schemas.HealthResponse,
)
async def health():
    return schemas.HealthResponse(status="running")


@router.get(
    "/info",
    status_code=status.HTTP_200_OK,
    response_model=schemas.InfoResponse,
)
async def info():
    dist = distribution("UnionChatBot")

    return schemas.InfoResponse(
        name=str(dist.metadata["Name"]),
        description=str(dist.metadata["Description"]),
        type="REST API",
        version=str(dist.version),
    )
