import sys
from unittest.mock import AsyncMock, MagicMock

import pytest

from agents.profkom_consultant import AgentStatus
from service.context import APP_CTX


class FakeMessage:
    def __init__(self, content):
        self.content = content


@pytest.fixture
def async_headers(mock_headers):
    """Заголовки с Prefer: respond-async для тестирования async-пути."""
    headers = dict(mock_headers)
    headers["prefer"] = "respond-async"
    return headers


@pytest.mark.anyio
async def test_test_invoke_success(async_client, monkeypatch, mock_headers):
    router_module = sys.modules["service.api.v1.router"]
    monkeypatch.setattr(
        router_module,
        "FallbackChatOpenAI",
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
        raise RuntimeError("LLM down")

    router_module = sys.modules["service.api.v1.router"]
    monkeypatch.setattr(
        router_module,
        "FallbackChatOpenAI",
        lambda **kwargs: MagicMock(invoke=_raise),
    )

    payload = {"question": "Кто ты воин?"}
    response = await async_client.post("/api/v1/test_invoke", json=payload, headers=mock_headers)

    assert response.status_code == 424
    data = response.json()
    assert "LLM down" in data["error_description"]


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

    trace_mock = MagicMock()
    langfuse_mock = MagicMock()
    langfuse_mock.client.trace.return_value = trace_mock
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

    langfuse_mock.client.trace.assert_called_once()
    trace_call_kwargs = langfuse_mock.client.trace.call_args.kwargs
    assert trace_call_kwargs["name"] == "chat"
    assert trace_call_kwargs["user_id"] == "test-user-id"
    assert trace_call_kwargs["session_id"] == "test-trace-id"
    assert trace_call_kwargs["input"]["organisation"] == "ППО Невинномысский Азот"
    assert trace_call_kwargs["input"]["text"] == "Как вступить в профсоюз?"
    assert trace_call_kwargs["metadata"]["source"] == "pytest"
    assert "pytest" in trace_call_kwargs["tags"]

    trace_mock.update.assert_called_once()
    update_call_kwargs = trace_mock.update.call_args.kwargs
    assert update_call_kwargs["output"]["response"] == "Это ответ агента"


@pytest.mark.anyio
async def test_chat_async_creates_job_and_returns_status(async_client, monkeypatch, async_headers):
    rate_limiter_mock = MagicMock()
    rate_limiter_mock.check_and_increment.return_value = (True, 1)
    monkeypatch.setattr(APP_CTX, "get_ratelimiter", AsyncMock(return_value=rate_limiter_mock))

    # Мок job store с контролируемым состоянием
    job_state = {}

    class FakeJobStore:
        async def create(self, job_id, *, user_id, organisation):
            if job_id in job_state:
                return False
            job_state[job_id] = {
                "status": "processing",
                "created_at": 0,
                "updated_at": 0,
                "response": None,
                "error": None,
                "code": None,
                "user_id": user_id,
                "organisation": organisation,
                "current_step": None,
                "current_step_message": None,
            }
            return True

        async def set_done(self, job_id, response):
            job_state[job_id]["status"] = "done"
            job_state[job_id]["response"] = response

        async def set_error(self, job_id, code, error):
            job_state[job_id]["status"] = "error"
            job_state[job_id]["code"] = code
            job_state[job_id]["error"] = error

        async def set_step(self, job_id, step_key, message):
            job_state[job_id]["current_step"] = step_key
            job_state[job_id]["current_step_message"] = message

        async def get(self, job_id):
            return job_state.get(job_id)

        async def health_check(self):
            return True

    monkeypatch.setattr(APP_CTX, "get_job_store", AsyncMock(return_value=FakeJobStore()))

    # Подменяем фоновую генерацию, чтобы сразу отметить задачу выполненной
    router_module = sys.modules["service.api.v1.router"]

    async def fake_bg(job_id, body, headers):
        await FakeJobStore().set_done(job_id, "Async answer")

    monkeypatch.setattr(router_module, "_run_generation_bg", fake_bg)

    payload = {
        "text": "Как вступить в профсоюз?",
        "organisation": "ППО Невинномысский Азот",
    }

    response = await async_client.post("/api/v1/chat", json=payload, headers=async_headers)
    assert response.status_code == 202
    data = response.json()
    assert data["job_id"] == async_headers["x-trace-id"]
    assert data["status"] == "processing"

    status_response = await async_client.get(f"/api/v1/chat/{async_headers['x-trace-id']}", headers=async_headers)
    assert status_response.status_code == 200
    status_data = status_response.json()
    assert status_data["status"] == "done"
    assert status_data["response"] == "Async answer"


@pytest.mark.anyio
async def test_chat_async_idempotent(async_client, monkeypatch, async_headers):
    rate_limiter_mock = MagicMock()
    rate_limiter_mock.check_and_increment.return_value = (True, 1)
    monkeypatch.setattr(APP_CTX, "get_ratelimiter", AsyncMock(return_value=rate_limiter_mock))

    job_state = {}

    class FakeJobStore:
        async def create(self, job_id, *, user_id, organisation):
            if job_id in job_state:
                return False
            job_state[job_id] = {"status": "processing"}
            return True

        async def get(self, job_id):
            return job_state.get(job_id)

        async def health_check(self):
            return True

    monkeypatch.setattr(APP_CTX, "get_job_store", AsyncMock(return_value=FakeJobStore()))

    router_module = sys.modules["service.api.v1.router"]
    bg_calls = []

    async def fake_bg(job_id, body, headers):
        bg_calls.append(job_id)

    monkeypatch.setattr(router_module, "_run_generation_bg", fake_bg)

    payload = {
        "text": "Как вступить в профсоюз?",
        "organisation": "ППО Невинномысский Азот",
    }

    response1 = await async_client.post("/api/v1/chat", json=payload, headers=async_headers)
    response2 = await async_client.post("/api/v1/chat", json=payload, headers=async_headers)

    assert response1.status_code == 202
    assert response2.status_code == 202
    assert len(bg_calls) == 1


@pytest.mark.anyio
async def test_chat_status_not_found(async_client, monkeypatch, async_headers):
    rate_limiter_mock = MagicMock()
    rate_limiter_mock.check_and_increment.return_value = (True, 1)
    monkeypatch.setattr(APP_CTX, "get_ratelimiter", AsyncMock(return_value=rate_limiter_mock))

    class FakeJobStore:
        async def get(self, job_id):
            return None

        async def health_check(self):
            return True

    monkeypatch.setattr(APP_CTX, "get_job_store", AsyncMock(return_value=FakeJobStore()))

    response = await async_client.get("/api/v1/chat/non-existent", headers=async_headers)
    assert response.status_code == 404
    assert response.json()["status"] == "not_found"


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


