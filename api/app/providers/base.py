"""Base provider interface for all external data sources.

Every provider implements a consistent interface for health checking,
availability detection, data fetching, normalization, error handling,
rate limiting, retry behavior, and caching.

Provider errors are isolated - one failed provider never crashes the app.
"""
from __future__ import annotations

import abc
import asyncio
import hashlib
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)


class ProviderStatus(str, Enum):
    CONFIGURED = "configured"
    AUTHENTICATED = "authenticated"
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    FAILED = "failed"
    NOT_CONFIGURED = "not_configured"


@dataclass
class ProviderHealth:
    """Health check result for a provider."""
    name: str
    status: ProviderStatus
    error_summary: str | None = None
    recommended_fix: str | None = None
    last_checked: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class NormalizedRecord:
    """A provider-normalized data record with provenance."""
    source: str
    source_url: str
    title: str
    summary: str
    event_type: str
    published_at: datetime | None = None
    observed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    content_hash: str = ""
    evidence_reference: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


class RateLimiter:
    """Simple token bucket rate limiter."""

    def __init__(self, max_requests: int = 30, window_seconds: float = 60.0):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._timestamps: list[float] = []

    async def acquire(self) -> None:
        now = time.monotonic()
        self._timestamps = [t for t in self._timestamps if now - t < self.window_seconds]
        if len(self._timestamps) >= self.max_requests:
            wait = self.window_seconds - (now - self._timestamps[0])
            if wait > 0:
                logger.debug("Rate limiter sleeping %.1fs", wait)
                await asyncio.sleep(wait)
        self._timestamps.append(time.monotonic())


class BaseProvider(abc.ABC):
    """Abstract base for all external data providers."""

    def __init__(self, name: str, rate_limiter: RateLimiter | None = None):
        self.name = name
        self._rate_limiter = rate_limiter or RateLimiter()
        self._cache: dict[str, tuple[float, Any]] = {}
        self._cache_ttl: float = 300.0  # 5 minutes default
        self.logger = logging.getLogger(f"provider.{name}")

    @abc.abstractmethod
    def is_configured(self) -> bool:
        """Whether required credentials/config are present."""
        ...

    @abc.abstractmethod
    async def check_health(self) -> ProviderHealth:
        """Run a safe health check. Never expose credentials."""
        ...

    @abc.abstractmethod
    async def fetch(self, **kwargs: Any) -> list[NormalizedRecord]:
        """Fetch and normalize data from the provider."""
        ...

    async def safe_health(self) -> ProviderHealth:
        """Health check wrapper that catches all errors."""
        try:
            return await self.check_health()
        except Exception as exc:
            return ProviderHealth(
                name=self.name,
                status=ProviderStatus.FAILED,
                error_summary=type(exc).__name__,
                recommended_fix="Check provider configuration and network connectivity.",
            )

    def _cache_key(self, **kwargs: Any) -> str:
        raw = ":".join(f"{k}={v}" for k, v in sorted(kwargs.items()))
        return hashlib.sha256(raw.encode()).hexdigest()

    def _get_cached(self, key: str) -> Any | None:
        if key in self._cache:
            ts, data = self._cache[key]
            if time.monotonic() - ts < self._cache_ttl:
                return data
            del self._cache[key]
        return None

    def _set_cached(self, key: str, data: Any) -> None:
        self._cache[key] = (time.monotonic(), data)

    async def _request_with_retry(
        self,
        client: httpx.AsyncClient,
        method: str,
        url: str,
        *,
        max_retries: int = 3,
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> httpx.Response:
        """Make an HTTP request with rate limiting and retry."""
        await self._rate_limiter.acquire()
        last_exc: Exception | None = None
        for attempt in range(max_retries):
            try:
                response = await client.request(
                    method, url, headers=headers, params=params, json=json_body,
                )
                if response.status_code == 429:
                    retry_after = float(response.headers.get("retry-after", str(2 ** attempt)))
                    self.logger.warning("Rate limited, waiting %.1fs", retry_after)
                    await asyncio.sleep(retry_after)
                    continue
                if response.status_code >= 500:
                    await asyncio.sleep(2 ** attempt)
                    continue
                return response
            except httpx.HTTPError as exc:
                last_exc = exc
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
        raise last_exc or RuntimeError(f"Request to {url} failed after {max_retries} retries")
