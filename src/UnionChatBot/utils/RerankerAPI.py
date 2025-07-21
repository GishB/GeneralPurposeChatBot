from typing import List
import numpy as np
from rank_bm25 import BM25Okapi
import tiktoken


class BM25Reranker:
    def __init__(self, tokenizer_name: str = "gpt-3.5-turbo"):
        self.tokenizer = tiktoken.encoding_for_model(tokenizer_name)
        self.bm25 = None

    def preprocess(self, text: str) -> List[str]:
        """Токенизация текста и возвращение строковых токенов."""
        tokens = self.tokenizer.encode(text.lower())
        # Преобразуем токены обратно в строки для совместимости с BM25
        token_strings = []
        for token in tokens:
            token_str = self.tokenizer.decode([token])
            token_str = token_str.strip()
            if token_str and len(token_str) > 0:
                token_strings.append(token_str)
        return token_strings

    def fit(self, documents: List[str]):
        """Обучение модели на корпусе документов для текущего запроса."""
        tokenized_docs = [self.preprocess(doc) for doc in documents]
        self.bm25 = BM25Okapi(tokenized_docs)

    def rerank(self, query: str, top_k: int = 3) -> List[int]:
        """Возвращает индексы наиболее релевантных документов из представленных."""
        if self.bm25 is None:
            raise ValueError("BM25 model not fitted. Call fit() first.")

        # Токенизируем запрос
        tokenized_query = self.preprocess(query)

        # Получаем оценки для всех документов
        scores = self.bm25.get_scores(tokenized_query)

        # Находим индексы с наибольшими оценками
        top_indices = np.argsort(scores)[::-1][:top_k]

        return top_indices.tolist()
