import redis
import numpy as np
import hashlib
import json
import os

from sklearn.metrics.pairwise import cosine_similarity
from typing import Tuple, Optional


class UserRateLimiter:
    """
    Ограничивает количество событий (сообщений) от конкретного user_id
    за фиксированное окно времени.

    Использует атомарные команды Redis INCR + EXPIRE[7].
    """

    USER_QUERY_LIMIT_N = int(os.getenv("USER_QUERY_LIMIT_N", 10))
    USER_QUERY_LIMIT_TTL_SECONDS = int(
        os.getenv("USER_QUERY_LIMIT_TTL_SECONDS", 16 * 3600)
    )
    REDIS_HOST = str(os.getenv("REDIS_HOST", "127.0.0.1"))
    REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
    RATE_LIMIT_TEMPLATE = str(os.getenv("RATE_LIMIT_TEMPLATE", "msg_count:{user_id}"))

    def __init__(self, db: int = 2):
        self.redis = redis.Redis(
            host=self.REDIS_HOST,
            port=self.REDIS_PORT,
            db=db,
            decode_responses=True,
        )

    def check_and_increment(self, user_id: str) -> Tuple[bool, int]:
        """
        Инкрементирует счётчик и проверяет, укладывается ли пользователь в лимит.

        Returns
        -------
        allowed : bool
            True, если пользователь ещё не превысил лимит.
        current : int
            Текущее значение счётчика после инкремента.
        """
        key = self.RATE_LIMIT_TEMPLATE.format(user_id=user_id)

        with self.redis.pipeline(transaction=True) as pipe:
            # 1) Увеличиваем счётчик на 1 (атомарно по отношению к другим INCR)[7]
            current = pipe.incr(key)

            pipe.expire(key, self.USER_QUERY_LIMIT_TTL_SECONDS)

            # Выполняем оба запроса
            current, _ = pipe.execute()

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
        как определено в спецификации TTL[1].
        """
        key = self.RATE_LIMIT_TEMPLATE.format(user_id=user_id)
        return self.redis.ttl(key)


class SemanticRedisCache:
    """Позволяет искать семантически похожие запросы за последние expire_time среди ответов пользователей."""

    api_key = os.getenv("API_KEY", None)
    folder_id = os.getenv("FOLDER_ID", None)
    host = os.getenv("REDIS_HOST", "127.0.0.1")
    port = int(os.getenv("REDIS_PORT", 6379))
    max_entries = int(os.getenv("MAX_CACHED_REQUESTS_N", 1000))
    expire_time = int(os.getenv("EXPIRE_TIME_CACHED_REQUEST_SECONDS", 7200))

    def __init__(
        self,
        db: int = 0,
        similarity_threshold: float = 0.9,
    ):
        self.redis = redis.Redis(host=self.host, port=self.port, db=db)
        self.similarity_threshold = similarity_threshold  # порог косинусной схожести

    def _generate_hash(self, query: str, type_hash: str) -> str:
        """Генерирует ключ на основе хеш запроса

        Args:
            query: text which has been
            type_hash: query or embedding key
        Return:

        """
        return f"{type_hash}:{hashlib.md5(query.encode('utf-8')).hexdigest()}"

    def _store_query_data(
        self, query: str, embedding: np.ndarray, response: str
    ) -> None:
        """Сохраняет запрос, эмбеддинг и ответ в Redis"""
        if isinstance(embedding, list):
            embedding = np.array(embedding, dtype=np.float32)

        # Сохраняем ответ
        query_key = self._generate_hash(query=query, type_hash="query")
        self.redis.setex(
            query_key,
            self.expire_time,
            json.dumps({"query": query, "response": response}),
        )

        # Сохраняем эмбеддинг как bytes
        embedding_key = self._generate_hash(query=query, type_hash="embedding")
        self.redis.setex(embedding_key, self.expire_time, embedding.tobytes())

        # Управляем размером кэша
        self._manage_cache_size()

    def _get_similar_query(self, query_embedding: np.ndarray) -> Optional[dict]:
        """Ищет похожий запрос в кэше"""

        # Ensure query_embedding is 2D
        if isinstance(query_embedding, list):
            query_embedding = np.array(query_embedding, dtype=np.float32)

        if query_embedding.ndim == 1:
            query_embedding = np.expand_dims(query_embedding, axis=0)

        # Получаем все ключи эмбеддингов
        embedding_keys = [key for key in self.redis.scan_iter("embedding:*")]
        if not embedding_keys:
            return None

        # Загружаем все эмбеддинги и преобразуем к 2D
        embeddings = []
        queries = []
        for key in embedding_keys:
            query_key = key.decode().replace("embedding:", "query:")
            query_data = json.loads(self.redis.get(query_key))
            queries.append(query_data)

            embedding_bytes = self.redis.get(key)
            emb = np.frombuffer(embedding_bytes, dtype=np.float32)

            # Ensure each cached embedding is 2D [1, n_features]
            if emb.ndim == 1:
                emb = np.expand_dims(emb, axis=0)
            embeddings.append(emb)

        # Stack all embeddings into [n_samples, n_features]
        embeddings = np.vstack(embeddings)

        # Вычисляем схожесть
        similarities = cosine_similarity(query_embedding, embeddings)[0]
        max_idx = np.argmax(similarities)

        if similarities[max_idx] >= self.similarity_threshold:
            return queries[max_idx]
        return None

    def get(self, query: str, query_embedding: np.ndarray) -> Optional[dict]:
        """Пытается найти похожий запрос в кэше"""
        similar_query = self._get_similar_query(query_embedding)
        if similar_query:
            return similar_query
        return None

    def set(self, query: str, query_embedding: np.ndarray, response: str) -> None:
        """Сохраняет новый запрос в кэш"""
        self._store_query_data(
            query=query, embedding=query_embedding, response=response
        )

    def _manage_cache_size(self):
        """Управление размером кэша (как в предыдущей реализации)"""
        if (
            self.redis.dbsize() > self.max_entries * 2
        ):  # умножаем на 2, так как храним два ключа на запрос
            oldest_keys = self.redis.keys("query:*")[: self.max_entries // 2]
            for key in oldest_keys:
                embedding_key = key.decode().replace("query:", "embedding:")
                self.redis.delete(key)
                self.redis.delete(embedding_key)
