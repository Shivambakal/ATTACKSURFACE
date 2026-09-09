"""Domainee.dev Custom Domain & DNS Intelligence Provider.

Integrates with https://api.domainee.dev
Authentication: Authorization: Bearer <DOMAINEE_API_KEY>
Endpoints:
- /v1/domains: registered custom domain routing & SSL status
- /v1/dns: DNS records inspection

SAFETY & ETHICAL RULES:
- Observations represent candidate DNS or custom domain configurations.
- Does not declare assets in scope automatically.
"""
from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from typing import Any

import httpx

from ..config import settings
from .base import BaseProvider, NormalizedRecord, ProviderHealth, ProviderStatus, RateLimiter

logger = logging.getLogger(__name__)


class DomaineeProvider(BaseProvider):
    """Adapter for Domainee.dev API."""

    BASE_URL = "https://api.domainee.dev"

    def __init__(self, rate_limiter: RateLimiter | None = None) -> None:
        super().__init__("domainee", rate_limiter or RateLimiter(max_requests=60, window_seconds=60.0))
        self.api_key = settings.domainee_api_key

    def is_configured(self) -> bool:
        return bool(self.api_key)

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    async def check_health(self) -> ProviderHealth:
        if not self.is_configured():
            return ProviderHealth(
                name=self.name,
                status=ProviderStatus.NOT_CONFIGURED,
                error_summary="DOMAINEE_API_KEY is not configured.",
                recommended_fix="Set DOMAINEE_API_KEY in server environment.",
            )

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{self.BASE_URL}/v1/domains",
                    headers=self._headers(),
                    params={"limit": 1},
                )
                if resp.status_code == 200:
                    return ProviderHealth(name=self.name, status=ProviderStatus.AVAILABLE)
                elif resp.status_code in (401, 403):
                    return ProviderHealth(
                        name=self.name,
                        status=ProviderStatus.FAILED,
                        error_summary=f"Authentication failed (HTTP {resp.status_code}).",
                        recommended_fix="Verify DOMAINEE_API_KEY validity.",
                    )
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
                        recommended_fix="Check api.domainee.dev availability.",
                    )
        except Exception as exc:
            return ProviderHealth(
                name=self.name,
                status=ProviderStatus.FAILED,
                error_summary=type(exc).__name__,
                recommended_fix="Verify network connectivity to api.domainee.dev.",
            )

    async def fetch(
        self,
        target: str = "",
        domain: str | None = None,
        **kwargs: Any,
    ) -> list[NormalizedRecord]:
        """Fetch DNS and domain observations from Domainee.dev."""
        if not self.is_configured():
            return []

        lookup_domain = domain or target
        if not lookup_domain:
            return []

        cache_key = self._cache_key(domain=lookup_domain)
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        records: list[NormalizedRecord] = []

        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                # Query DNS info endpoint if available
                resp = await self._request_with_retry(
                    client,
                    "GET",
                    f"{self.BASE_URL}/v1/dns",
                    headers=self._headers(),
                    params={"domain": lookup_domain},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    records.extend(self.normalize_dns_data(data, domain=lookup_domain))

            self._set_cached(cache_key, records)
            return records
        except Exception as exc:
            logger.warning("Domainee fetch failed: %s", exc)
            return []

    def normalize_dns_data(self, data: dict[str, Any], domain: str) -> list[NormalizedRecord]:
        """Normalizes Domainee DNS/SSL response."""
        records: list[NormalizedRecord] = []
        dns_records = data.get("records") or data.get("dns") or []
        if isinstance(dns_records, dict):
            dns_records = [dns_records]

        for item in dns_records:
            name = item.get("name") or domain
            rtype = item.get("type", "A")
            value = item.get("value") or item.get("data", "")
            rec_id = f"domainee:{domain}:{name}:{rtype}:{value}"
            content_hash = hashlib.sha256(rec_id.encode()).hexdigest()

            records.append(
                NormalizedRecord(
                    source="DOMAINEE",
                    source_url=f"https://domainee.dev/domains/{domain}",
                    title=f"Domainee DNS record for {name} ({rtype} -> {value})",
                    summary=f"Domainee observed DNS record {name} ({rtype}) pointing to {value}.",
                    event_type="DNS_CHANGE",
                    published_at=datetime.now(timezone.utc),
                    observed_at=datetime.now(timezone.utc),
                    content_hash=content_hash,
                    evidence_reference=rec_id,
                    metadata={
                        "domain": domain,
                        "hostname": name,
                        "record_type": rtype,
                        "value": value,
                        "authority_level": "THIRD_PARTY_DNS_TELEMETRY",
                        "evidence_type": "DNS_RECORD_OBSERVATION",
                    },
                )
            )

        return records
