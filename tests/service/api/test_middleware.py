"""Tests for request/response body decoding in log_requests middleware."""

from unittest.mock import MagicMock

from service.api.middleware import _get_decoded_body


def test_empty_body_returns_empty_dict_without_warning():
    """Empty body (e.g. GET requests) is not a warning-worthy event."""
    logger = MagicMock()

    result = _get_decoded_body(b"", "request", logger)

    assert result == {}
    logger.warning.assert_not_called()


def test_invalid_json_returns_empty_dict_with_warning():
    """Non-empty malformed body still produces a warning."""
    logger = MagicMock()

    result = _get_decoded_body(b"not-a-json", "response", logger)

    assert result == {}
    logger.warning.assert_called_once_with("response body is not json")


def test_valid_json_returns_parsed_body():
    """Valid JSON body is decoded into a dict."""
    logger = MagicMock()

    result = _get_decoded_body(b'{"question": "hi"}', "request", logger)

    assert result == {"question": "hi"}
    logger.warning.assert_not_called()
