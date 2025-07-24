import os
from typing import Any

import numpy as np
import requests
import time

from chromadb import Documents, EmbeddingFunction, Embeddings


class MyEmbeddingFunction(EmbeddingFunction):
    api_url = os.getenv(
        "EMBEDDING_API",
        "https://llm.api.cloud.yandex.net:443/foundationModels/v1/textEmbedding",
    )
    folder_id = os.getenv("FOLDER_ID", None)
    iam_token = os.getenv("API_KEY", None)
    time_sleep = float(os.getenv("TIME_SLEEP_RATE_EMBEDDER", 0.01))

    def __init__(
        self,
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
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.iam_token}",
            "x-folder-id": self.folder_id,
        }
        # set default text type doc if not provided
        self.text_type = text_type or "doc"

        # Set default model URIs if not provided
        self.doc_model_uri = (
            doc_model_uri or f"emb://{self.folder_id}/text-search-doc/latest"
        )
        self.query_model_uri = (
            query_model_uri or f"emb://{self.folder_id}/text-search-query/latest"
        )

    def _get_single_embedding(self, text: str) -> np.ndarray:
        """
        Get embedding for a single text.

        Args:
            text: Input text to embed
            text_type: "doc" or "query"

        Returns:
            numpy.ndarray: Embedding vector
        """
        model_uri = (
            self.doc_model_uri if self.text_type == "doc" else self.query_model_uri
        )

        data = {"modelUri": model_uri, "text": text}
        time.sleep(self.time_sleep)
        response = requests.post(self.api_url, json=data, headers=self.headers)
        response.raise_for_status()

        return np.array(response.json()["embedding"])

    def __call__(self, input: Documents) -> Embeddings:
        if isinstance(input, str):
            input = [input]

        embeddings = []
        for text in input:
            embedding = self._get_single_embedding(text)
            embeddings.append(embedding)
        return np.array(embeddings)
