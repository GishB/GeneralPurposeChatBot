import numpy as np
import requests
import time

from chromadb import Documents, EmbeddingFunction, Embeddings


class MyEmbeddingFunction(EmbeddingFunction):
    def __init__(
        self,
        api_url: str,
        folder_id: str,
        iam_token: str,
        doc_model_uri: str = None,
        query_model_uri: str = None,
        text_type: str = None,
        time_sleep: float = 0.01,
    ):
        """
        Initialize the embedding function with Yandex GPT API credentials.

        Args:
            api_url: Base URL for the embedding API
            folder_id: Yandex Cloud folder ID
            iam_token: IAM token for authentication
            doc_model_uri: Model URI for document embeddings
            query_model_uri: Model URI for query embeddings
            time_sleep: time between each query to yandex api.
        """
        self.api_url = api_url
        self.folder_id = folder_id
        self.iam_token = iam_token
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {iam_token}",
            "x-folder-id": folder_id,
        }
        # set default text type doc if not provided
        self.text_type = text_type or "doc"
        self.time_sleep = time_sleep

        # Set default model URIs if not provided
        self.doc_model_uri = (
            doc_model_uri or f"emb://{folder_id}/text-search-doc/latest"
        )
        self.query_model_uri = (
            query_model_uri or f"emb://{folder_id}/text-search-query/latest"
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
