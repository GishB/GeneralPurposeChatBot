import redis
from typing import Tuple

class UserRateLimiter:
    """
    Ограничивает количество событий (сообщений) от конкретного user_id
    за фиксированное окно времени.

    Использует атомарные команды Redis INCR + EXPIRE[7].
    """

    def __init__(self, logger, **kwargs):
        self.logger = logger
        self.logger.info("Create Redis UserRateLimiter")
        self.USER_QUERY_LIMIT_N = kwargs.get("USER_QUERY_LIMIT_N", 10)
        self.USER_QUERY_LIMIT_TTL_SECONDS = int(kwargs.get("USER_QUERY_LIMIT_TTL_SECONDS", 20 * 3600))
        self.RATE_LIMIT_TEMPLATE = kwargs.get("RATE_LIMIT_TEMPLATE", "msg_count:{user_id}")

        self.logger.info(f"Limit template: {self.RATE_LIMIT_TEMPLATE} ")
        self.logger.info(f"Query limit: {self.USER_QUERY_LIMIT_N}")
        self.logger.info(f"Expire time: {self.USER_QUERY_LIMIT_TTL_SECONDS}")
        self.logger.info(f"Host: {kwargs.get('host', '127.0.0.1')}")
        self.logger.info(f"Port: {kwargs.get('port', 6379)}")
        self.logger.info(f"DB number: {kwargs.get('db', 0)}")
        self.logger.info(f"decode_responses: {kwargs.get('decode_responses', True)}")

        self.redis = redis.Redis(
            host=kwargs.get("host", "127.0.0.1"),
            port=kwargs.get("port", 6379),
            db=kwargs.get("db", 2),
            decode_responses=kwargs.get("decode_responses", True),
        )
        self.logger.info("Redis UserRateLimiter has been initialized")

    def check_and_increment(self, user_id: str) -> Tuple[bool, int]:
        """
        Инкрементирует счётчик и проверяет, укладывается ли пользователь в лимит.

        Arg:
            user_id: уникальный идентификатор пользователя.

        Returns:
            Tuple, где первое значение True, если пользователь ещё не превысил лимит,
            и текущее значение счётчика после инкремента.
        """
        key = self.RATE_LIMIT_TEMPLATE.format(user_id=user_id)

        with self.redis.pipeline(transaction=True) as pipe:
            pipe.incr(key)
            pipe.ttl(key)
            results = pipe.execute()
            current, ttl = results

        if current == 1 or ttl == -1 or ttl == -2:
            self.redis.expire(key, self.USER_QUERY_LIMIT_TTL_SECONDS)

        allowed = current <= self.USER_QUERY_LIMIT_N
        return allowed, current

    def get_remaining(self, user_id: str) -> int:
        """
        Сколько сообщений осталось до лимита. Если ключа нет — возвращает max.
        """
        key = self.RATE_LIMIT_TEMPLATE.format(user_id=user_id)
        value = self.redis.get(key)
        value = int(value) if value is not None else 0
        remaining = max(self.USER_QUERY_LIMIT_N - value, 0)
        return remaining

    def reset_counter(self, user_id: str) -> None:
        """
        Принудительно обнуляет счётчик (например, администраторская команда).
        """
        key = self.RATE_LIMIT_TEMPLATE.format(user_id=user_id)
        self.redis.delete(key)

    def ttl(self, user_id: str) -> int:
        """
        Возвращает оставшийся TTL ключа или -2 (нет ключа) / -1 (без TTL),
        как определено в спецификации.
        """
        key = self.RATE_LIMIT_TEMPLATE.format(user_id=user_id)
        return self.redis.ttl(key)

    def health_check(self) -> bool:
        """ Simple ping check

        Returns:
            check that redis is healthy
        """
        pong = self.redis.ping()
        if not pong:
            self.logger.warning("Redis PING returned False")
            return False
        return True
