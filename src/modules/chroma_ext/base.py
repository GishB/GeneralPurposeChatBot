from typing import Any, Dict, List

import chromadb
import pandas as pd

from service.logger import LoggerConfigurator

from .utils import BM25Reranker, MyEmbeddingFunction


class ChromaAdapter:
    """Класс позволяющий по http провести взаимодействие с ChromaDB.

    Notes:
        1. Позволяет искать информацию в векторной базе данных исходя из запроса пользователя (RAG).
        2. Позволяет сортировать документы по лексической похожести к запросу пользователя (Rerank)
    """

    def __init__(
        self,
        logger: LoggerConfigurator,
        similarity_filter: float = 1.5,
        reranker_type: str = "bm25",
        text_type: str = "query",
        **kwargs,
    ):
        self.logger = logger
        self.logger.info("Initializing ChromaAdapter")
        self.reranker_type = reranker_type
        if reranker_type == "bm25":
            self.reranker = BM25Reranker(logger=logger)
        else:
            NotImplementedError("Других моделей для задач сортировки документов не существует!")

        self.api_key = kwargs.get("API_KEY", None)
        self.logger.info(f"CHROMA_API_KEY: {self.api_key[:4]}**{self.api_key[-4:]}")
        self.api_url = kwargs.get("API_URL", "https://llm.api.cloud.yandex.net:443/foundationModels/v1/textEmbedding")
        self.logger.info(f"CHROMA_API_URL: {self.api_url}")
        self.folder_id = kwargs.get("FOLDER_ID", None)
        self.logger.info(f"CHROMA_FOLDER_ID: {self.folder_id[:4]}**{self.folder_id[-4:]}")

        self.host = kwargs.get("CHROMA_HOST", "127.0.0.1")
        self.logger.info(f"CHROMA_HOST: {self.host}")

        self.port = kwargs.get("CHROMA_PORT", 8000)
        self.logger.info(f"CHROMA_PORT: {self.port}")

        self.topk_documents = kwargs.get("CHROMA_TOPK_DOCUMENTS", 5)
        self.logger.info(f"CHROMA_TOPK: {self.topk_documents}")

        self.max_rag_documents = kwargs.get("CHROMA_MAX_RAG_DOCUMENTS", 20)
        self.logger.info(f"CHROMA_MAX_RAG: {self.max_rag_documents}")

        self.similarity_filter = similarity_filter
        self.logger.info(f"similarity_filter score: {self.similarity_filter}")

        self.client = chromadb.HttpClient(host=self.host, port=self.port)
        self._embedding_function = None

        self._tokenizer = None
        self._reranker_model = None
        self.text_type = text_type

        if self.folder_id is None:
            raise ValueError("FOLDER_ID must be provided")
        if self.api_key is None:
            raise ValueError("API_KEY must be provided")
        if self.topk_documents >= self.max_rag_documents:
            raise ValueError("TOPK_DOCUMENTS must be less than MAX_RAG_DOCUMENTS")
        self.logger.info("Initialized ChromaAdapter")

    @property
    def embedding_function(self):
        self.logger.debug("embedding_function initialized")
        if self._embedding_function is None:
            self._embedding_function = MyEmbeddingFunction(
                logger=self.logger,
                api_url=self.api_url,
                folder_id=self.folder_id,
                iam_token=self.api_key,
                text_type=self.text_type,
            )
        self.logger.debug("embedding_function initialized")
        return self._embedding_function

    def get_info_from_db(self, query: str, collection_name: str, n_results: int = 30, **kwargs) -> Dict[str, Any]:
        self.logger.debug(f"get_info_from_db called for {collection_name}")
        collection = self.client.get_collection(name=collection_name, embedding_function=self.embedding_function)

        return collection.query(
            query_texts=[query],
            n_results=n_results,
            include=["documents", "metadatas", "distances"],
        )

    def get_filtered_documents(self, data_raw: Dict[str, Any]) -> dict:
        self.logger.info(f"get_filtered_documents: documents number {len(data_raw['documents'])}")
        distances = data_raw["distances"][0]  # Берем первый элемент, так как query_texts=[query]
        documents = data_raw["documents"][0]
        metadatas = data_raw["metadatas"][0]

        return {
            "documents": [
                doc.split("<body>")[-1].replace("</body>", "")
                for doc, dist in zip(documents, distances)
                if dist < self.similarity_filter
            ],
            "metadatas": [metadatas[idx] for idx, dist in enumerate(distances) if dist < self.similarity_filter],
        }

    def get_pairs(self, query: str, documents: List[str]) -> List[List[str]]:
        self.logger.info(f"called get_pairs for {query}")
        return [[query, doc] for doc in documents]

    def apply_reranker(self, query, documents):
        self.logger.info(f"called apply_reranker for {query}")
        if self.reranker_type == "bm25":
            self.reranker.fit(documents)
            return self.reranker.rerank(query=query, top_k=self.topk_documents)
        return None

    def get_info(self, query: str, collection_name: str) -> pd.DataFrame:
        # TO DO: фильтрация по метаданным и потом только query!
        self.logger.info(f"called {query} in get_info for {collection_name}")

        data_raw = self.get_info_from_db(
            query=query,
            collection_name=collection_name,
            n_results=self.max_rag_documents,
        )
        filtered_documents = self.get_filtered_documents(data_raw)

        if not filtered_documents["documents"]:
            self.logger.debug(f"no documents found in {collection_name}")
            return pd.DataFrame.from_dict(
                data={
                    "documents": [],
                    "metadatas": [],
                }
            )

        idx_relevant_documents = self.apply_reranker(query=query, documents=filtered_documents["documents"])
        self.logger.info(f"Finished get_info for {query} returned {len(idx_relevant_documents)} documents")
        return pd.DataFrame.from_dict(
            data={
                "documents": [filtered_documents["documents"][idx] for idx in idx_relevant_documents],
                "metadatas": [filtered_documents["metadatas"][idx] for idx in idx_relevant_documents],
            }
        )
