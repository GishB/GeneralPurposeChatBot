import os

import redis
from datetime import datetime, timedelta
from typing import Optional


class ChatHistoryManager:
    def __init__(
        self,
        redis_host: str = "localhost",
        redis_port: int = 6379,
        redis_db: int = 1,
        history_ttl_days: Optional[int] = None,
        max_history_length: Optional[int] = None,
    ):
        """
        Инициализация менеджера истории чата.

        Args:
            redis_host: хост Redis
            redis_port: порт Redis
            redis_db: номер базы данных Redis
        """
        self.max_history_length = (
            max_history_length
            if max_history_length
            else int(os.environ["MAX_HISTORY_USER_LENGTH"])
        )
        self.history_ttl_days = (
            history_ttl_days
            if history_ttl_days
            else int(os.environ["HISTORY_USER_TTL_DAYS"])
        )
        self.redis_client = redis.StrictRedis(
            host=redis_host,
            port=redis_port,
            db=redis_db,
            decode_responses=True,  # Автоматически декодируем из bytes в str
        )
        self.history_ttl_days = history_ttl_days

    def _get_history_key(self, user_id: str) -> str:
        """Генерирует ключ Redis для хранения истории пользователя."""
        return f"chat_history:{user_id}"

    def get_user_history(self, user_id: str) -> str:
        """
        Получает историю сообщений пользователя.

        Args:
            user_id: идентификатор пользователя

        Returns:
            Строка с историей сообщений или пустая строка, если истории нет
        """
        history_key = self._get_history_key(user_id)
        messages = self.redis_client.lrange(history_key, 0, self.max_history_length - 1)
        return "\n".join(reversed(messages)) if messages else ""

    def add_message_to_history(self, user_id: str, message: str) -> None:
        """
        Добавляет сообщение в историю пользователя.

        Args:
            user_id: идентификатор пользователя
            message: текст сообщения
        """
        if not message.strip():
            return

        history_key = self._get_history_key(user_id)

        # Добавляем сообщение с временной меткой
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        formatted_message = f"[{timestamp}] {message}"

        # Добавляем в начало списка и ограничиваем длину
        self.redis_client.lpush(history_key, formatted_message)
        self.redis_client.ltrim(history_key, 0, self.max_history_length - 1)

        # Устанавливаем TTL если ключ новый
        if self.redis_client.ttl(history_key) == -1:
            self.redis_client.expire(history_key, timedelta(days=self.history_ttl_days))

    def get_formatted_history(self, user_id: str) -> Optional[str]:
        """
        Возвращает историю в формате для вставки в промпт.

        Args:
            user_id: идентификатор пользователя

        Returns:
            Форматированная строка истории или None если история пуста
        """
        history = self.get_user_history(user_id)
        if not history:
            return ""

        return (
            "\n<История диалога с пользователем>\n"
            f"{history}\n"
            "</Конец истории диалога с пользователем>"
        )

    def clear_user_history(self, user_id: str) -> None:
        """
        Очищает историю сообщений пользователя.

        Args:
            user_id: идентификатор пользователя
        """
        history_key = self._get_history_key(user_id)
        self.redis_client.delete(history_key)
