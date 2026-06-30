from unittest.mock import MagicMock, patch

import pytest

from modules.llm_ext import FallbackChatOpenAI


class FakeMessage:
    def __init__(self, content):
        self.content = content


class FakePrimary:
    def __init__(self, exc=None):
        self._exc = exc

    def invoke(self, input_value, config=None):
        if self._exc:
            raise self._exc
        return FakeMessage("primary")

    async def ainvoke(self, input_value, config=None):
        if self._exc:
            raise self._exc
        return FakeMessage("primary async")


class FakeFallback:
    def invoke(self, input_value, config=None):
        return FakeMessage("fallback")

    async def ainvoke(self, input_value, config=None):
        return FakeMessage("fallback async")


def _build_wrapper(primary, fallback=None):
    with patch("modules.llm_ext.ChatOpenAI") as mock_cls:
        mock_cls.return_value = primary
        wrapper = FallbackChatOpenAI(
            primary_params={"model": "primary", "openai_api_key": "pk"},
            fallback_params={"model": "fallback", "openai_api_key": "fk"} if fallback else None,
            logger=None,
        )
        if fallback is not None:
            wrapper._fallback = fallback
        return wrapper


def test_fallback_uses_primary_on_success():
    wrapper = _build_wrapper(FakePrimary())
    result = wrapper.invoke("hello")
    assert result.content == "primary"


def test_fallback_switches_to_fallback_on_auth_error():
    from openai import AuthenticationError

    wrapper = _build_wrapper(
        FakePrimary(
            exc=AuthenticationError(
                message="unauthorized",
                response=MagicMock(status_code=401, text="unauthorized"),
                body={"message": "unauthorized"},
            )
        ),
        fallback=FakeFallback(),
    )

    result = wrapper.invoke("hello")
    assert result.content == "fallback"


@pytest.mark.anyio
async def test_fallback_async_switches_to_fallback():
    from openai import RateLimitError

    wrapper = _build_wrapper(
        FakePrimary(
            exc=RateLimitError(
                message="rate limit",
                response=MagicMock(status_code=429, text="rate limit"),
                body={"message": "rate limit"},
            )
        ),
        fallback=FakeFallback(),
    )

    result = await wrapper.ainvoke("hello")
    assert result.content == "fallback async"


def test_fallback_raises_when_no_fallback():
    from openai import AuthenticationError

    wrapper = _build_wrapper(
        FakePrimary(
            exc=AuthenticationError(
                message="unauthorized",
                response=MagicMock(status_code=401, text="unauthorized"),
                body={"message": "unauthorized"},
            )
        ),
        fallback=None,
    )

    with pytest.raises(RuntimeError, match="Primary LLM failed and no fallback"):
        wrapper.invoke("hello")
