import sys
from unittest.mock import AsyncMock, MagicMock

import pytest

from agents.profkom_consultant import AgentStatus
from service.context import APP_CTX


class FakeMessage:
    def __init__(self, content):
        self.content = content


@pytest.mark.anyio
async def test_test_invoke_success(async_client, monkeypatch, mock_headers):
    router_module = sys.modules["service.api.v1.router"]
    monkeypatch.setattr(
        router_module,
        "ChatOpenAI",
        lambda **kwargs: MagicMock(invoke=lambda question: FakeMessage("Mocked answer")),
    )

    payload = {
        "question": "Кто ты воин?",
        "generation_params": {},
    }

    response = await async_client.post("/api/v1/test_invoke", json=payload, headers=mock_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["answer"] == "Mocked answer"


@pytest.mark.anyio
async def test_test_invoke_failed_dependency(async_client, monkeypatch, mock_headers):
    def _raise(*args, **kwargs):
        raise RuntimeError("YandexGPT down")

    router_module = sys.modules["service.api.v1.router"]
    monkeypatch.setattr(
        router_module,
        "ChatOpenAI",
        lambda **kwargs: MagicMock(invoke=_raise),
    )

    payload = {"question": "Кто ты воин?"}
    response = await async_client.post("/api/v1/test_invoke", json=payload, headers=mock_headers)

    assert response.status_code == 424
    data = response.json()
    assert "YandexGPT down" in data["error_description"]


@pytest.mark.anyio
async def test_chat_success(async_client, monkeypatch, mock_headers):
    rate_limiter_mock = MagicMock()
    rate_limiter_mock.check_and_increment.return_value = (True, 1)
    monkeypatch.setattr(APP_CTX, "get_ratelimiter", AsyncMock(return_value=rate_limiter_mock))

    checkpointer_mock = AsyncMock()
    checkpointer_cm = AsyncMock()
    checkpointer_cm.__aenter__ = AsyncMock(return_value=checkpointer_mock)
    checkpointer_cm.__aexit__ = AsyncMock(return_value=None)

    postgres_mock = MagicMock()
    postgres_mock.get_user_checkpointer.return_value = checkpointer_cm
    monkeypatch.setattr(APP_CTX, "get_postgres_client", AsyncMock(return_value=postgres_mock))

    langfuse_mock = MagicMock()
    langfuse_mock.client.trace.return_value = MagicMock()
    monkeypatch.setattr(APP_CTX, "get_langfuse", AsyncMock(return_value=langfuse_mock))

    agent_mock = MagicMock()
    monkeypatch.setattr(APP_CTX, "get_agent", lambda: agent_mock)

    graph_mock = AsyncMock()
    graph_mock.ainvoke.return_value = {"final_answer": "Это ответ агента"}

    router_module = sys.modules["service.api.v1.router"]
    monkeypatch.setattr(router_module, "build_builder", lambda agent, checkpointer: graph_mock)

    payload = {
        "text": "Как вступить в профсоюз?",
        "organisation": "ППО Невинномысский Азот",
    }

    response = await async_client.post("/api/v1/chat", json=payload, headers=mock_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["response"] == "Это ответ агента"

    graph_mock.ainvoke.assert_awaited_once()
    call_kwargs = graph_mock.ainvoke.call_args.kwargs
    assert call_kwargs["input"]["status"] == AgentStatus.ACTIVE


@pytest.mark.anyio
async def test_chat_rate_limit(async_client, monkeypatch, mock_headers):
    rate_limiter_mock = MagicMock()
    rate_limiter_mock.check_and_increment.return_value = (False, 10)
    rate_limiter_mock.ttl.return_value = 42
    monkeypatch.setattr(APP_CTX, "get_ratelimiter", AsyncMock(return_value=rate_limiter_mock))

    payload = {
        "text": "Как вступить в профсоюз?",
        "organisation": "ППО Невинномысский Азот",
    }

    response = await async_client.post("/api/v1/chat", json=payload, headers=mock_headers)

    assert response.status_code == 200
    data = response.json()
    assert "превысили свой лимит" in data["response"]
    assert "42" in data["response"]
