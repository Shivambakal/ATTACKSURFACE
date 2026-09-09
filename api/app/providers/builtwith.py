"""BuiltWith Technographic Change Provider.

Integrates with the BuiltWith Change API:
https://api.builtwith.com/change-api (/change1/api.json)

Tracks technology additions and removals over configurable time windows.
Supports multi-domain batch lookups and incremental SINCE timestamps.

IMPORTANT:
BuiltWith data represents external technographic telemetry,
NOT direct proof of production deployment.
"""
from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Any

import httpx

from ..config import settings
from .base import BaseProvider, NormalizedRecord, ProviderHealth, ProviderStatus, RateLimiter

logger = logging.getLogger(__name__)


class BuiltWithProvider(BaseProvider):
    """Adapter for BuiltWith Change API."""

    BASE_URL = "https://api.builtwith.com/change1/api.json"

    def __init__(self, rate_limiter: RateLimiter | None = None) -> None:
        super().__init__("builtwith", rate_limiter or RateLimiter(max_requests=60, window_seconds=60.0))
        self.api_key = settings.builtwith_api_key

    def is_configured(self) -> bool:
        return bool(self.api_key)

    async def check_health(self) -> ProviderHealth:
        if not self.is_configured():
            return ProviderHealth(
                name=self.name,
                status=ProviderStatus.NOT_CONFIGURED,
                error_summary="BUILTWITH_API_KEY is not configured.",
                recommended_fix="Set BUILTWITH_API_KEY in server environment.",
            )

        # Lightweight check with mock or sample query
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    self.BASE_URL,
                    params={"KEY": self.api_key, "LOOKUP": "example.com"},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    if "Errors" in data and data["Errors"]:
                        return ProviderHealth(
                            name=self.name,
                            status=ProviderStatus.FAILED,
                            error_summary=str(data["Errors"]),
                            recommended_fix="Verify BuiltWith API key validity and quota.",
                        )
                    return ProviderHealth(name=self.name, status=ProviderStatus.AVAILABLE)
                elif resp.status_code == 429:
                    return ProviderHealth(
                        name=self.name,
                        status=ProviderStatus.UNAVAILABLE,
                        error_summary="Rate limited (HTTP 429).",
                    )
                else:
                    return ProviderHealth(
                        name=self.name,
                        status=ProviderStatus.FAILED,
                        error_summary=f"HTTP {resp.status_code}",
                        recommended_fix="Check BuiltWith API status and subscription.",
                    )
        except Exception as exc:
            return ProviderHealth(
                name=self.name,
                status=ProviderStatus.FAILED,
                error_summary=type(exc).__name__,
                recommended_fix="Verify network connectivity to api.builtwith.com.",
            )

    async def fetch(
        self,
        target: str = "",
        domains: list[str] | None = None,
        since: datetime | None = None,
        **kwargs: Any,
    ) -> list[NormalizedRecord]:
        """Fetch technographic changes for single or multiple domains."""
        if not self.is_configured():
            return []

        lookup_domains = domains or ([target] if target else [])
        if not lookup_domains:
            return []

        # BuiltWith supports comma-separated domains in LOOKUP
        lookup_str = ",".join(d.strip() for d in lookup_domains if d.strip())
        params: dict[str, Any] = {
            "KEY": self.api_key,
            "LOOKUP": lookup_str,
        }
        if since:
            params["SINCE"] = since.strftime("%Y-%m-%d")

        cache_key = self._cache_key(lookup=lookup_str, since=str(since))
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        try:
            async with httpx.AsyncClient(timeout=25.0) as client:
                resp = await self._request_with_retry(
                    client,
                    "GET",
                    self.BASE_URL,
                    params=params,
                )
                if resp.status_code != 200:
                    logger.warning("BuiltWith responded with HTTP %d", resp.status_code)
                    return []

                payload = resp.json()
                records = self.normalize_payload(payload)
                self._set_cached(cache_key, records)
                return records
        except Exception as exc:
            logger.warning("BuiltWith fetch failed: %s", exc)
            return []

    def normalize_payload(self, payload: dict[str, Any]) -> list[NormalizedRecord]:
        """Normalizes BuiltWith Change API response into NormalizedRecord objects."""
        records: list[NormalizedRecord] = []
        results = payload.get("results") or payload.get("Results") or []
        if isinstance(payload, list):
            results = payload

        for res in results:
            domain = res.get("lookup") or res.get("Lookup") or "unknown"
            additions = res.get("additions") or res.get("Additions") or []
            removals = res.get("removals") or res.get("Removals") or []

            # Additions
            for item in additions:
                tech_name = item.get("tech") or item.get("Technology") or item.get("name", "Unknown")
                category = item.get("category") or item.get("Category", "Unknown")
                rec_id = f"bw:{domain}:add:{tech_name}"
                content_hash = hashlib.sha256(rec_id.encode()).hexdigest()

                records.append(
                    NormalizedRecord(
                        source="BUILTWITH",
                        source_url=f"https://api.builtwith.com/change1/api.json?LOOKUP={domain}",
                        title=f"BuiltWith detected technology added: {tech_name} on {domain}",
                        summary=f"External technographic scan detected addition of {tech_name} (Category: {category}). Note: Not direct proof of active deployment.",
                        event_type="TECHNOLOGY_ADDED",
                        published_at=datetime.now(timezone.utc),
                        observed_at=datetime.now(timezone.utc),
                        content_hash=content_hash,
                        evidence_reference=f"builtwith:{domain}:{tech_name}",
                        metadata={
                            "domain": domain,
                            "technology": tech_name,
                            "category": category,
                            "change_direction": "ADDED",
                            "evidence_type": "TECHNOGRAPHIC_CHANGE",
                            "authority_level": "THIRD_PARTY_TELEMETRY",
                            "raw_item": item,
                        },
                    )
                )

            # Removals
            for item in removals:
                tech_name = item.get("tech") or item.get("Technology") or item.get("name", "Unknown")
                category = item.get("category") or item.get("Category", "Unknown")
                rec_id = f"bw:{domain}:rem:{tech_name}"
                content_hash = hashlib.sha256(rec_id.encode()).hexdigest()

                records.append(
                    NormalizedRecord(
                        source="BUILTWITH",
                        source_url=f"https://api.builtwith.com/change1/api.json?LOOKUP={domain}",
                        title=f"BuiltWith detected technology removed: {tech_name} on {domain}",
                        summary=f"External technographic scan detected removal of {tech_name} (Category: {category}).",
                        event_type="TECHNOLOGY_REMOVED",
                        published_at=datetime.now(timezone.utc),
                        observed_at=datetime.now(timezone.utc),
                        content_hash=content_hash,
                        evidence_reference=f"builtwith:{domain}:{tech_name}",
                        metadata={
                            "domain": domain,
                            "technology": tech_name,
                            "category": category,
                            "change_direction": "REMOVED",
                            "evidence_type": "TECHNOGRAPHIC_CHANGE",
                            "authority_level": "THIRD_PARTY_TELEMETRY",
                            "raw_item": item,
                        },
                    )
                )

        return records
