"""
Kimi (Moonshot AI) модель для DeepEval LLM-as-Judge.

Использует OpenAI-compatible API через AsyncOpenAI клиент.
Базовый URL: https://api.moonshot.ai/v1 (international endpoint).
Поддерживает корпоративные сертификаты через те же env, что и GigaChat.
"""

import asyncio
import json
import os
import re
import ssl
from typing import Optional

import httpx
from deepeval.models import DeepEvalBaseLLM
from openai import AsyncOpenAI


def _create_http_client() -> httpx.AsyncClient:
    """
    Создаёт httpx-клиент с корпоративными сертификатами.

    Returns:
        Настроенный httpx.AsyncClient
    """
    ca_path = (
        os.getenv("SSL_CERT_FILE")
        or os.getenv("REQUESTS_CA_BUNDLE")
        or os.getenv("GIGACHAT_CA_BUNDLE_FILEPATH")
    )
    cert_path = os.getenv("GIGACHAT_TLS_CERT_FILEPATH")
    key_path = os.getenv("GIGACHAT_KEY_FILEPATH")
    verify_ssl = os.getenv("KIMI_VERIFY_SSL", "true").lower() not in ("false", "0", "no", "")

    kwargs: dict = {"timeout": 60.0}

    client_cert = None
    if cert_path and key_path and os.path.exists(cert_path) and os.path.exists(key_path):
        client_cert = (cert_path, key_path)

    if verify_ssl and ca_path and os.path.exists(ca_path):
        ssl_context = ssl.create_default_context(cafile=ca_path)
        if client_cert:
            ssl_context.load_cert_chain(certfile=cert_path, keyfile=key_path)
        kwargs["verify"] = ssl_context
    elif verify_ssl:
        kwargs["verify"] = True
    else:
        kwargs["verify"] = False

    if client_cert:
        kwargs["cert"] = client_cert

    return httpx.AsyncClient(**kwargs)


class KimiJudgeModel(DeepEvalBaseLLM):
    """
    Кастомная модель для DeepEval с использованием Kimi (Moonshot AI).

    Используется как judge модель для оценки качества ответов агента.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: str = "moonshot-v1-8k",
    ):
        self._model_name = model
        self._http_client = _create_http_client()

        effective_base_url = base_url or os.getenv(
            "KIMI_BASE_URL", "https://api.moonshot.ai/v1"
        )

        self._client = AsyncOpenAI(
            api_key=api_key or os.getenv("KIMI_API_KEY"),
            base_url=effective_base_url,
            http_client=self._http_client,
        )
        super().__init__()

    def load_model(self) -> AsyncOpenAI:
        """Возвращает инициализированный OpenAI-клиент."""
        return self._client

    @staticmethod
    def _extract_json(text: str) -> str:
        text = text.strip()
        if text.startswith("```"):
            match = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
            if match:
                text = match.group(1).strip()
        return text

    def _try_parse(self, text: str) -> str | None:
        cleaned = self._extract_json(text)
        if not cleaned:
            return None
        try:
            json.loads(cleaned)
            return cleaned
        except json.JSONDecodeError:
            return None

    def generate(self, prompt: str) -> str:
        """Синхронная генерация ответа (обёртка над async)."""
        return asyncio.run(self.a_generate(prompt))

    async def a_generate(self, prompt: str) -> str:
        """Асинхронная генерация ответа с JSON extraction."""
        response = await self._client.chat.completions.create(
            model=self._model_name,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Ты аналитик данных. Сравни тексты и верни результат "
                        "строго в формате JSON."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.0,
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content or ""

        parsed = self._try_parse(content)
        if parsed:
            return parsed

        # Fallback для невалидного JSON
        fallback_reason = (
            f"Kimi returned invalid JSON. Raw: {content[:200]}"
        )
        return json.dumps(
            {
                "score": 0.6,
                "reason": fallback_reason,
            },
            ensure_ascii=False,
        )

    def get_model_name(self) -> str:
        """Возвращает имя модели."""
        return self._model_name
