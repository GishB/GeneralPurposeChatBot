"""Integration tests for Redis module.

Run with::

    UNION_TEST_MODE=local pytest tests/integration/test_redis.py -v
    # or after kubectl port-forward
    UNION_TEST_MODE=cluster pytest tests/integration/test_redis.py -v
"""

import time
import uuid

import pytest

pytestmark = [pytest.mark.integration]


@pytest.fixture(autouse=True)
def _clean_rate_limiter(redis_rate_limiter):
    """Reset counter for the test user before each test."""
    user_id = "integration-test-user"
    redis_rate_limiter.reset_counter(user_id)
    yield
    redis_rate_limiter.reset_counter(user_id)


def test_redis_rate_limiter_allows_under_limit(redis_rate_limiter):
    """Requests are allowed while under the configured limit."""
    user_id = "integration-test-user"
    allowed, current = redis_rate_limiter.check_and_increment(user_id)
    assert allowed is True
    assert current == 1


def test_redis_rate_limiter_blocks_over_limit(logger, redis_settings):
    """Requests are blocked once the limit is exceeded."""
    from modules.redis_ext.utils import UserRateLimiter

    limit = 5
    limiter = UserRateLimiter(
        logger=logger,
        host=redis_settings.host,
        port=redis_settings.port,
        password=redis_settings.password,
        RATE_LIMIT_TEMPLATE="msg_count:{user_id}",
        USER_QUERY_LIMIT_TTL_SECONDS=60,
        USER_QUERY_LIMIT_N=limit,
    )
    user_id = "integration-test-user-over-limit"
    limiter.reset_counter(user_id)

    for _ in range(limit):
        allowed, _ = limiter.check_and_increment(user_id)
        assert allowed is True

    allowed, current = limiter.check_and_increment(user_id)
    assert allowed is False
    assert current == limit + 1


def test_redis_rate_limiter_remaining(redis_rate_limiter):
    """Remaining counter decreases with each request."""
    user_id = "integration-test-user"
    assert redis_rate_limiter.get_remaining(user_id) == redis_rate_limiter.USER_QUERY_LIMIT_N

    redis_rate_limiter.check_and_increment(user_id)
    assert redis_rate_limiter.get_remaining(user_id) == redis_rate_limiter.USER_QUERY_LIMIT_N - 1


def test_redis_rate_limiter_health_check(redis_rate_limiter):
    """Redis responds to PING."""
    assert redis_rate_limiter.health_check() is True


def test_redis_adapter_save_and_get(redis_adapter):
    """RedisAdapter can persist and retrieve JSON metadata."""
    query = f"integration test query {uuid.uuid4()}"
    meta = "test-meta"
    payload = {"output": "test answer", "json": {"key": "value"}}

    redis_adapter.save(meta_info=meta, query=query, output=payload["output"], json_data=payload["json"])
    # RedisSearch vector index is asynchronous; poll until the entry is searchable.
    result = None
    for _ in range(20):
        time.sleep(0.5)
        result = redis_adapter.get(meta_info=meta, query=query)
        if result is not None:
            break

    assert result is not None
    assert result["output"] == payload["output"]
    assert result["json"] == payload["json"]


def test_redis_adapter_get_missing(redis_adapter):
    """RedisAdapter returns None for unknown queries."""
    result = redis_adapter.get(meta_info="missing", query=f"unknown-{uuid.uuid4()}")
    assert result is None


def test_redis_adapter_health_check(redis_adapter):
    """RedisAdapter reports healthy when cache is present."""
    assert redis_adapter.health_check() is True
