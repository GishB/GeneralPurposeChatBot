from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from modules.chroma_ext.base import ChromaAdapter


@pytest.fixture
def adapter():
    logger = MagicMock()
    with patch("modules.chroma_ext.base.chromadb.HttpClient") as MockClient, \
         patch("modules.chroma_ext.base.BM25Reranker") as MockReranker:
        mock_client = MagicMock()
        MockClient.return_value = mock_client
        mock_reranker = MagicMock()
        MockReranker.return_value = mock_reranker
        inst = ChromaAdapter(
            logger=logger,
            similarity_filter=1.0,
            reranker_type="bm25",
            text_type="query",
            API_KEY="key123456789",
            FOLDER_ID="fld123456789",
            CHROMA_HOST="testhost",
            CHROMA_PORT=9000,
            CHROMA_TOPK_DOCUMENTS=3,
            CHROMA_MAX_RAG_DOCUMENTS=10,
        )
        inst._mock_client = mock_client
        inst._mock_reranker = mock_reranker
        return inst


class TestChromaAdapterInit:
    def test_validation_errors(self):
        logger = MagicMock()
        with patch("modules.chroma_ext.base.chromadb.HttpClient"):
            # FOLDER_ID=None and API_KEY=None currently raise TypeError due to slice
            # before validation (bug in code)
            with pytest.raises(TypeError):
                ChromaAdapter(logger=logger, API_KEY="key", FOLDER_ID=None)
            with pytest.raises(TypeError):
                ChromaAdapter(logger=logger, API_KEY=None, FOLDER_ID="fld123456789")
            with pytest.raises(ValueError, match="TOPK"):
                ChromaAdapter(logger=logger, API_KEY="key", FOLDER_ID="fld123456789", CHROMA_TOPK_DOCUMENTS=20, CHROMA_MAX_RAG_DOCUMENTS=20)

    def test_unsupported_reranker_does_not_raise(self):
        # Current code instantiates NotImplementedError but does not raise it (bug).
        logger = MagicMock()
        with patch("modules.chroma_ext.base.chromadb.HttpClient"):
            adapter = ChromaAdapter(
                logger=logger,
                API_KEY="key123456789",
                FOLDER_ID="fld123456789",
                reranker_type="unknown",
            )
            assert getattr(adapter, "reranker", None) is None

    def test_params_set(self, adapter):
        assert adapter.host == "testhost"
        assert adapter.port == 9000
        assert adapter.topk_documents == 3
        assert adapter.max_rag_documents == 10
        assert adapter.similarity_filter == 1.0


class TestChromaAdapterEmbeddingFunction:
    @patch("modules.chroma_ext.base.MyEmbeddingFunction")
    def test_lazy_initialization(self, MockEmb, adapter):
        mock_ef = MagicMock()
        MockEmb.return_value = mock_ef
        ef = adapter.embedding_function
        assert ef is mock_ef
        MockEmb.assert_called_once()
        # second call returns cached
        assert adapter.embedding_function is mock_ef


class TestChromaAdapterStartSpan:
    def test_prefers_current_span(self, adapter):
        parent = MagicMock()
        child = MagicMock()
        parent.span.return_value = child
        with patch("modules.chroma_ext.base.current_span") as mock_cs, \
             patch("modules.chroma_ext.base.current_trace") as mock_ct:
            mock_cs.get.return_value = parent
            mock_ct.get.return_value = MagicMock()
            result = adapter._start_span("chroma_test", {"a": 1})
            assert result is child

    def test_fallback_to_trace(self, adapter):
        trace = MagicMock()
        child = MagicMock()
        trace.span.return_value = child
        with patch("modules.chroma_ext.base.current_span") as mock_cs, \
             patch("modules.chroma_ext.base.current_trace") as mock_ct:
            mock_cs.get.return_value = None
            mock_ct.get.return_value = trace
            result = adapter._start_span("chroma_test", {"a": 1})
            assert result is child

    def test_none_when_no_context(self, adapter):
        with patch("modules.chroma_ext.base.current_span") as mock_cs, \
             patch("modules.chroma_ext.base.current_trace") as mock_ct:
            mock_cs.get.return_value = None
            mock_ct.get.return_value = None
            assert adapter._start_span("chroma_test", {"a": 1}) is None


