import json
from unittest.mock import ANY, MagicMock, patch

import pytest

from modules.redis_ext.base import RedisAdapter


@pytest.fixture
def mock_embeddings():
    return MagicMock()


@pytest.fixture
def mock_logger():
    return MagicMock()


@pytest.fixture
def adapter(mock_logger, mock_embeddings):
    with patch("modules.redis_ext.base.RedisSemanticCache") as MockCache:
        mock_cache = MagicMock()
        MockCache.return_value = mock_cache
        inst = RedisAdapter(
            logger=mock_logger,
            embeddings=mock_embeddings,
            redis_url="redis://test:6379",
            redis_threshold=0.1,
            redis_ttl=60,
        )
        inst._mock_cache = mock_cache
        return inst


class TestRedisAdapterInit:
    def test_uses_explicit_args(self, mock_logger, mock_embeddings):
        with patch("modules.redis_ext.base.RedisSemanticCache") as MockCache:
            RedisAdapter(
                logger=mock_logger,
                embeddings=mock_embeddings,
                redis_url="redis://explicit:6379",
                redis_threshold=0.2,
                redis_ttl=120,
            )
            MockCache.assert_called_once_with(
                redis_url="redis://explicit:6379",
                embeddings=mock_embeddings,
                distance_threshold=0.2,
                ttl=120,
            )

    def test_fallback_to_env_vars(self, monkeypatch, mock_logger, mock_embeddings):
        monkeypatch.setenv("REDIS_URL", "redis://env:6379")
        monkeypatch.setenv("REDIS_THRESHOLD", "0.3")
        monkeypatch.setenv("REDIS_TTL", "240")
        with patch("modules.redis_ext.base.RedisSemanticCache") as MockCache:
            RedisAdapter(
                logger=mock_logger,
                embeddings=mock_embeddings,
                redis_url=None,
                redis_threshold=None,
                redis_ttl=None,
            )
            MockCache.assert_called_once_with(
                redis_url="redis://env:6379",
                embeddings=mock_embeddings,
                distance_threshold=0.3,
                ttl=240,
            )


class TestRedisAdapterSave:
    def test_save_calls_update_and_ends_span(self, adapter):
        span = MagicMock()
        adapter._start_span = MagicMock(return_value=span)
        adapter.save(meta_info="meta", query="q", output="out", json_data={"k": "v"})

        adapter._mock_cache.update.assert_called_once()
        args = adapter._mock_cache.update.call_args[0]
        assert args[0] == "q"
        assert args[1] == "meta"
        generation = args[2][0]
        assert json.loads(generation.text)["output"] == "out"
        span.end.assert_called_once_with(output={"status": "saved"})

    def test_save_error_ends_span_with_error(self, adapter):
        span = MagicMock()
        adapter._start_span = MagicMock(return_value=span)
        adapter._mock_cache.update.side_effect = RuntimeError("boom")

        with pytest.raises(RuntimeError, match="boom"):
            adapter.save(meta_info="meta", query="q")

        span.end.assert_called_once_with(level="ERROR", status_message="boom")


class TestRedisAdapterGet:
    def test_get_hit_parses_json(self, adapter):
        span = MagicMock()
        adapter._start_span = MagicMock(return_value=span)
        payload = {"output": "hello", "json": {"x": 1}}
        gen = MagicMock()
        gen.text = json.dumps(payload)
        adapter._mock_cache.lookup.return_value = [gen]

        result = adapter.get(meta_info="meta", query="q")
        assert result == payload
        span.end.assert_called_once_with(output={"hit": True})

    def test_get_miss_returns_none(self, adapter):
        span = MagicMock()
        adapter._start_span = MagicMock(return_value=span)
        adapter._mock_cache.lookup.return_value = None

        result = adapter.get(meta_info="meta", query="q")
        assert result is None
        span.end.assert_called_once_with(output={"hit": False})

    def test_get_json_decode_error_logs_and_returns_none(self, adapter):
        span = MagicMock()
        adapter._start_span = MagicMock(return_value=span)
        gen = MagicMock()
        gen.text = "not-json"
        adapter._mock_cache.lookup.return_value = [gen]

        result = adapter.get(meta_info="meta", query="q")
        assert result is None
        adapter.logger.error.assert_called()
        span.end.assert_called_once_with(level="ERROR", status_message=ANY)

    def test_get_exception_propagates(self, adapter):
        span = MagicMock()
        adapter._start_span = MagicMock(return_value=span)
        adapter._mock_cache.lookup.side_effect = ValueError("redis down")

        with pytest.raises(ValueError, match="redis down"):
            adapter.get(meta_info="meta", query="q")

        span.end.assert_called_once_with(level="ERROR", status_message="redis down")


class TestRedisAdapterHealthCheck:
    def test_true_when_cache_present(self, adapter):
        assert adapter.health_check() is True

    def test_false_when_cache_missing(self, adapter):
        adapter.semantic_cache = None
        assert adapter.health_check() is False


class TestRedisAdapterStartSpan:
    def test_prefers_current_span(self, adapter):
        child_span = MagicMock()
        parent_span = MagicMock()
        parent_span.span.return_value = child_span

        with patch("modules.redis_ext.base.current_span") as mock_cs, \
             patch("modules.redis_ext.base.current_trace") as mock_ct:
            mock_cs.get.return_value = parent_span
            mock_ct.get.return_value = MagicMock()

            result = adapter._start_span("redis_test", {"a": 1})
            assert result is child_span
            parent_span.span.assert_called_once_with(name="redis_test", input={"a": 1})

    def test_fallback_to_trace(self, adapter):
        trace = MagicMock()
        child = MagicMock()
        trace.span.return_value = child

        with patch("modules.redis_ext.base.current_span") as mock_cs, \
             patch("modules.redis_ext.base.current_trace") as mock_ct:
            mock_cs.get.return_value = None
            mock_ct.get.return_value = trace

            result = adapter._start_span("redis_test", {"a": 1})
            assert result is child
            trace.span.assert_called_once_with(name="redis_test", input={"a": 1})

    def test_none_when_no_context(self, adapter):
        with patch("modules.redis_ext.base.current_span") as mock_cs, \
             patch("modules.redis_ext.base.current_trace") as mock_ct:
            mock_cs.get.return_value = None
            mock_ct.get.return_value = None

            assert adapter._start_span("redis_test", {"a": 1}) is None
