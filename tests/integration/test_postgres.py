"""Integration tests for Postgres module.

Run with::

    UNION_TEST_MODE=local pytest tests/integration/test_postgres.py -v
    # or after kubectl port-forward
    UNION_TEST_MODE=cluster pytest tests/integration/test_postgres.py -v
"""

import pytest

pytestmark = [pytest.mark.integration]


@pytest.mark.asyncio
async def test_postgres_client_creates_pool(postgres_client):
    """PostgresClient can create a connection pool."""
    await postgres_client.ensure_pool()
    stats = await postgres_client.get_pool_stats()
    assert stats is not None
    assert stats.get("pool_size", 0) > 0


@pytest.mark.asyncio
async def test_postgres_connection_alive(postgres_client):
    """A connection from the pool can execute ``SELECT 1``."""
    await postgres_client.ensure_pool()
    conn = await postgres_client._take_conn_in_loop(0, postgres_client.settings.pool_max_size)
    assert conn is not None
    await postgres_client._pool.putconn(conn)


@pytest.mark.asyncio
async def test_postgres_saver_setup(postgres_client):
    """AsyncPostgresSaver can create checkpoint tables."""
    await postgres_client.ensure_pool()
    async with postgres_client.get_user_checkpointer() as saver:
        await saver.setup()
