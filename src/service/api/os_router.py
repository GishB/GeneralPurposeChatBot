from importlib.metadata import distribution

from fastapi import APIRouter, HTTPException, status

from service.context import APP_CTX

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
    "/ready",
    status_code=status.HTTP_200_OK,
    response_model=schemas.ReadinessResponse,
)
async def ready():
    checks = []
    try:
        langfuse = await APP_CTX.get_langfuse()
        checks.append(("langfuse", langfuse.health_check()))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"langfuse not ready: {exc}",
        ) from exc
    try:
        chroma = await APP_CTX.get_chroma()
        checks.append(("chroma", chroma.health_check()))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"chroma not ready: {exc}",
        ) from exc
    try:
        redis = await APP_CTX.get_redis()
        checks.append(("redis", redis.health_check()))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"redis not ready: {exc}",
        ) from exc
    try:
        postgres = await APP_CTX.get_postgres_client()
        checks.append(("postgres", postgres.health_check()))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"postgres not ready: {exc}",
        ) from exc
    try:
        rate_limiter = await APP_CTX.get_ratelimiter()
        checks.append(("rate_limiter", rate_limiter.health_check()))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"rate_limiter not ready: {exc}",
        ) from exc

    for name, result in checks:
        if not result:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"{name} health check returned false",
            )

    return schemas.ReadinessResponse(status="ready")


@router.get(
    "/info",
    status_code=status.HTTP_200_OK,
    response_model=schemas.InfoResponse,
)
async def info():
    dist = distribution("UnionChatBot")

    return schemas.InfoResponse(
        name=str(dist.metadata.get("Name", "UnionChatBot")),
        description=str(dist.metadata.get("Description", "")),
        type="REST API",
        version=str(dist.version),
    )
