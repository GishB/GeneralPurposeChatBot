import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from service.api import create_app
from service.context import APP_CTX


@pytest.fixture
def app(monkeypatch):
    async def _noop(*args, **kwargs):
        pass

    monkeypatch.setattr(APP_CTX, "on_startup", _noop)
    monkeypatch.setattr(APP_CTX, "on_shutdown", _noop)
    return create_app()


@pytest_asyncio.fixture
async def async_client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture
def mock_headers():
    return {
        "x-trace-id": "test-trace-id",
        "x-request-time": "2024-01-01T00:00:00+03:00",
        "x-source-name": "pytest",
        "x-user-id": "test-user-id",
    }
