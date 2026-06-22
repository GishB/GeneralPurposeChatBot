"""Integration tests for YandexGPT API.

These tests call the real YandexGPT API and may incur costs. Export keys::

    export OPENAI_API_KEY=...
    export OPENAI_FOLDER_ID=...

Run::

    UNION_TEST_MODE=local pytest tests/integration/test_yandex.py -v
"""

import os

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.yandex]


def _skip_if_no_keys():
    """Helper to skip when Yandex credentials are missing."""
    if not os.getenv("OPENAI_API_KEY") or not os.getenv("OPENAI_FOLDER_ID"):
        pytest.skip("OPENAI_API_KEY and OPENAI_FOLDER_ID must be set for Yandex tests")


def test_yandex_direct_invoke(yandex_settings):
    """Direct ChatOpenAI call to YandexGPT returns an answer."""
    _skip_if_no_keys()

    from langchain_openai import ChatOpenAI

    client = ChatOpenAI(**yandex_settings.base_params)
    answer = client.invoke("Скажи 'тест пройден' одной фразой.")
    assert answer.content
    assert "тест" in answer.content.lower() or "test" in answer.content.lower()


@pytest.mark.cluster
def test_yandex_via_api(http_client):
    """``POST /api/v1/test_invoke`` returns a non-empty answer."""
    _skip_if_no_keys()

    response = http_client.post(
        "/api/v1/test_invoke",
        json={"question": "Скажи 'тест пройден' одной фразой.", "generation_params": {}},
        headers={
            "x-trace-id": "yandex-integration-test",
            "x-request-time": "2024-01-01T00:00:00+03:00",
            "x-source-name": "pytest",
            "x-user-id": "yandex-test-user",
        },
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["answer"]
