import contextlib
import typing as tp

from fastapi import FastAPI

from .metric_router import router as metric_router
from .middleware import log_requests
from .os_router import router as service_router
from .v1 import router as v1_router


@contextlib.asynccontextmanager
async def lifespan(_) -> tp.AsyncContextManager:
    from service.context import APP_CTX

    await APP_CTX.on_startup()
    yield
    await APP_CTX.on_shutdown()


def create_app() -> FastAPI:
    app_man = FastAPI(title="Basic App", lifespan=lifespan)
    app_man.middleware("http")(log_requests)
    app_man.include_router(service_router, tags=["Test service routes"])
    app_man.include_router(metric_router, tags=["Feedbacks metric routes"])
    app_man.include_router(v1_router, prefix="/api/v1", tags=["service"])
    return app_man


__all__ = ["create_app"]
