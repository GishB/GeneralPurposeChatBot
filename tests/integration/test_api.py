"""HTTP-level integration tests for the chatbot service.

These tests are cluster-only because they need a running application reachable
via port-forward. Example setup::

    kubectl port-forward -n unionchatbot svc/general-purpose-chatbot 8080:80
    UNION_TEST_MODE=cluster pytest tests/integration/test_api.py -v
"""

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.cluster]


def test_health_endpoint(http_client):
    """``GET /health`` returns running status."""
    response = http_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "running"}


def test_ready_endpoint(http_client):
    """``GET /ready`` returns ready status when all dependencies are healthy."""
    response = http_client.get("/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


def test_info_endpoint(http_client):
    """``GET /info`` returns service metadata."""
    response = http_client.get("/info")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "UnionChatBot"
    assert data["type"] == "REST API"


def test_chat_endpoint_smoke(http_client):
    """``POST /api/v1/chat`` returns a response without hitting rate limit.

    This is a smoke test: it checks that the full pipeline (Redis, Postgres,
    Langfuse, Chroma, YandexGPT) is wired together. The exact answer content is
    not asserted.
    """
    user_id = "integration-test-user"
    response = http_client.post(
        "/api/v1/chat",
        json={
            "text": "Как вступить в профсоюз?",
            "organisation": "ППО Невинномысский Азот",
        },
        headers={
            "x-trace-id": "api-integration-test",
            "x-request-time": "2024-01-01T00:00:00+03:00",
            "x-source-name": "pytest",
            "x-user-id": user_id,
        },
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["response"]
    assert len(data["response"]) >= 4
