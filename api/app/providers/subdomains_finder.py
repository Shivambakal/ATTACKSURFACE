"""Subdomains Finder Provider Adapter.

Status: UNVERIFIED
Until official documentation or live authenticated tests confirm the exact endpoint,
this adapter enforces UNVERIFIED / DISABLED state at runtime.

Uses verified mock fixture structure for test suites and schema compatibility.
"""
from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from typing import Any

from ..config import settings
from .base import BaseProvider, NormalizedRecord, ProviderHealth, ProviderStatus, RateLimiter

logger = logging.getLogger(__name__)

# Documented response schema fixture
SUBDOMAINS_FINDER_FIXTURE = {
    "status": "success",
    "domain": "example.com",
    "subdomains_count": 3,
    "subdomains": [
        {"subdomain": "api.example.com", "ip": "93.184.216.34", "first_seen": "2025-01-01T00:00:00Z"},
        {"subdomain": "auth.example.com", "ip": "93.184.216.35", "first_seen": "2025-02-01T00:00:00Z"},
        {"subdomain": "staging.example.com", "ip": "93.184.216.36", "first_seen": "2025-03-01T00:00:00Z"},
    ]
}


class SubdomainsFinderProvider(BaseProvider):
    """Adapter for Subdomains Finder API (Enforced UNVERIFIED status)."""

    def __init__(self, rate_limiter: RateLimiter | None = None) -> None:
        super().__init__("subdomains_finder", rate_limiter or RateLimiter(max_requests=30, window_seconds=60.0))
        self.api_key = settings.subdomains_finder_api_key
        # Enforce UNVERIFIED state until live endpoint is verified
        self.status = ProviderStatus.UNAVAILABLE

    def is_configured(self) -> bool:
        return bool(self.api_key)

    async def check_health(self) -> ProviderHealth:
        if not self.is_configured():
            return ProviderHealth(
                name=self.name,
                status=ProviderStatus.NOT_CONFIGURED,
                error_summary="SUBDOMAINS_FINDER_API_KEY is not configured.",
                recommended_fix="Set SUBDOMAINS_FINDER_API_KEY in server environment.",
            )

        # Unverified provider warning
        return ProviderHealth(
            name=self.name,
            status=ProviderStatus.UNAVAILABLE,
            error_summary="Provider status is UNVERIFIED. Awaiting verified endpoint documentation.",
            recommended_fix="Provide confirmed official API documentation before enabling live polling.",
        )

    async def fetch(self, target: str = "", **kwargs: Any) -> list[NormalizedRecord]:
        """Disabled at runtime unless running in mock test mode."""
        if kwargs.get("use_fixture", False):
            return self.normalize_payload(SUBDOMAINS_FINDER_FIXTURE, domain=target or "example.com")
        return []

    def normalize_payload(self, data: dict[str, Any], domain: str) -> list[NormalizedRecord]:
        """Normalizes documented fixture into NormalizedRecord objects."""
        records: list[NormalizedRecord] = []
        subs = data.get("subdomains", [])

        for item in subs:
            fqdn = item.get("subdomain") or f"{item.get('name')}.{domain}"
            ip = item.get("ip", "")
            first_seen_str = item.get("first_seen")
            obs_dt = datetime.fromisoformat(first_seen_str.replace("Z", "+00:00")) if first_seen_str else datetime.now(timezone.utc)
            content_hash = hashlib.sha256(f"subdomains_finder:{fqdn}:{ip}".encode()).hexdigest()

            records.append(
                NormalizedRecord(
                    source="SUBDOMAINS_FINDER",
                    source_url=f"https://subdomains-finder.local/query?domain={domain}",
                    title=f"Subdomains Finder discovered candidate subdomain: {fqdn}",
                    summary=f"Subdomain enumeration discovered {fqdn} (IP: {ip}). Note: Unverified source, requires scope validation.",
                    event_type="ASSET_CANDIDATE",
                    published_at=obs_dt,
                    observed_at=obs_dt,
                    content_hash=content_hash,
                    evidence_reference=f"subdomains_finder:{fqdn}",
                    metadata={
                        "domain": domain,
                        "subdomain": fqdn,
                        "ip": ip,
                        "authority_level": "UNVERIFIED_THIRD_PARTY",
                        "evidence_type": "SUBDOMAIN_DISCOVERY",
                        "raw_item": item,
                    },
                )
            )

        return records
