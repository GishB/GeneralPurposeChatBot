"""
Клиент для вызова UnionChatBot API (/api/v1/chat).

Поддерживает:
- Прямой вызов через /chat (REST)
- Health check через /health
"""

import os
import uuid
from dataclasses import dataclass
from typing import Optional

import httpx


AGENT_BASE_URL = os.getenv("AGENT_BASE_URL", "http://localhost:8080")
DEFAULT_TIMEOUT = float(os.getenv("AGENT_TIMEOUT", "60.0"))


class AgentConnectionError(Exception):
    """Ошибка подключения к агенту."""
    pass


@dataclass
class AgentResponse:
    """Структура ответа агента."""
    response: str
    raw_response: Optional[dict] = None


@dataclass
class AgentRequest:
    """Структура запроса к агенту."""
    message: str
    organisation: str = "ППО Невинномысский Азот"

    def to_chat_payload(self) -> dict:
        """Преобразует в формат для /chat endpoint."""
        return {
            "text": self.message,
            "organisation": self.organisation,
        }


async def call_agent_chat(
    request: AgentRequest,
    user_id: str = "eval-user",
    trace_id: Optional[str] = None,
) -> AgentResponse:
    """
    Вызвать агента через /api/v1/chat endpoint.

    Args:
        request: Запрос к агенту
        user_id: ID пользователя для заголовка x-user-id
        trace_id: ID трейса для заголовка x-trace-id

    Returns:
        AgentResponse с ответом агента

    Raises:
        AgentConnectionError: При ошибке подключения
    """
    trace_id = trace_id or str(uuid.uuid4())

    headers = {
        "Content-Type": "application/json",
        "x-trace-id": trace_id,
        "x-request-time": "2026-04-10T12:00:00+00:00",
        "x-source-name": "eval-client",
        "x-user-id": user_id,
    }

    payload = request.to_chat_payload()

    try:
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
            response = await client.post(
                f"{AGENT_BASE_URL}/api/v1/chat",
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
            data = response.json()

            return AgentResponse(
                response=data.get("response", ""),
                raw_response=data,
            )

    except httpx.ConnectError as e:
        raise AgentConnectionError(
            f"Не удалось подключиться к агенту по адресу {AGENT_BASE_URL}. "
            f"Убедитесь, что агент запущен."
        ) from e
    except httpx.TimeoutException as e:
        raise AgentConnectionError(
            f"Таймаут при запросе к агенту ({AGENT_BASE_URL})."
        ) from e
    except httpx.HTTPStatusError as e:
        raise AgentConnectionError(
            f"Агент вернул ошибку: HTTP {e.response.status_code}. "
            f"Response: {e.response.text[:200]}"
        ) from e


async def health_check(base_url: str = AGENT_BASE_URL, timeout: float = 5.0) -> bool:
    """
    Проверить доступность агента через /health.

    Args:
        base_url: Базовый URL агента
        timeout: Таймаут запроса

    Returns:
        True если агент доступен
    """
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(f"{base_url}/health")
            if response.status_code == 200:
                data = response.json()
                return data.get("status") == "running"
    except Exception:
        pass
    return False


# Алиас для удобства
call_agent = call_agent_chat
