from unittest.mock import MagicMock, patch

import pytest

from modules.redis_ext.utils.RedisAdapters import UserRateLimiter


@pytest.fixture
def limiter():
    mock_logger = MagicMock()
    with patch("modules.redis_ext.utils.RedisAdapters.redis.Redis") as MockRedis:
        mock_redis = MagicMock()
        MockRedis.return_value = mock_redis
        inst = UserRateLimiter(
            logger=mock_logger,
            host="test-host",
            port=6380,
            db=3,
            decode_responses=True,
            USER_QUERY_LIMIT_N=5,
            USER_QUERY_LIMIT_TTL_SECONDS=60,
            RATE_LIMIT_TEMPLATE="rl:{user_id}",
        )
        inst._mock_redis = mock_redis
        return inst


class TestUserRateLimiterInit:
    def test_uses_defaults(self):
        mock_logger = MagicMock()
        with patch("modules.redis_ext.utils.RedisAdapters.redis.Redis") as MockRedis:
            UserRateLimiter(logger=mock_logger)
            MockRedis.assert_called_once_with(
                host="127.0.0.1",
                port=6379,
                db=2,
                decode_responses=True,
            )

    def test_uses_kwargs(self):
        mock_logger = MagicMock()
        with patch("modules.redis_ext.utils.RedisAdapters.redis.Redis") as MockRedis:
            UserRateLimiter(
                logger=mock_logger,
                host="h",
                port=1234,
                db=7,
                decode_responses=False,
            )
            MockRedis.assert_called_once_with(
                host="h",
                port=1234,
                db=7,
                decode_responses=False,
            )


class TestUserRateLimiterCheckAndIncrement:
    def test_new_key_sets_expire(self, limiter):
        pipe = MagicMock()
        pipe.incr.return_value = None
        pipe.ttl.return_value = None
        pipe.execute.return_value = [1, -2]
        limiter._mock_redis.pipeline.return_value.__enter__.return_value = pipe

        allowed, count = limiter.check_and_increment("u1")
        assert allowed is True
        assert count == 1
        limiter._mock_redis.expire.assert_called_once_with("rl:u1", 60)

    def test_within_limit_no_expire(self, limiter):
        pipe = MagicMock()
        pipe.execute.return_value = [3, 55]
        limiter._mock_redis.pipeline.return_value.__enter__.return_value = pipe

        allowed, count = limiter.check_and_increment("u1")
        assert allowed is True
        assert count == 3
        limiter._mock_redis.expire.assert_not_called()

    def test_exceeds_limit(self, limiter):
        pipe = MagicMock()
        pipe.execute.return_value = [6, 10]
        limiter._mock_redis.pipeline.return_value.__enter__.return_value = pipe

        allowed, count = limiter.check_and_increment("u1")
        assert allowed is False
        assert count == 6


class TestUserRateLimiterGetRemaining:
    def test_key_exists(self, limiter):
        limiter._mock_redis.get.return_value = "3"
        assert limiter.get_remaining("u1") == 2

    def test_key_missing(self, limiter):
        limiter._mock_redis.get.return_value = None
        assert limiter.get_remaining("u1") == 5


class TestUserRateLimiterResetCounter:
    def test_deletes_key(self, limiter):
        limiter.reset_counter("u1")
        limiter._mock_redis.delete.assert_called_once_with("rl:u1")


class TestUserRateLimiterTtl:
    def test_delegates_to_redis(self, limiter):
        limiter._mock_redis.ttl.return_value = 42
        assert limiter.ttl("u1") == 42
        limiter._mock_redis.ttl.assert_called_once_with("rl:u1")


class TestUserRateLimiterHealthCheck:
    def test_healthy(self, limiter):
        limiter._mock_redis.ping.return_value = True
        assert limiter.health_check() is True

    def test_unhealthy(self, limiter):
        limiter._mock_redis.ping.return_value = False
        assert limiter.health_check() is False
        limiter.logger.warning.assert_called_once()
