from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from modules.chroma_ext.utils.embedings import MyEmbeddingFunction


@pytest.fixture
def embedder():
    logger = MagicMock()
    return MyEmbeddingFunction(
        logger=logger,
        folder_id="b1g2d3f4",
        iam_token="t0k3n-12345678",
        doc_model_uri="doc-uri",
        query_model_uri="query-uri",
        text_type="doc",
        time_sleep=0,
        max_retries=2,
        request_timeout=5,
        batch_size=2,
        sleep_between_batches=0,
    )


class TestMyEmbeddingFunctionInit:
    def test_defaults_and_kwargs(self, embedder):
        assert embedder.api_url == "https://llm.api.cloud.yandex.net:443/foundationModels/v1/textEmbedding"
        assert embedder.folder_id == "b1g2d3f4"
        assert embedder.iam_token == "t0k3n-12345678"
        assert embedder.text_type == "doc"
        assert embedder.doc_model_uri == "doc-uri"
        assert embedder.query_model_uri == "query-uri"
        assert embedder.max_retries == 2
        assert embedder.batch_size == 2


class TestMyEmbeddingFunctionGetSingleEmbedding:
    @patch("modules.chroma_ext.utils.embedings.time.sleep", return_value=None)
    @patch("modules.chroma_ext.utils.embedings.requests.post")
    def test_success_returns_ndarray(self, mock_post, mock_sleep, embedder):
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.json.return_value = {"embedding": [0.1, 0.2, 0.3]}
        mock_post.return_value = mock_resp

        result = embedder._get_single_embedding("hello")
        assert isinstance(result, np.ndarray)
        np.testing.assert_array_equal(result, np.array([0.1, 0.2, 0.3]))

    @patch("modules.chroma_ext.utils.embedings.time.sleep", return_value=None)
    @patch("modules.chroma_ext.utils.embedings.requests.post")
    def test_transient_retries_then_success(self, mock_post, mock_sleep, embedder):
        bad_resp = MagicMock()
        bad_resp.ok = False
        bad_resp.status_code = 503
        bad_resp.text = "busy"

        good_resp = MagicMock()
        good_resp.ok = True
        good_resp.json.return_value = {"embedding": [1.0]}

        mock_post.side_effect = [bad_resp, good_resp]

        result = embedder._get_single_embedding("hello")
        np.testing.assert_array_equal(result, np.array([1.0]))
        assert mock_post.call_count == 2
        embedder.logger.warning.assert_called()

    @patch("modules.chroma_ext.utils.embedings.time.sleep", return_value=None)
    @patch("modules.chroma_ext.utils.embedings.requests.post")
    def test_non_transient_4xx_raises(self, mock_post, mock_sleep, embedder):
        bad_resp = MagicMock()
        bad_resp.ok = False
        bad_resp.status_code = 400
        bad_resp.text = "bad request"
        bad_resp.raise_for_status.side_effect = Exception("HTTP 400")
        mock_post.return_value = bad_resp

        with pytest.raises(Exception, match="HTTP 400"):
            embedder._get_single_embedding("hello")

    @patch("modules.chroma_ext.utils.embedings.time.sleep", return_value=None)
    @patch("modules.chroma_ext.utils.embedings.requests.post")
    def test_timeout_retries_then_raises(self, mock_post, mock_sleep, embedder):
        from requests.exceptions import ConnectTimeout

        mock_post.side_effect = ConnectTimeout("timeout")

        with pytest.raises(ConnectTimeout):
            embedder._get_single_embedding("hello")
        assert mock_post.call_count == 2


class TestMyEmbeddingFunctionBatched:
    def test_batched_exact_and_remainder(self, embedder):
        result = list(embedder._batched(["a", "b", "c", "d", "e"], 2))
        assert result == [["a", "b"], ["c", "d"], ["e"]]

    def test_batched_empty(self, embedder):
        result = list(embedder._batched([], 3))
        assert result == []


class TestMyEmbeddingFunctionCall:
    @patch("modules.chroma_ext.utils.embedings.time.sleep", return_value=None)
    @patch("modules.chroma_ext.utils.embedings.requests.post")
    def test_call_single_string(self, mock_post, mock_sleep, embedder):
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.json.return_value = {"embedding": [0.5]}
        mock_post.return_value = mock_resp

        result = embedder("hello")
        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], np.ndarray)

    @patch("modules.chroma_ext.utils.embedings.time.sleep", return_value=None)
    @patch("modules.chroma_ext.utils.embedings.requests.post")
    def test_call_batches_with_sleep(self, mock_post, mock_sleep, embedder):
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.json.return_value = {"embedding": [0.1]}
        mock_post.return_value = mock_resp

        embedder.batch_size = 2
        result = embedder(["a", "b", "c"])
        assert isinstance(result, list)
        assert len(result) == 3
        assert all(isinstance(r, np.ndarray) for r in result)
        # sleep вызывается: base sleep для каждого запроса + sleep_between_batches
        assert mock_sleep.call_count >= 1
