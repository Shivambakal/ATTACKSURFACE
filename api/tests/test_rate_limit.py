import time
from unittest.mock import MagicMock
import pytest
from starlette.requests import Request
from starlette.responses import Response, JSONResponse
from app.middleware.rate_limit import RateLimiter, RateLimitMiddleware

class MockPipeline:
    def __init__(self, current_count: int, oldest_ts: float):
        self.current_count = current_count
        self.oldest_ts = oldest_ts

    def zremrangebyscore(self, key, min_val, max_val):
        return self

    def zcard(self, key):
        return self

    def zrange(self, key, start, stop, withscores=False):
        return self

    def zadd(self, key, mapping):
        return self

    def expire(self, key, seconds):
        return self

    def execute(self):
        # Return results simulating [zrem_count, zcard_count, oldest_entries]
        return [0, self.current_count, [(b"old", self.oldest_ts)] if self.oldest_ts else []]

def create_mock_redis(count: int, oldest_ts: float):
    client = MagicMock()
    client.pipeline = MagicMock(return_value=MockPipeline(count, oldest_ts))
    return client

def test_rate_limiter_under_limit():
    now = time.time()
    mock_redis = create_mock_redis(count=5, oldest_ts=now - 10)
    limiter = RateLimiter(redis_client=mock_redis)

    limited, retry_after, remaining = limiter.check_limit("test:key", limit=10, window_seconds=60)
    assert not limited
    assert retry_after == 0
    assert remaining == 4  # limit(10) - (current(5) + 1)

def test_rate_limiter_over_limit():
    now = time.time()
    mock_redis = create_mock_redis(count=10, oldest_ts=now - 20)
    limiter = RateLimiter(redis_client=mock_redis)

    limited, retry_after, remaining = limiter.check_limit("test:key", limit=10, window_seconds=60)
    assert limited
    assert retry_after > 0
    assert remaining == 0

def test_rate_limiter_fails_open_on_redis_error():
    broken_redis = MagicMock()
    broken_redis.pipeline.side_effect = ConnectionError("Redis down")
    limiter = RateLimiter(redis_client=broken_redis)

    limited, retry_after, remaining = limiter.check_limit("test:key", limit=10, window_seconds=60)
    # Must fail open: never crash or block requests when Redis fails
    assert not limited
    assert remaining == 10

def test_rate_limiter_fails_open_when_no_client():
    limiter = RateLimiter(redis_client=None)
    limiter.get_client = MagicMock(return_value=None)
    limited, retry_after, remaining = limiter.check_limit("test:key", limit=10, window_seconds=60)
    assert not limited

@pytest.mark.asyncio
async def test_middleware_blocks_when_limit_exceeded():
    now = time.time()
    mock_redis = create_mock_redis(count=100, oldest_ts=now - 10)

    app = MagicMock()
    middleware = RateLimitMiddleware(
        app,
        redis_client=mock_redis,
        enabled=True,
        ip_limit=5,
        ip_window=60,
    )

    scope = {
        "type": "http",
        "method": "GET",
        "path": "/targets",
        "headers": [(b"host", b"localhost")],
        "client": ("192.0.2.1", 12345),
    }
    request = Request(scope)

    async def call_next(req):
        return Response("OK")

    response = await middleware.dispatch(request, call_next)
    assert response.status_code == 429
    assert "Retry-After" in response.headers
    assert "X-RateLimit-Limit" in response.headers

@pytest.mark.asyncio
async def test_middleware_allows_excluded_paths():
    mock_redis = create_mock_redis(count=100, oldest_ts=time.time())
    app = MagicMock()
    middleware = RateLimitMiddleware(app, redis_client=mock_redis, enabled=True)

    scope = {
        "type": "http",
        "method": "GET",
        "path": "/health",
        "headers": [(b"host", b"localhost")],
        "client": ("192.0.2.1", 12345),
    }
    request = Request(scope)

    async def call_next(req):
        return Response("health ok", status_code=200)

    response = await middleware.dispatch(request, call_next)
    assert response.status_code == 200

@pytest.mark.asyncio
async def test_middleware_differentiates_authenticated_user():
    now = time.time()
    mock_redis = create_mock_redis(count=2, oldest_ts=now - 5)
    app = MagicMock()
    middleware = RateLimitMiddleware(app, redis_client=mock_redis, enabled=True, user_limit=50)

    scope = {
        "type": "http",
        "method": "GET",
        "path": "/targets",
        "headers": [(b"host", b"localhost"), (b"x-user-id", b"user-789")],
        "client": ("192.0.2.1", 12345),
    }
    request = Request(scope)

    async def call_next(req):
        return Response("OK", status_code=200)

    response = await middleware.dispatch(request, call_next)
    assert response.status_code == 200
    assert response.headers.get("X-RateLimit-Limit") == "50"
