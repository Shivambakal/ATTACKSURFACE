"""Censys Platform REST API Provider.

Integrates with the Censys Platform REST API:
https://docs.censys.com/reference/get-started
https://search.censys.io/api/v2

Authentication:
Authorization: Bearer <CENSYS_API_KEY> (Personal Access Token)
Optional: X-Organization-ID: <CENSYS_ORGANIZATION_ID>

IMPORTANT:
Censys data represents public internet observations.
Never equate IP/host observation with verified company asset ownership
without entity attribution.
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


class CensysProvider(BaseProvider):
    """Adapter for Censys Platform REST API (v2)."""

    BASE_URL = "https://search.censys.io/api/v2"

    def __init__(self, rate_limiter: RateLimiter | None = None) -> None:
        super().__init__("censys", rate_limiter or RateLimiter(max_requests=120, window_seconds=60.0))
        self.api_key = settings.censys_api_key
        self.org_id = settings.censys_organization_id

    def is_configured(self) -> bool:
        return bool(self.api_key)

    def _headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/json",
            "User-Agent": "AttackSurfaceTimeline/0.1 (authorized security research)",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        if self.org_id:
            headers["X-Organization-ID"] = self.org_id
        return headers

    async def check_health(self) -> ProviderHealth:
        if not self.is_configured():
            return ProviderHealth(
                name=self.name,
                status=ProviderStatus.NOT_CONFIGURED,
                error_summary="CENSYS_API_KEY is not configured.",
                recommended_fix="Set CENSYS_API_KEY (Censys Personal Access Token) in server environment.",
            )

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Lightweight account/quota or sample search check
                resp = await client.get(
                    f"{self.BASE_URL}/hosts/search",
                    headers=self._headers(),
                    params={"q": "8.8.8.8", "per_page": 1},
                )
                if resp.status_code == 200:
                    return ProviderHealth(name=self.name, status=ProviderStatus.AVAILABLE)
                elif resp.status_code in (401, 403):
                    return ProviderHealth(
                        name=self.name,
                        status=ProviderStatus.FAILED,
                        error_summary="Authentication failed (HTTP 401/403). Check PAT validity.",
                        recommended_fix="Verify CENSYS_API_KEY Personal Access Token permissions.",
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
                        recommended_fix="Check Censys API platform availability.",
                    )
        except Exception as exc:
            return ProviderHealth(
                name=self.name,
                status=ProviderStatus.FAILED,
                error_summary=type(exc).__name__,
                recommended_fix="Verify network connectivity to search.censys.io.",
            )

    async def fetch(
        self,
        target: str = "",
        ip: str | None = None,
        query: str | None = None,
        **kwargs: Any,
    ) -> list[NormalizedRecord]:
        """Query Censys for host observations or domain searches."""
        if not self.is_configured():
            return []

        search_query = query or (f"services.tls.certificates.leaf_data.names: {target}" if target else None)
        lookup_ip = ip

        cache_key = self._cache_key(target=target, ip=str(ip), query=str(query))
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        records: list[NormalizedRecord] = []

        try:
            async with httpx.AsyncClient(timeout=25.0) as client:
                # Direct IP Host lookup if IP provided
                if lookup_ip:
                    url = f"{self.BASE_URL}/hosts/{lookup_ip}"
                    resp = await self._request_with_retry(client, "GET", url, headers=self._headers())
                    if resp.status_code == 200:
                        host_data = resp.json().get("result", {})
                        records.extend(self.normalize_host_result(host_data, target=target or lookup_ip))
                # Search query if target or query provided
                elif search_query:
                    url = f"{self.BASE_URL}/hosts/search"
                    params = {"q": search_query, "per_page": 10}
                    resp = await self._request_with_retry(client, "GET", url, headers=self._headers(), params=params)
                    if resp.status_code == 200:
                        hits = resp.json().get("result", {}).get("hits", [])
                        for hit in hits:
                            records.extend(self.normalize_search_hit(hit, target=target))

            self._set_cached(cache_key, records)
            return records
        except Exception as exc:
            logger.warning("Censys fetch failed: %s", exc)
            return []

    def normalize_host_result(self, host: dict[str, Any], target: str) -> list[NormalizedRecord]:
        """Normalizes a Censys /hosts/{ip} object."""
        records: list[NormalizedRecord] = []
        ip = host.get("ip", "unknown")
        services = host.get("services", [])
        last_observed = host.get("last_observed_at")
        observed_dt = datetime.fromisoformat(last_observed.replace("Z", "+00:00")) if last_observed else datetime.now(timezone.utc)

        # Service / Port observations
        ports = [s.get("port") for s in services if "port" in s]
        service_names = [s.get("service_name") for s in services if "service_name" in s]

        content_hash = hashlib.sha256(f"censys:host:{ip}:{sorted(ports)}".encode()).hexdigest()

        records.append(
            NormalizedRecord(
                source="CENSYS",
                source_url=f"https://search.censys.io/hosts/{ip}",
                title=f"Censys observed infrastructure for {ip} (Ports: {', '.join(map(str, ports[:5]))})",
                summary=f"Public Internet scan observed host {ip} running services: {', '.join(filter(None, service_names[:5]))}. Note: Ownership requires verification.",
                event_type="INFRASTRUCTURE_OBSERVATION",
                published_at=observed_dt,
                observed_at=observed_dt,
                content_hash=content_hash,
                evidence_reference=f"censys:{ip}",
                metadata={
                    "ip": ip,
                    "target": target,
                    "ports": ports,
                    "services": service_names,
                    "autonomous_system": host.get("autonomous_system", {}),
                    "location": host.get("location", {}),
                    "operating_system": host.get("operating_system", {}),
                    "authority_level": "INTERNET_SCAN_OBSERVATION",
                    "evidence_type": "PORT_SERVICE_OBSERVATION",
                },
            )
        )

        return records

    def normalize_search_hit(self, hit: dict[str, Any], target: str) -> list[NormalizedRecord]:
        """Normalizes a Censys search hit."""
        records: list[NormalizedRecord] = []
        ip = hit.get("ip", "unknown")
        services = hit.get("services", [])
        ports = [s.get("port") for s in services if isinstance(s, dict) and "port" in s]

        content_hash = hashlib.sha256(f"censys:hit:{ip}:{target}".encode()).hexdigest()

        records.append(
            NormalizedRecord(
                source="CENSYS",
                source_url=f"https://search.censys.io/hosts/{ip}",
                title=f"Censys search candidate host {ip} related to {target}",
                summary=f"Observed IP {ip} matching certificate or DNS query for {target}. Ports: {ports}.",
                event_type="ASSET_CANDIDATE",
                published_at=datetime.now(timezone.utc),
                observed_at=datetime.now(timezone.utc),
                content_hash=content_hash,
                evidence_reference=f"censys:search:{ip}:{target}",
                metadata={
                    "ip": ip,
                    "target": target,
                    "ports": ports,
                    "raw_hit": hit,
                    "authority_level": "INTERNET_SCAN_OBSERVATION",
                    "evidence_type": "PASSIVE_SEARCH_RESULT",
                },
            )
        )
        return records
