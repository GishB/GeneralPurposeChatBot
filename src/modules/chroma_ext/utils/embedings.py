import os
import time
from typing import Any

import numpy as np
import requests

from itertools import islice
from typing import Iterable
from requests.exceptions import ConnectTimeout, ReadTimeout, Timeout
from chromadb import Documents, EmbeddingFunction, Embeddings
from service.logger import LoggerConfigurator


class MyEmbeddingFunction(EmbeddingFunction):
    def __init__(
        self,
        logger: LoggerConfigurator,
        doc_model_uri: str = None,
        query_model_uri: str = None,
        text_type: str = None,
        *args: Any,
        **kwargs: Any,
    ):
        """
        Initialize the embedding function with Yandex GPT API credentials.

        Args:
            doc_model_uri: Model URI for document embeddings
            query_model_uri: Model URI for query embeddings
            time_sleep: time between each query to yandex api.
        """
        super().__init__(*args, **kwargs)
        self.logger = logger
        self.api_url = os.getenv(
            "EMBEDDING_API",
            "https://llm.api.cloud.yandex.net:443/foundationModels/v1/textEmbedding",
        ) or kwargs.get("api_url")
        self.logger.info(f"api_url: {self.api_url}")

        self.folder_id = kwargs.get("folder_id")
        self.logger.info(f"iam_token: {self.folder_id[:4]}***{self.folder_id[-4:]}")

        self.iam_token = kwargs.get("iam_token")
        self.logger.info(f"iam_token: {self.iam_token[:4]}***{self.iam_token[-4:]}")

        self.time_sleep = kwargs.get("time_sleep", 0.05)
        self.logger.info(f"time_sleep: {self.time_sleep}")

        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.iam_token}",
            "x-folder-id": self.folder_id,
        }
        # set default text type doc if not provided
        self.text_type = text_type or "doc"
        self.logger.info(f"text_type: {self.text_type}")

        # Set default model URIs if not provided
        self.doc_model_uri = doc_model_uri or f"emb://{self.folder_id}/text-search-doc/latest"
        self.logger.info(f"doc_model_uri: {self.doc_model_uri}")
        self.query_model_uri = query_model_uri or f"emb://{self.folder_id}/text-search-query/latest"
        self.logger.info(f"query_model_uri: {self.query_model_uri}")

        # Set default retry logic and process long documents
        self.max_retries = kwargs.get("max_retries", 5)
        self.request_timeout = kwargs.get("request_timeout", 1)  # seconds
        self.batch_size = kwargs.get("batch_size", 16)
        self.sleep_between_batches = kwargs.get("sleep_between_batches", 2)

    def _get_single_embedding(self, text: str) -> np.ndarray:
        """Получить эмбеддинг для одного текста с ретраями и обрезкой по длине."""
        model_uri = self.doc_model_uri if self.text_type == "doc" else self.query_model_uri

        data = {"modelUri": model_uri, "text": text}

        for attempt in range(1, self.max_retries + 1):
            try:
                # базовый sleep под RPS
                time.sleep(self.time_sleep)

                resp = requests.post(
                    self.api_url,
                    json=data,
                    headers=self.headers,
                    timeout=self.request_timeout,
                )

                # 2xx — ок сразу
                if resp.ok:
                    return np.array(resp.json()["embedding"])

                # 429 / 5xx — временные, пробуем ещё раз
                if resp.status_code in (429, 500, 502, 503, 504):
                    self.logger.warning(
                        f"Embedding transient error {resp.status_code} on attempt "
                        f"{attempt}/{self.max_retries}: {resp.text[:300]!r}"
                    )
                    # экспоненциальный backoff c небольшим множителем
                    backoff = self.time_sleep * (2**attempt)
                    time.sleep(backoff)
                    continue

                # Остальные 4xx — логическая ошибка, ретраить нет смысла
                self.logger.error(
                    f"Embedding request failed: status={resp.status_code}, "
                    f"body={resp.text[:500]!r}"
                )
                self.logger.error(f"Model URI: {model_uri}")
                self.logger.error(f"Text length: {len(text)}")
                resp.raise_for_status()

            except (ConnectTimeout, ReadTimeout, Timeout) as e:
                self.logger.warning(
                    f"Embedding timeout on attempt {attempt}/{self.max_retries}: {e}"
                )
                if attempt == self.max_retries:
                    raise
                backoff = self.time_sleep * (2**attempt)
                time.sleep(backoff)

        # Если все попытки не удались, явно падаем
        raise RuntimeError(
            f"Failed to get embedding after {self.max_retries} attempts "
            f"for text of length {len(text)}"
        )

    @staticmethod
    def _batched(iterable: Iterable[str], n: int):
        """batched('ABCDEFG', 3) -> ABC DEF G"""
        it = iter(iterable)
        while batch := list(islice(it, n)):
            yield batch


    def __call__(self, input: Documents) -> Embeddings:
        if isinstance(input, str):
            input = [input]

        embeddings = []

        for batch_idx, batch in enumerate(self._batched(input, self.batch_size)):
            if batch_idx != 0:
                time.sleep(self.sleep_between_batches)

            self.logger.info(
                f"Embedding batch {batch_idx}, size={len(batch)}"
            )
            for text in batch:
                emb = self._get_single_embedding(text)
                embeddings.append(emb)

        return np.array(embeddings)

