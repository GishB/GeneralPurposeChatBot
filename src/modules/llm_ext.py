"""Fallback LLM wrapper for OpenRouter → YandexGPT failover."""

from __future__ import annotations

import functools
from typing import Any, Callable

from langchain_core.callbacks.manager import AsyncCallbackManagerForLLMRun, CallbackManagerForLLMRun
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langchain_core.outputs import ChatResult
from langchain_openai import ChatOpenAI
from openai import AuthenticationError, PermissionDeniedError, RateLimitError


class FallbackChatOpenAI(BaseChatModel):
    """ChatOpenAI-совместимая обёртка с fallback на YandexGPT.

    При ошибках первичного провайдера (OpenRouter), таких как 401, 403, 429
    или сетевые сбои, автоматически переключается на YandexGPT.
    """

    primary_params: dict[str, Any]
    fallback_params: dict[str, Any] | None = None
    logger: Any | None = None

    def __init__(
        self,
        primary_params: dict[str, Any],
        fallback_params: dict[str, Any] | None = None,
        logger: Any | None = None,
    ):
        super().__init__(
            primary_params=primary_params,
            fallback_params=fallback_params,
            logger=logger,
        )
        self._primary = ChatOpenAI(**primary_params)
        self._fallback: ChatOpenAI | None = None
        if fallback_params:
            self._fallback = ChatOpenAI(**fallback_params)

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        """Синхронный вызов для BaseChatModel — делегирует primary с fallback."""
        try:
            return self._primary._generate(messages, stop=stop, run_manager=run_manager, **kwargs)
        except (AuthenticationError, PermissionDeniedError, RateLimitError) as e:
            self._log("warning", f"Primary LLM failed ({e.__class__.__name__}), trying fallback")
        except Exception as e:  # noqa: BLE001
            self._log("error", f"Primary LLM unexpected error: {e}")
        if self._fallback is None:
            raise RuntimeError("Primary LLM failed and no fallback configured")
        return self._fallback._generate(messages, stop=stop, run_manager=run_manager, **kwargs)

    async def _agenerate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: AsyncCallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        """Асинхронный вызов для BaseChatModel — делегирует primary с fallback."""
        try:
            return await self._primary._agenerate(messages, stop=stop, run_manager=run_manager, **kwargs)
        except (AuthenticationError, PermissionDeniedError, RateLimitError) as e:
            self._log("warning", f"Primary LLM async failed ({e.__class__.__name__}), trying fallback")
        except Exception as e:  # noqa: BLE001
            self._log("error", f"Primary LLM unexpected async error: {e}")
        if self._fallback is None:
            raise RuntimeError("Primary LLM async failed and no fallback configured")
        return await self._fallback._agenerate(messages, stop=stop, run_manager=run_manager, **kwargs)

    def _log(self, level: str, message: str) -> None:
        if self.logger is None:
            return
        log_func = getattr(self.logger, level, None)
        if log_func:
            log_func(message)

    @property
    def _llm_type(self) -> str:
        return "fallback_chat_openai"

    @property
    def _identifying_params(self) -> dict[str, Any]:
        return {"primary": self.primary_params, "fallback": self.fallback_params}

    def invoke(self, input_value: Any, config: Any | None = None) -> BaseMessage:
        return self._try_invoke("invoke", input_value, config)

    async def ainvoke(self, input_value: Any, config: Any | None = None) -> BaseMessage:
        method: Callable[..., Any] = self._primary.ainvoke
        try:
            if config is not None:
                return await method(input_value, config=config)
            return await method(input_value)
        except (AuthenticationError, PermissionDeniedError, RateLimitError) as e:
            self._log("warning", f"Primary LLM async failed ({e.__class__.__name__}), trying fallback")
            return await self._afallback_invoke("ainvoke", input_value, config)
        except Exception as e:  # noqa: BLE001
            self._log("error", f"Primary LLM unexpected async error: {e}")
            return await self._afallback_invoke("ainvoke", input_value, config)

    def _try_invoke(
        self,
        method_name: str,
        input_value: Any,
        config: Any | None = None,
    ) -> BaseMessage:
        """Вызывает метод primary, при ошибках fallback."""
        method: Callable[..., BaseMessage] = getattr(self._primary, method_name)
        try:
            if config is not None:
                return method(input_value, config=config)
            return method(input_value)
        except (AuthenticationError, PermissionDeniedError, RateLimitError) as e:
            self._log("warning", f"Primary LLM failed ({e.__class__.__name__}), trying fallback")
            return self._fallback_invoke(method_name, input_value, config)
        except Exception as e:  # noqa: BLE001
            self._log("error", f"Primary LLM unexpected error: {e}")
            return self._fallback_invoke(method_name, input_value, config)

    def _fallback_invoke(
        self,
        method_name: str,
        input_value: Any,
        config: Any | None = None,
    ) -> BaseMessage:
        """Вызывает fallback LLM, если он сконфигурирован."""
        if self._fallback is None:
            raise RuntimeError("Primary LLM failed and no fallback configured")

        method: Callable[..., BaseMessage] = getattr(self._fallback, method_name)
        if config is not None:
            return method(input_value, config=config)
        return method(input_value)

    async def _afallback_invoke(
        self,
        method_name: str,
        input_value: Any,
        config: Any | None = None,
    ) -> BaseMessage:
        if self._fallback is None:
            raise RuntimeError("Primary LLM failed and no fallback configured")

        method: Callable[..., Any] = getattr(self._fallback, method_name)
        if config is not None:
            return await method(input_value, config=config)
        return await method(input_value)

    def __getattr__(self, name: str) -> Any:
        """Проксирует остальные атрибуты к primary-клиенту."""
        return getattr(self._primary, name)

    def bind(self, *args: Any, **kwargs: Any) -> Any:
        """Поддержка bind/bind_tools LangChain."""
        bound_primary = self._primary.bind(*args, **kwargs)
        if self._fallback is None:
            return bound_primary
        bound_fallback = self._fallback.bind(*args, **kwargs)

        new = FallbackChatOpenAI(
            primary_params=self.primary_params,
            fallback_params=self.fallback_params,
            logger=self.logger,
        )
        new._primary = bound_primary
        new._fallback = bound_fallback
        functools.update_wrapper(new.invoke, bound_primary.invoke)
        return new

    def with_structured_output(self, *args: Any, **kwargs: Any) -> Any:
        """Проксирует with_structured_output на primary, fallback не применяется."""
        return self._primary.with_structured_output(*args, **kwargs)

    def with_fallbacks(self, *args: Any, **kwargs: Any) -> Any:
        """Проксирует with_fallbacks на primary."""
        return self._primary.with_fallbacks(*args, **kwargs)
