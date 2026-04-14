import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from modules.postgres_ext.base import PostgresClient


@pytest.fixture
def client():
    config = MagicMock()
    config.encoded_pass = "secret"
    config.user = "u"
    config.host = "h"
    config.port = 5432
    config.postgres_db = "db"
    config.pool_min_size = 1
    config.pool_max_size = 5
    config.pool_max_idle = 30.0
    config.conninfo = "postgresql://u:secret@h:5432/db"
    logger = MagicMock()
    return PostgresClient(config=config, logger=logger)


class TestPostgresClientInit:
    def test_pool_starts_none(self, client):
        assert client._pool is None
        assert isinstance(client._lock, asyncio.Lock)
        client.logger.info.assert_called()


@pytest.mark.asyncio
class TestPostgresClientEnsurePool:
    async def test_creates_pool_once(self, client):
        with patch("modules.postgres_ext.base.AsyncConnectionPool") as MockPool:
            mock_pool = AsyncMock()
            mock_pool.get_stats = MagicMock(return_value={"pool_size": 1})
            MockPool.return_value = mock_pool

            await client.ensure_pool()
            await client.ensure_pool()

            MockPool.assert_called_once_with(
                conninfo=client.settings.conninfo,
                min_size=client.settings.pool_min_size,
                max_size=client.settings.pool_max_size,
                max_idle=client.settings.pool_max_idle,
            )
            assert mock_pool.open.await_count == 1

    async def test_race_condition_safe(self, client):
        with patch("modules.postgres_ext.base.AsyncConnectionPool") as MockPool:
            mock_pool = AsyncMock()
            mock_pool.get_stats = MagicMock(return_value={"pool_size": 1})
            MockPool.return_value = mock_pool

            async def task():
                await client.ensure_pool()

            await asyncio.gather(task(), task(), task())
            MockPool.assert_called_once()


@pytest.mark.asyncio
class TestPostgresClientTakeConnInLoop:
    async def test_happy_path(self, client):
        with patch("modules.postgres_ext.base.AsyncConnectionPool") as MockPool:
            mock_pool = AsyncMock()
            mock_pool.get_stats = MagicMock(return_value={"pool_size": 1})
            mock_conn = AsyncMock()
            mock_pool.getconn.return_value = mock_conn
            MockPool.return_value = mock_pool
            await client.ensure_pool()

            conn = await client._take_conn_in_loop(0, 3)
            assert conn is mock_conn
            mock_conn.execute.assert_any_call("SELECT 1")
            mock_conn.execute.assert_any_call("ROLLBACK")

    async def test_retries_then_none(self, client):
        with patch("modules.postgres_ext.base.AsyncConnectionPool") as MockPool:
            mock_pool = AsyncMock()
            mock_pool.get_stats = MagicMock(return_value={"pool_size": 1})
            mock_conn = AsyncMock()
            mock_conn.execute.side_effect = RuntimeError("dead")
            mock_pool.getconn.return_value = mock_conn
            MockPool.return_value = mock_pool
            await client.ensure_pool()

            conn = await client._take_conn_in_loop(0, 2)
            assert conn is None
            assert mock_conn.close.await_count == 2


@pytest.mark.asyncio
class TestPostgresClientGetUserCheckpointer:
    async def test_yields_saver_and_returns_conn(self, client):
        with patch("modules.postgres_ext.base.AsyncConnectionPool") as MockPool, \
             patch("modules.postgres_ext.base.AsyncPostgresSaver") as MockSaver:
            mock_pool = AsyncMock()
            mock_pool.get_stats = MagicMock(return_value={"pool_size": 1})
            mock_conn = AsyncMock()
            mock_pool.getconn.return_value = mock_conn
            MockPool.return_value = mock_pool
            mock_saver = MagicMock()
            MockSaver.return_value = mock_saver

            await client.ensure_pool()
            async with client.get_user_checkpointer() as saver:
                assert saver is mock_saver

            mock_conn.set_autocommit.assert_awaited_once_with(True)
            mock_pool.putconn.assert_awaited_once_with(mock_conn)


@pytest.mark.asyncio
class TestPostgresClientGetPoolStats:
    async def test_none_when_no_pool(self, client):
        assert await client.get_pool_stats() is None

    async def test_returns_stats(self, client):
        with patch("modules.postgres_ext.base.AsyncConnectionPool") as MockPool:
            mock_pool = AsyncMock()
            mock_pool.get_stats = MagicMock(return_value={"pool_size": 2})
            MockPool.return_value = mock_pool
            await client.ensure_pool()
            stats = await client.get_pool_stats()
            assert stats == {"pool_size": 2}


@pytest.mark.asyncio
class TestPostgresClientClose:
    async def test_closes_and_nulls_pool(self, client):
        with patch("modules.postgres_ext.base.AsyncConnectionPool") as MockPool:
            mock_pool = AsyncMock()
            mock_pool.get_stats = MagicMock(return_value={"pool_size": 1})
            MockPool.return_value = mock_pool
            await client.ensure_pool()
            await client.close()
            mock_pool.close.assert_awaited_once()
            assert client._pool is None

    async def test_idempotent(self, client):
        await client.close()
        assert client._pool is None


class TestPostgresClientHealthCheck:
    def test_false_before_init(self, client):
        assert client.health_check() is False

    def test_true_after_init(self, client):
        # We can't easily async ensure_pool in sync test, so set pool manually
        client._pool = MagicMock()
        assert client.health_check() is True
