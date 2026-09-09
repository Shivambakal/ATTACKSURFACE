"""Redis-backed rate limiting middleware.

Supports per-IP, per-user, and per-target rate limiting with
sliding window counters.
"""
from __future__ import annotations

import hashlib
import logging
import re
import time
from typing import Callable

from redis import Redis
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from ..config import settings

logger = logging.getLogger(__name__)

# Excluded endpoints that should not be rate-limited
EXCLUDED_PATHS = {"/health", "/docs", "/redoc", "/openapi.json"}

# Regex to match target snapshot collection requests: POST /targets/{target_id}/snapshots
TARGET_SNAPSHOT_PATH_REGEX = re.compile(r"^/targets/([^/]+)/snapshots(?:/.*)?$")


class RateLimiter:
    """Sliding-window rate limiter using Redis sorted sets (ZSET)."""

    def __init__(self, redis_client: Redis | None = None) -> None:
        self._client = redis_client
        self._last_connect_failure: float = 0.0
        self._retry_interval: float = 30.0

    def get_client(self) -> Redis | None:
        if self._client is not None:
            return self._client
        now = time.time()
        if now - self._last_connect_failure < self._retry_interval:
            return None
        try:
            self._client = Redis.from_url(
                settings.redis_url,
                decode_responses=True,
                socket_timeout=0.5,
                socket_connect_timeout=0.5,
            )
            return self._client
        except Exception as exc:
            self._last_connect_failure = now
            logger.warning("Failed to connect to Redis for rate limiting: %s", exc)
            return None


    def check_limit(
        self,
        key: str,
        limit: int,
        window_seconds: int,
    ) -> tuple[bool, int, int]:
        """Check sliding window limit for key.

        Returns:
            tuple of (is_limited: bool, retry_after: int, remaining: int)
        """
        client = self.get_client()
        if client is None:
            # Fail open if Redis is unavailable: never crash or block requests
            return False, 0, limit

        now = time.time()
        window_start = now - window_seconds

        try:
            pipe = client.pipeline()
            # 1. Remove timestamps outside the sliding window
            pipe.zremrangebyscore(key, "-inf", window_start)
            # 2. Count requests currently in the window
            pipe.zcard(key)
            # 3. Retrieve the oldest request in the current window to compute retry_after
            pipe.zrange(key, 0, 0, withscores=True)
            results = pipe.execute()

            current_count = results[1]
            oldest_entries = results[2]

            if current_count >= limit:
                if oldest_entries:
                    oldest_ts = oldest_entries[0][1]
                    retry_after = max(1, int(oldest_ts + window_seconds - now))
                else:
                    retry_after = window_seconds
                return True, retry_after, 0

            # Under the limit: add the current timestamp and refresh expiration
            member = f"{now}:{time.time_ns()}"
            pipe = client.pipeline()
            pipe.zadd(key, {member: now})
            pipe.expire(key, window_seconds + 5)
            pipe.execute()

            remaining = max(0, limit - (current_count + 1))
            return False, 0, remaining

        except Exception as exc:
            self._last_connect_failure = time.time()
            self._client = None
            logger.warning("Redis rate limit operation failed; failing open: %s", exc)
            return False, 0, limit



