"""Адаптер для хранения фоновых задач чат-генерации в Redis."""

import json
import time
from typing import Any

import redis.asyncio as aioredis


class ChatJobStore:
    """Хранилище статусов асинхронных задач генерации ответа.

    Использует отдельную Redis БД (по умолчанию db=3) для изоляции от
    семантического кэша (db=0) и rate-limiter (db=2).
    """

    def __init__(
        self,
        host: str,
        port: int,
        password: str | None,
        db: int = 3,
        ttl: int = 900,
        logger: Any | None = None,
        redis: Any | None = None,
    ) -> None:
        self.redis = redis if redis is not None else aioredis.Redis(
            host=host,
            port=port,
            password=password,
            db=db,
            decode_responses=True,
        )
        self.ttl = ttl
        self.logger = logger

    def _key(self, job_id: str) -> str:
        return f"chat:job:{job_id}"

    async def create(self, job_id: str, *, user_id: str, organisation: str) -> bool:
        """Создать запись о задаче, если её ещё нет.

        Returns:
            True если задача создана, False если уже существует.
        """
        payload = {
            "status": "processing",
            "created_at": time.time(),
            "updated_at": time.time(),
            "response": None,
            "error": None,
            "code": None,
            "user_id": user_id,
            "organisation": organisation,
        }
        created = await self.redis.set(self._key(job_id), json.dumps(payload), ex=self.ttl, nx=True)
        if self.logger:
            self.logger.debug(f"ChatJobStore create {job_id}: created={bool(created)}")
        return bool(created)

    async def set_done(self, job_id: str, response: str) -> None:
        """Отметить задачу как выполненную и сохранить ответ."""
        await self._patch(job_id, status="done", response=response)

    async def set_error(self, job_id: str, code: str, error: str) -> None:
        """Отметить задачу как завершившуюся с ошибкой."""
        await self._patch(job_id, status="error", code=code, error=error)

    async def get(self, job_id: str) -> dict[str, Any] | None:
        """Получить текущий статус задачи."""
        raw = await self.redis.get(self._key(job_id))
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError as e:
            if self.logger:
                self.logger.error(f"ChatJobStore corrupted value for {job_id}: {e}")
            return None

    async def health_check(self) -> bool:
        """Проверка доступности Redis."""
        return bool(await self.redis.ping())

    async def _patch(self, job_id: str, **fields: Any) -> None:
        raw = await self.redis.get(self._key(job_id))
        if raw is None:
            if self.logger:
                self.logger.warning(f"ChatJobStore cannot patch missing job {job_id}")
            return
        data = json.loads(raw)
        data.update(fields)
        data["updated_at"] = time.time()
        await self.redis.set(self._key(job_id), json.dumps(data), ex=self.ttl)
