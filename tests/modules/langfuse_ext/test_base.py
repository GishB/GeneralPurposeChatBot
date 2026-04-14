from unittest.mock import MagicMock, patch

import pytest

from modules.langfuse_ext.base import LangfuseClient


@pytest.fixture
def client():
    config = MagicMock()
    config.host = "https://langfuse.test"
    config.secret_key = "secret_key_123"
    config.public_key = "public_key_456"
    config.stage = "test"
    logger = MagicMock()
    return LangfuseClient(app_config=config, logger=logger)


class TestLangfuseClientInit:
    def test_logs_masked_keys(self, client):
        client.logger.debug.assert_any_call("Secret Key: secr**_123")
        client.logger.debug.assert_any_call("Public Key: publ**_456")
        assert client.client is not None
        assert client.handler is not None


class TestLangfuseClientCreateClient:
    @patch("modules.langfuse_ext.base.Langfuse")
    def test_creates_langfuse_instance(self, MockLangfuse):
        config = MagicMock()
        config.host = "h"
        config.secret_key = "s"
        config.public_key = "p"
        logger = MagicMock()
        client = LangfuseClient(app_config=config, logger=logger)
        # access property to trigger creation
        _ = client._LangfuseClient__create_client
        MockLangfuse.assert_called_with(secret_key="s", public_key="p", host="h")


class TestLangfuseClientCreateCallbackHandler:
    @patch("modules.langfuse_ext.base.CallbackHandler")
    def test_creates_handler(self, MockHandler):
        config = MagicMock()
        config.host = "h"
        config.secret_key = "s"
        config.public_key = "p"
        config.stage = "stage"
        logger = MagicMock()
        client = LangfuseClient(app_config=config, logger=logger)
        _ = client._LangfuseClient__create_callback_handler
        MockHandler.assert_called_with(
            public_key="p", secret_key="s", host="h", trace_name="stage"
        )


class TestLangfuseClientHealthCheck:
    def test_true_when_auth_ok(self, client):
        client.client = MagicMock()
        client.client.auth_check.return_value = True
        assert client.health_check() is True

    def test_false_when_auth_fails(self, client):
        client.client = MagicMock()
        client.client.auth_check.return_value = False
        assert client.health_check() is False


class TestLangfuseClientOnStartup:
    @pytest.mark.asyncio
    async def test_reassigns_and_checks(self, client):
        client.client = MagicMock()
        client.handler = MagicMock()
        with patch.object(client, "health_check", return_value=True) as mock_hc:
            await client.on_startup()
            mock_hc.assert_called_once()

    @pytest.mark.asyncio
    async def test_catches_exceptions(self, client):
        with patch.object(
            type(client), "_LangfuseClient__create_client", property(lambda self: (_ for _ in ()).throw(RuntimeError("boom")))
        ):
            # Should not raise
            await client.on_startup()
