import os

import redis
from datetime import datetime, timedelta
from typing import Optional


class ChatHistoryManager:
    history_ttl_days = int(os.getenv("HISTORY_USER_TTL_DAYS", 7))
    max_history_length = int(os.getenv("MAX_HISTORY_USER_LENGTH", 10))
    redis_host = os.getenv("REDIS_HOST", "127.0.0.1")
    redis_port = int(os.getenv("REDIS_PORT", 6379))

    def __init__(self, redis_db: int = 1, **kwargs):
        """
        Инициализация менеджера истории чата.

        Args:
            redis_db: номер базы данных Redis
        """

        self.redis_client = redis.StrictRedis(
            host=self.redis_host,
            port=self.redis_port,
            db=redis_db,
            decode_responses=True,  # Автоматически декодируем из bytes в str
        )

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