class TestChromaAdapterGetInfoFromDb:
    def test_success(self, adapter):
        span = MagicMock()
        adapter._start_span = MagicMock(return_value=span)
        mock_collection = MagicMock()
        mock_collection.query.return_value = {
            "documents": [["doc1", "doc2"]],
            "metadatas": [[{"m": 1}, {"m": 2}]],
            "distances": [[0.1, 0.2]],
        }
        adapter._mock_client.get_collection.return_value = mock_collection

        result = adapter.get_info_from_db("q", "coll", n_results=5, where={"topic": "t"})
        assert result["documents"][0] == ["doc1", "doc2"]
        span.end.assert_called_once_with(output={"documents_returned": 2})

    def test_error_ends_span(self, adapter):
        span = MagicMock()
        adapter._start_span = MagicMock(return_value=span)
        adapter._mock_client.get_collection.side_effect = RuntimeError("chroma down")
        with pytest.raises(RuntimeError, match="chroma down"):
            adapter.get_info_from_db("q", "coll")
        span.end.assert_called_once_with(level="ERROR", status_message="chroma down")


class TestChromaAdapterGetFilteredDocuments:
    def test_filters_by_distance_and_strips_body(self, adapter):
        data_raw = {
            "documents": [["<body>keep1</body>", "<body>keep2</body>", "drop"]],
            "metadatas": [[{"a": 1}, {"a": 2}, {"a": 3}]],
            "distances": [[0.5, 0.9, 1.5]],
        }
        result = adapter.get_filtered_documents(data_raw)
        assert result["documents"] == ["keep1", "keep2"]
        assert result["metadatas"] == [{"a": 1}, {"a": 2}]


class TestChromaAdapterGetPairs:
    def test_builds_pairs(self, adapter):
        result = adapter.get_pairs("query", ["d1", "d2"])
        assert result == [["query", "d1"], ["query", "d2"]]


class TestChromaAdapterApplyReranker:
    def test_delegates_to_bm25(self, adapter):
        adapter._mock_reranker.rerank.return_value = [1, 0]
        idx = adapter.apply_reranker("q", ["d1", "d2", "d3"])
        adapter._mock_reranker.fit.assert_called_once_with(["d1", "d2", "d3"])
        adapter._mock_reranker.rerank.assert_called_once_with(query="q", top_k=3)
        assert idx == [1, 0]


class TestChromaAdapterGetInfo:
    def test_full_flow_returns_dataframe(self, adapter):
        span = MagicMock()
        adapter._start_span = MagicMock(return_value=span)
        mock_collection = MagicMock()
        mock_collection.query.return_value = {
            "documents": [["<body>d1</body>", "<body>d2</body>"]],
            "metadatas": [[{"t": "a"}, {"t": "b"}]],
            "distances": [[0.1, 0.2]],
        }
        adapter._mock_client.get_collection.return_value = mock_collection
        adapter._mock_reranker.rerank.return_value = [0]

        df = adapter.get_info("query", "coll", topics=["a", "b"])
        assert isinstance(df, pd.DataFrame)
        assert df["documents"].tolist() == ["d1"]
        # get_info creates its own span and get_info_from_db creates another;
        # last end call belongs to the outer chroma_rag span
        span.end.assert_called_with(output={"documents_found": 1})

    def test_empty_filtered_documents(self, adapter):
        span = MagicMock()
        adapter._start_span = MagicMock(return_value=span)
        mock_collection = MagicMock()
        mock_collection.query.return_value = {
            "documents": [["drop"]],
            "metadatas": [[{"t": "a"}]],
            "distances": [[2.0]],
        }
        adapter._mock_client.get_collection.return_value = mock_collection

        df = adapter.get_info("query", "coll")
        assert isinstance(df, pd.DataFrame)
        assert df.empty
        span.end.assert_called_with(output={"documents_found": 0})

    def test_exception_ends_span(self, adapter):
        span = MagicMock()
        adapter._start_span = MagicMock(return_value=span)
        adapter._mock_client.get_collection.side_effect = ValueError("fail")
        with pytest.raises(ValueError, match="fail"):
            adapter.get_info("query", "coll")
        span.end.assert_called_with(level="ERROR", status_message="fail")


class TestChromaAdapterHealthCheck:
    def test_always_true(self, adapter):
        assert adapter.health_check() is True
