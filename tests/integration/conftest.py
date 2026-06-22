"""Fixtures for integration tests.

Two modes are supported:
- ``local``  -> services are started via testcontainers (Postgres/Redis).
- ``cluster`` -> services are reached via ``kubectl port-forward``; the test
  expects forwarded ports on localhost.

Control the mode with the ``UNION_TEST_MODE`` environment variable.
"""

from __future__ import annotations

import os
import socket
import time
import urllib.parse
from typing import TYPE_CHECKING

import pytest
import pytest_asyncio

if TYPE_CHECKING:
    from testcontainers.postgres import PostgresContainer
    from testcontainers.redis import RedisContainer

INTEGRATION_MODE = os.getenv("UNION_TEST_MODE", "local")

# macOS Docker Desktop does not expose /var/run/docker.sock by default.
# Point testcontainers to the active Docker Desktop socket if DOCKER_HOST is unset.
if not os.getenv("DOCKER_HOST"):
    for _docker_socket in (
        os.path.expanduser("~/.docker/run/docker.sock"),
        "/var/run/docker.sock",
    ):
        if os.path.exists(_docker_socket):
            os.environ["DOCKER_HOST"] = f"unix://{_docker_socket}"
            break


# --------------------------------------------------------------------------- #
# Mode helpers
# --------------------------------------------------------------------------- #


def pytest_configure(config) -> None:
    """Add custom markers so pytest does not complain about unknown marks."""
    config.addinivalue_line("markers", "integration: integration tests against real services")
    config.addinivalue_line("markers", "local: runnable locally with testcontainers")
    config.addinivalue_line("markers", "cluster: requires kubectl port-forward to k8s services")
    config.addinivalue_line("markers", "yandex: calls real YandexGPT API (may incur costs)")
    config.addinivalue_line("markers", "langfuse: requires running Langfuse instance")
    config.addinivalue_line("markers", "chroma: requires ChromaDB instance")


@pytest.fixture(scope="session")
def integration_mode() -> str:
    """Current integration test mode: ``local`` or ``cluster``."""
    return INTEGRATION_MODE


@pytest.fixture(scope="session")
def is_local(integration_mode: str) -> bool:
    return integration_mode == "local"


@pytest.fixture(scope="session")
def is_cluster(integration_mode: str) -> bool:
    return integration_mode == "cluster"


# --------------------------------------------------------------------------- #
# Containers (local mode only)
# --------------------------------------------------------------------------- #


@pytest.fixture(scope="session")
def postgres_container(integration_mode: str):
    """Postgres testcontainer for local mode."""
    if integration_mode != "local":
        yield None
        return

    from testcontainers.postgres import PostgresContainer

    with PostgresContainer(
        image="postgres:15-alpine",
        username="postgres",
        password="postgres",
        dbname="postgres",
    ) as container:
        yield container


@pytest.fixture(scope="session")
def redis_container(integration_mode: str):
    """Redis testcontainer for local mode."""
    if integration_mode != "local":
        yield None
        return

    from testcontainers.redis import RedisContainer

    # Redis Stack includes the RediSearch module required by RedisSemanticCache.
    with RedisContainer(image="redis/redis-stack-server:7.4.0-v0") as container:
        yield container


# --------------------------------------------------------------------------- #
# Service endpoints
# --------------------------------------------------------------------------- #


