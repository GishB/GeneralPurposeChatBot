"""Integration tests for LLM API via OpenRouter.

These tests call the real OpenRouter API and may incur costs. Export keys::

    export LLM_API_KEY=...

Run::

    UNION_TEST_MODE=local pytest tests/integration/test_llm.py -v
"""

import os

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.llm]


def _skip_if_no_key():
    """Helper to skip when LLM credentials are missing."""
    if not os.getenv("LLM_API_KEY"):
        pytest.skip("LLM_API_KEY must be set for LLM tests")


def test_llm_direct_invoke(llm_settings):
    """Direct ChatOpenAI call to OpenRouter returns an answer."""
    _skip_if_no_key()

    from langchain_openai import ChatOpenAI

    client = ChatOpenAI(**llm_settings.base_params)
    answer = client.invoke("Скажи 'тест пройден' одной фразой.")
    assert answer.content
    assert "тест" in answer.content.lower() or "test" in answer.content.lower()


@pytest.mark.cluster
def test_llm_via_api(http_client):
    """``POST /api/v1/test_invoke`` returns a non-empty answer."""
    _skip_if_no_key()

    response = http_client.post(
        "/api/v1/test_invoke",
        json={"question": "Скажи 'тест пройден' одной фразой.", "generation_params": {}},
        headers={
            "x-trace-id": "llm-integration-test",
            "x-request-time": "2024-01-01T00:00:00+03:00",
            "x-source-name": "pytest",
            "x-user-id": "llm-test-user",
        },
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["answer"]
