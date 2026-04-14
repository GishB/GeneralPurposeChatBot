from unittest.mock import MagicMock

import pytest

from modules.chroma_ext.utils.reranker import BM25Reranker


@pytest.fixture
def reranker():
    logger = MagicMock()
    return BM25Reranker(logger=logger, tokenizer_name="gpt-3.5-turbo")


class TestBM25RerankerInit:
    def test_initializes_tokenizer(self, reranker):
        assert reranker.tokenizer is not None
        reranker.logger.info.assert_called()


class TestBM25RerankerPreprocess:
    def test_preprocess_lowercases_and_tokenizes(self, reranker):
        tokens = reranker.preprocess("Hello World")
        assert isinstance(tokens, list)
        assert len(tokens) > 0
        # tiktoken tokens converted back to strings; "hello" and " world" or similar
        text = " ".join(tokens)
        assert "hello" in text.lower()

    def test_preprocess_filters_empty(self, reranker):
        tokens = reranker.preprocess("")
        assert tokens == []


class TestBM25RerankerFit:
    def test_fit_builds_bm25(self, reranker):
        reranker.fit(["first document", "second document"])
        assert reranker.bm25 is not None


class TestBM25RerankerRerank:
    def test_rerank_before_fit_raises(self, reranker):
        with pytest.raises(ValueError, match="not fitted"):
            reranker.rerank("query", top_k=2)

    def test_rerank_returns_top_k_indices(self, reranker):
        docs = [
            "python programming language",
            "cooking recipes for dinner",
            "python snakes in the wild",
        ]
        reranker.fit(docs)
        indices = reranker.rerank("python code", top_k=2)
        assert len(indices) == 2
        assert all(isinstance(i, int) for i in indices)

    def test_rerank_top_k_larger_than_docs(self, reranker):
        docs = ["only one document here"]
        reranker.fit(docs)
        indices = reranker.rerank("query", top_k=5)
        assert len(indices) == 1