def _wait_for_port(host: str, port: int, timeout: float = 30.0) -> None:
    """Wait until ``host:port`` becomes reachable."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=1):
                return
        except OSError:
            time.sleep(0.25)
    pytest.fail(f"Port {host}:{port} did not become reachable within {timeout}s")


@pytest.fixture(scope="session")
def postgres_endpoint(postgres_container: PostgresContainer | None, integration_mode: str) -> str:
    """Return a psycopg-compatible connection string.

    In local mode the testcontainer is used. In cluster mode we expect
    ``kubectl port-forward svc/sevenelement-db-rw 5432:5432`` to be active.
    """
    if integration_mode == "local":
        url = postgres_container.get_connection_url()
        return url.replace("+psycopg2", "").replace("+asyncpg", "")
    return "postgresql://postgres:postgres@127.0.0.1:5432/postgres"


@pytest.fixture(scope="session")
def redis_url(redis_container: RedisContainer | None, integration_mode: str) -> str:
    """Redis URL for rate limiter / semantic cache tests.

    In cluster mode we expect ``kubectl port-forward svc/redis-stack 6379:6379``.
    """
    if integration_mode == "local":
        host_exposed = redis_container.get_container_host_ip()
        port_exposed = redis_container.get_exposed_port(6379)
        return f"redis://{host_exposed}:{port_exposed}"
    return os.getenv("REDIS_URL", "redis://127.0.0.1:6379")


# --------------------------------------------------------------------------- #
# Service settings
# --------------------------------------------------------------------------- #


@pytest.fixture(scope="session")
def postgres_settings(postgres_endpoint: str) -> "PostgreSettings":
    """PostgreSettings pointing to the test endpoint."""
    from service.config import PostgreSettings

    parsed = urllib.parse.urlparse(postgres_endpoint)
    path = parsed.path or "/postgres"
    return PostgreSettings(
        PG_USER=parsed.username or "postgres",
        PG_PASSWORD=urllib.parse.unquote(parsed.password or "postgres"),
        POSTGRES_DB=path.lstrip("/"),
        PG_SCHEMA="public",
        PG_HOST=parsed.hostname or "127.0.0.1",
        PG_PORT=parsed.port or 5432,
    )


@pytest.fixture(scope="session")
def redis_settings(redis_url: str) -> "RedisSettings":
    """RedisSettings pointing to the test Redis."""
    from service.config import RedisSettings

    parsed = urllib.parse.urlparse(redis_url)
    return RedisSettings(
        REDIS_HOST=parsed.hostname or "127.0.0.1",
        REDIS_PORT=parsed.port or 6379,
        REDIS_PASSWORD=urllib.parse.unquote(parsed.password or ""),
        REDIS_THRESHOLD=0.99,
        REDIS_TTL=3600,
        USER_COUNTER_LIMIT=1000,
        USER_TTL_LIMIT=60,
    )


@pytest.fixture(scope="session")
def langfuse_settings(integration_mode: str) -> "LangFuseSettings | None":
    """LangFuse settings from environment.

    In cluster mode the values are expected to match ``kubectl port-forward
    svc/langfuse-web 3000:3000``. In local mode Langfuse tests are skipped
    unless ``LANGFUSE_HOST`` is explicitly provided.
    """
    from service.config import LangFuseSettings

    host = os.getenv("LANGFUSE_HOST")
    secret = os.getenv("LANGFUSE_SECRET_KEY")
    public = os.getenv("LANGFUSE_PUBLIC_KEY")

    if integration_mode == "local" and not host:
        return None

    return LangFuseSettings(
        LANGFUSE_HOST=host or "http://127.0.0.1:3000",
        LANGFUSE_SECRET_KEY=secret or "",
        LANGFUSE_PUBLIC_KEY=public or "",
        LANGFUSE_STAGE=os.getenv("LANGFUSE_STAGE", "integration"),
    )


@pytest.fixture(scope="session")
def yandex_settings() -> "YandexGPTSettings":
    """YandexGPT settings from environment."""
    from service.config import YandexGPTSettings

    return YandexGPTSettings(
        MODEL_NAME=os.getenv("MODEL_NAME", "yandexgpt"),
        TEMPERATURE=float(os.getenv("TEMPERATURE", "0.1")),
        LLM_MAX_RETRIES=int(os.getenv("LLM_MAX_RETRIES", "3")),
        OPENAI_API_KEY=os.getenv("OPENAI_API_KEY", ""),
        OPENAI_FOLDER_ID=os.getenv("OPENAI_FOLDER_ID", ""),
        OPENAI_API_BASE=os.getenv("OPENAI_API_BASE", "https://llm.api.cloud.yandex.net/v1"),
    )


@pytest.fixture(scope="session")
def chroma_settings(integration_mode: str) -> "ChromaSettings | None":
    """ChromaDB settings. Local mode is skipped unless explicitly configured."""
    from service.config import ChromaSettings

    host = os.getenv("CHROMA_HOST")
    if integration_mode == "local" and not host:
        return None

    return ChromaSettings(
        CHROMA_HOST=host or "127.0.0.1",
        CHROMA_PORT=int(os.getenv("CHROMA_PORT", "8000")),
        COLLECTION_NAME=os.getenv("COLLECTION_NAME", "PRODUCTION_PROFKOM"),
        OPENAI_API_KEY=os.getenv("OPENAI_API_KEY", ""),
        OPENAI_FOLDER_ID=os.getenv("OPENAI_FOLDER_ID", ""),
    )


# --------------------------------------------------------------------------- #
# Clients
# --------------------------------------------------------------------------- #


@pytest.fixture(scope="session")
def logger_configurator():
    """Logger configured to write to a temp directory."""
    import tempfile

    import pytz

    from service.logger import LoggerConfigurator
    from service.logger.context_vars import ContextVarsContainer

    tmpdir = tempfile.mkdtemp(prefix="unionchatbot-tests-")
    config = LoggerConfigurator(
        log_lvl=20,  # INFO
        log_file_path=os.path.join(tmpdir, "app.log"),
        metric_file_path=os.path.join(tmpdir, "app-metric.log"),
        audit_file_path=os.path.join(tmpdir, "events.log"),
        audit_host_ip="127.0.0.1",
        audit_host_uid="test-uid",
        context_vars_container=ContextVarsContainer(),
        timezone=pytz.UTC,
        rotation="10 MB",
    )
    return config


@pytest.fixture(scope="session")
def logger(logger_configurator):
    return logger_configurator.async_logger


@pytest.fixture
async def postgres_client(postgres_settings, logger):
    """Fresh PostgresClient connected to the test database."""
    from modules.postgres_ext import PostgresClient

    client = PostgresClient(config=postgres_settings, logger=logger)
    yield client
    await client.close()


@pytest.fixture
def redis_rate_limiter(redis_settings, logger):
    """UserRateLimiter backed by the test Redis."""
    from modules.redis_ext.utils import UserRateLimiter

    return UserRateLimiter(
        logger=logger,
        host=redis_settings.host,
        port=redis_settings.port,
        password=redis_settings.password,
        RATE_LIMIT_TEMPLATE=redis_settings.rate_limit_template,
        USER_QUERY_LIMIT_TTL_SECONDS=redis_settings.user_ttl_limit,
        USER_QUERY_LIMIT_N=redis_settings.user_counter_limit,
    )


@pytest.fixture
def mock_embeddings():
    """Fake embeddings object compatible with RedisSemanticCache init."""
    from langchain_core.embeddings import FakeEmbeddings

    return FakeEmbeddings(size=128)


@pytest.fixture
def redis_adapter(redis_settings, mock_embeddings, logger):
    """RedisAdapter backed by the test Redis."""
    from modules.redis_ext import RedisAdapter

    return RedisAdapter(
        logger=logger,
        embeddings=mock_embeddings,
        redis_url=redis_settings.redis_url,
        redis_threshold=redis_settings.redis_threshold,
        redis_ttl=redis_settings.redis_ttl,
    )


@pytest.fixture
def langfuse_client(langfuse_settings, logger):
    """LangfuseClient for the test Langfuse instance."""
    from modules.langfuse_ext import LangfuseClient

    if langfuse_settings is None:
        pytest.skip("Langfuse is not configured for this integration mode")
    return LangfuseClient(app_config=langfuse_settings, logger=logger)


# --------------------------------------------------------------------------- #
# Cluster-only HTTP client
# --------------------------------------------------------------------------- #


@pytest.fixture(scope="session")
def cluster_app_url(integration_mode: str) -> str:
    """Base URL of the port-forwarded chatbot service."""
    if integration_mode != "cluster":
        pytest.skip("Cluster-only fixture")
    return os.getenv("UNION_CHATBOT_URL", "http://127.0.0.1:8080")


@pytest.fixture
def http_client(cluster_app_url: str):
    """Sync HTTP client for the port-forwarded application."""
    from httpx import Client

    _wait_for_port("127.0.0.1", int(urllib.parse.urlparse(cluster_app_url).port or 8080))
    with Client(base_url=cluster_app_url, timeout=60.0) as client:
        yield client
