import asyncio

import pytest
from fakeredis.aioredis import FakeRedis

from modules.redis_ext.job_store import ChatJobStore


@pytest.fixture
def fake_store():
    redis = FakeRedis(decode_responses=True)
    return ChatJobStore(host="localhost", port=6379, password=None, db=3, ttl=900, redis=redis)


@pytest.mark.anyio
async def test_create_and_get(fake_store):
    created = await fake_store.create("job-1", user_id="u1", organisation="org1")
    assert created is True

    job = await fake_store.get("job-1")
    assert job is not None
    assert job["status"] == "processing"
    assert job["user_id"] == "u1"
    assert job["organisation"] == "org1"


@pytest.mark.anyio
async def test_create_idempotent(fake_store):
    created1 = await fake_store.create("job-1", user_id="u1", organisation="org1")
    created2 = await fake_store.create("job-1", user_id="u2", organisation="org2")
    assert created1 is True
    assert created2 is False

    job = await fake_store.get("job-1")
    assert job["user_id"] == "u1"


@pytest.mark.anyio
async def test_set_done(fake_store):
    await fake_store.create("job-1", user_id="u1", organisation="org1")
    await fake_store.set_done("job-1", "answer text")

    job = await fake_store.get("job-1")
    assert job["status"] == "done"
    assert job["response"] == "answer text"


@pytest.mark.anyio
async def test_set_error(fake_store):
    await fake_store.create("job-1", user_id="u1", organisation="org1")
    await fake_store.set_error("job-1", "TIMEOUT", "too slow")

    job = await fake_store.get("job-1")
    assert job["status"] == "error"
    assert job["code"] == "TIMEOUT"
    assert job["error"] == "too slow"


@pytest.mark.anyio
async def test_get_missing(fake_store):
    assert await fake_store.get("missing") is None


@pytest.mark.anyio
async def test_ttl_extends_on_update(fake_store):
    await fake_store.create("job-1", user_id="u1", organisation="org1")
    ttl1 = await fake_store.redis.ttl(fake_store._key("job-1"))
    await asyncio.sleep(0.1)
    await fake_store.set_done("job-1", "answer")
    ttl2 = await fake_store.redis.ttl(fake_store._key("job-1"))
    assert ttl2 > ttl1 - 1  # TTL обновился
