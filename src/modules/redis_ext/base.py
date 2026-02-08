import json
import os
from typing import Any, Dict, Optional

from langchain_core.outputs import Generation
from langchain_redis import RedisSemanticCache
from modules.logger_ext import get_logger

logger = get_logger(__name__)

class RedisAdapter:
    def __init__(self, embeddings: object):
        """
        Инициализация с доступом к SemanticCache индексу через VectorStore.
        """
        self.redis_url = os.getenv("REDIS_URL", "redis://127.0.0.1:6379")
        logger.info(f"Redis url: {self.redis_url}")
        self.embeddings = embeddings
        self.semantic_cache = RedisSemanticCache(
            redis_url=self.redis_url,
            embeddings=embeddings,
            distance_threshold=float(os.getenv("REDIS_THRESHOLD", 0.05)),
            ttl=int(os.getenv("REDIS_TTL", 3600)),
        )
        logger.info(f'REDIS_THRESHOLD: {float(os.getenv("REDIS_THRESHOLD", 0.05))}')
        logger.info(f"REDIS_TTL: {float(os.getenv("REDIS_TTL", 3600))}")


    def save(self, meta_info: str, query: str = "", output: str = "", json_data: Optional[dict] = None):
        """
        output=str в text, json_data=dict в metadata.
        """
        logger.info(f"saving query")
        metadata = {"json": json_data} if json_data else {}
        metadata["query"] = query
        metadata["output"] = output

        json_str = json.dumps(metadata)

        result = [Generation(text=json_str)]
        self.semantic_cache.update(query, meta_info, result)

    def get(self, meta_info: str, query: str = "") -> Optional[Dict[str, Any]]:
        """Возвращает полный dict из JSON в text."""
        logger.info(f"getting query")
        result = self.semantic_cache.lookup(query, meta_info)
        if result:
            try:
                return json.loads(result[0].text)
            except json.JSONDecodeError as e:
                print(f"JSON decode error: {e}")
                return None
        return None