class RateLimitMiddleware(BaseHTTPMiddleware):
    """Starlette middleware implementing sliding-window rate limiting.

    Provides three tiers of limits:
    - Per-IP rate limiting for unauthenticated requests
    - Per-user rate limiting for authenticated requests
    - Per-target rate limiting for snapshot collection operations
    """

    def __init__(
        self,
        app,
        redis_client: Redis | None = None,
        enabled: bool | None = None,
        ip_limit: int | None = None,
        ip_window: int = 60,
        user_limit: int | None = None,
        user_window: int = 60,
        target_collection_limit: int | None = None,
        target_collection_window: int = 3600,
    ) -> None:
        super().__init__(app)
        self.limiter = RateLimiter(redis_client)
        self.enabled = enabled if enabled is not None else getattr(settings, "rate_limit_enabled", True)
        self.ip_limit = ip_limit or getattr(settings, "rate_limit_per_minute", 60)
        self.ip_window = ip_window
        self.user_limit = user_limit or getattr(settings, "rate_limit_user_per_minute", 120)
        self.user_window = user_window
        self.target_collection_limit = target_collection_limit or getattr(
            settings, "rate_limit_collection_per_hour", 10
        )
        self.target_collection_window = target_collection_window

    def _get_client_ip(self, request: Request) -> str:
        """Extract the client IP address from proxy headers or connection info."""
        x_forwarded_for = request.headers.get("x-forwarded-for")
        if x_forwarded_for:
            # Client IP is the first address in the chain
            ip = x_forwarded_for.split(",")[0].strip()
            if ip:
                return ip

        x_real_ip = request.headers.get("x-real-ip")
        if x_real_ip and x_real_ip.strip():
            return x_real_ip.strip()

        if request.client and request.client.host:
            return request.client.host

        return "127.0.0.1"

    def _get_auth_user_identifier(self, request: Request) -> str | None:
        """Extract authenticated user identifier if present, without logging credentials."""
        # 1. Check request state (set by upstream auth middleware)
        user = getattr(request.state, "user", None)
        if user is not None:
            if isinstance(user, dict):
                uid = user.get("id") or user.get("sub")
                if uid:
                    return str(uid)
            uid = getattr(user, "id", None) or getattr(user, "sub", None)
            if uid:
                return str(uid)
            return str(user)

        user_id = getattr(request.state, "user_id", None)
        if user_id:
            return str(user_id)

        # 2. Check X-User-ID header if provided
        header_user_id = request.headers.get("x-user-id")
        if header_user_id and header_user_id.strip():
            return header_user_id.strip()

        # 3. Check Authorization Bearer header: hash token to avoid storing raw secrets
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()
            if token:
                # Store one-way hash of token, never the token itself
                return hashlib.sha256(token.encode("utf-8")).hexdigest()[:16]

        return None

    def _extract_target_id_for_collection(self, request: Request) -> str | None:
        """Return target_id if the request is a snapshot collection POST."""
        if request.method.upper() != "POST":
            return None
        match = TARGET_SNAPSHOT_PATH_REGEX.match(request.url.path)
        if match:
            return match.group(1)
        return None

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Check if rate limiting is enabled, route is excluded, or OPTIONS preflight
        if not self.enabled or request.url.path in EXCLUDED_PATHS or request.method.upper() == "OPTIONS":
            return await call_next(request)

        now = time.time()

        # ── 1. Target Collection Rate Limiting ────────────────────────────
        target_id = self._extract_target_id_for_collection(request)
        if target_id:
            target_key = f"ratelimit:target:{target_id}:snapshots"
            limited, retry_after, remaining = self.limiter.check_limit(
                key=target_key,
                limit=self.target_collection_limit,
                window_seconds=self.target_collection_window,
            )
            if limited:
                logger.warning(
                    "Target collection rate limit exceeded for target %s (limit: %d/%ds)",
                    target_id,
                    self.target_collection_limit,
                    self.target_collection_window,
                )
                return JSONResponse(
                    status_code=429,
                    content={
                        "detail": (
                            f"Target collection rate limit exceeded for target {target_id}. "
                            f"Limit is {self.target_collection_limit} collections per hour."
                        ),
                        "retry_after": retry_after,
                    },
                    headers={
                        "Retry-After": str(retry_after),
                        "X-RateLimit-Limit": str(self.target_collection_limit),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": str(int(now + retry_after)),
                    },
                )

        # ── 2. Per-User or Per-IP Rate Limiting ───────────────────────────
        auth_user = self._get_auth_user_identifier(request)
        if auth_user:
            limit_key = f"ratelimit:user:{auth_user}"
            limit_value = self.user_limit
            window_value = self.user_window
        else:
            client_ip = self._get_client_ip(request)
            limit_key = f"ratelimit:ip:{client_ip}"
            limit_value = self.ip_limit
            window_value = self.ip_window

        limited, retry_after, remaining = self.limiter.check_limit(
            key=limit_key,
            limit=limit_value,
            window_seconds=window_value,
        )

        if limited:
            logger.warning(
                "Rate limit exceeded for key %s (limit: %d/%ds)",
                limit_key,
                limit_value,
                window_value,
            )
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Rate limit exceeded. Please try again later.",
                    "retry_after": retry_after,
                },
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(limit_value),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(now + retry_after)),
                },
            )

        # Request allowed: proceed to endpoint
        response = await call_next(request)

        # Add rate limit headers to response
        response.headers["X-RateLimit-Limit"] = str(limit_value)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(now + window_value))

        return response
