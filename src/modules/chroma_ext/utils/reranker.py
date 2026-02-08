from typing import List

import numpy as np
import tiktoken
from rank_bm25 import BM25Okapi

from service.logger import LoggerConfigurator


class BM25Reranker:
    def __init__(self, logger: LoggerConfigurator, tokenizer_name: str = "gpt-3.5-turbo"):
        self.logger = logger
        self.logger.info(f"Initializing BM25Reranker with {tokenizer_name}")
        self.tokenizer = tiktoken.encoding_for_model(tokenizer_name)
        self.bm25 = None
        self.logger.info("BM25Reranker initialized")

    def preprocess(self, text: str) -> List[str]:
        """Токенизация текста и возвращение строковых токенов."""
        self.logger.debug("Preprocessing over text")
        tokens = self.tokenizer.encode(text.lower())
        # Преобразуем токены обратно в строки для совместимости с BM25
        token_strings = []
        for token in tokens:
            token_str = self.tokenizer.decode([token])
            token_str = token_str.strip()
            if token_str and len(token_str) > 0:
                token_strings.append(token_str)
        self.logger.debug("Finished preprocessing over text")
        return token_strings

    def fit(self, documents: List[str]):
        """Обучение модели на корпусе документов для текущего запроса."""
        self.logger.info(f"Fitting {len(documents)} documents")
        tokenized_docs = [self.preprocess(doc) for doc in documents]
        self.bm25 = BM25Okapi(tokenized_docs)

    def rerank(self, query: str, top_k: int = 3) -> List[int]:
        """Возвращает индексы наиболее релевантных документов из представленных."""
        self.logger.info(f"Reranking | top_k={top_k}")
        if self.bm25 is None:
            raise ValueError("BM25 model not fitted. Call fit() first.")

        # Токенизируем запрос
        tokenized_query = self.preprocess(query)

        # Получаем оценки для всех документов
        scores = self.bm25.get_scores(tokenized_query)

        # Находим индексы с наибольшими оценками
        top_indices = np.argsort(scores)[::-1][:top_k]
        self.logger.info(f"Finished reranking | top_k={top_k}")
        return top_indices.tolist()
