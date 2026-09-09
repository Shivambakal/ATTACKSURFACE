"""Shodan Passive Intelligence Provider.

Integrates with the official Shodan API:
https://developer.shodan.io/api
https://api.shodan.io

Features:
- Passive DNS / domain lookup (/dns/domain/{domain})
- Passive Host lookup (/shodan/host/{ip})
- Account / plan quota checks (/api-info)

SAFETY & ETHICAL RULES:
- Exclusively uses passive cached observations.
- NEVER triggers active Shodan scan operations (/shodan/scan).
- NEVER converts banner metadata into vulnerability claims.
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


class ShodanProvider(BaseProvider):
    """Adapter for Shodan Passive Intelligence API."""

    BASE_URL = "https://api.shodan.io"

    def __init__(self, rate_limiter: RateLimiter | None = None) -> None:
        super().__init__("shodan", rate_limiter or RateLimiter(max_requests=60, window_seconds=60.0))
        self.api_key = settings.shodan_api_key

    def is_configured(self) -> bool:
        return bool(self.api_key)

    async def check_health(self) -> ProviderHealth:
        if not self.is_configured():
            return ProviderHealth(
                name=self.name,
                status=ProviderStatus.NOT_CONFIGURED,
                error_summary="SHODAN_API_KEY is not configured.",
                recommended_fix="Set SHODAN_API_KEY in server environment.",
            )

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{self.BASE_URL}/api-info",
                    params={"key": self.api_key},
                )
                if resp.status_code == 200:
                    info = resp.json()
                    plan = info.get("plan", "unknown")
                    scan_credits = info.get("scan_credits", 0)
                    query_credits = info.get("query_credits", 0)
                    logger.info("Shodan account plan: %s (query credits: %s)", plan, query_credits)
                    return ProviderHealth(name=self.name, status=ProviderStatus.AVAILABLE)
                elif resp.status_code in (401, 403):
                    return ProviderHealth(
                        name=self.name,
                        status=ProviderStatus.FAILED,
                        error_summary="Invalid SHODAN_API_KEY (HTTP 401/403).",
                        recommended_fix="Verify your Shodan API key.",
                    )
                elif resp.status_code == 429:
                    return ProviderHealth(
                        name=self.name,
                        status=ProviderStatus.UNAVAILABLE,
                        error_summary="Shodan API rate limit reached.",
                    )
                else:
                    return ProviderHealth(
                        name=self.name,
                        status=ProviderStatus.FAILED,
                        error_summary=f"HTTP {resp.status_code}",
                        recommended_fix="Verify Shodan API service status.",
                    )
        except Exception as exc:
            return ProviderHealth(
                name=self.name,
                status=ProviderStatus.FAILED,
                error_summary=type(exc).__name__,
                recommended_fix="Verify network connectivity to api.shodan.io.",
            )

    async def fetch(
        self,
        target: str = "",
        ip: str | None = None,
        domain: str | None = None,
        history: bool = False,
        **kwargs: Any,
    ) -> list[NormalizedRecord]:
        """Fetch passive observations from Shodan for a domain or IP."""
        if not self.is_configured():
            return []

        lookup_domain = domain or target
        lookup_ip = ip

        cache_key = self._cache_key(target=target, ip=str(ip), domain=str(domain), history=str(history))
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        records: list[NormalizedRecord] = []

        try:
            async with httpx.AsyncClient(timeout=25.0) as client:
                # 1. Host IP Lookup if provided
                if lookup_ip:
                    params: dict[str, Any] = {"key": self.api_key}
                    if history:
                        params["history"] = "true"

                    resp = await self._request_with_retry(
                        client,
                        "GET",
                        f"{self.BASE_URL}/shodan/host/{lookup_ip}",
                        params=params,
                    )
                    if resp.status_code == 200:
                        host_data = resp.json()
                        records.extend(self.normalize_host_data(host_data, target=lookup_ip))

                # 2. Domain DNS Lookup if domain provided
                elif lookup_domain:
                    resp = await self._request_with_retry(
                        client,
                        "GET",
                        f"{self.BASE_URL}/dns/domain/{lookup_domain}",
                        params={"key": self.api_key},
                    )
                    if resp.status_code == 200:
                        domain_data = resp.json()
                        records.extend(self.normalize_domain_data(domain_data, domain=lookup_domain))

            self._set_cached(cache_key, records)
            return records
        except Exception as exc:
            logger.warning("Shodan fetch failed: %s", exc)
            return []

    def normalize_host_data(self, data: dict[str, Any], target: str) -> list[NormalizedRecord]:
        """Normalizes Shodan /shodan/host/{ip} output."""
        records: list[NormalizedRecord] = []
        ip = data.get("ip_str", target)
        ports = data.get("ports", [])
        hostnames = data.get("hostnames", [])
        last_update = data.get("last_update")
        obs_dt = datetime.fromisoformat(last_update.replace("Z", "+00:00")) if last_update else datetime.now(timezone.utc)

        content_hash = hashlib.sha256(f"shodan:host:{ip}:{sorted(ports)}".encode()).hexdigest()

        records.append(
            NormalizedRecord(
                source="SHODAN",
                source_url=f"https://www.shodan.io/host/{ip}",
                title=f"Shodan observed host {ip} (Ports: {', '.join(map(str, ports[:5]))})",
                summary=f"Passive Shodan scan observed ports {ports} on host {ip} (Hostnames: {', '.join(hostnames[:3])}). Banners represent observation only, not confirmed vulnerabilities.",
                event_type="INFRASTRUCTURE_OBSERVATION",
                published_at=obs_dt,
                observed_at=obs_dt,
                content_hash=content_hash,
                evidence_reference=f"shodan:{ip}",
                metadata={
                    "ip": ip,
                    "target": target,
                    "ports": ports,
                    "hostnames": hostnames,
                    "os": data.get("os"),
                    "isp": data.get("isp"),
                    "asn": data.get("asn"),
                    "authority_level": "INTERNET_SCAN_OBSERVATION",
                    "evidence_type": "PORT_SERVICE_OBSERVATION",
                },
            )
        )
        return records

    def normalize_domain_data(self, data: dict[str, Any], domain: str) -> list[NormalizedRecord]:
        """Normalizes Shodan /dns/domain/{domain} output."""
        records: list[NormalizedRecord] = []
        subdomains = data.get("subdomains", [])
        data_records = data.get("data", [])

        for sub in subdomains[:20]:
            fqdn = f"{sub}.{domain}"
            content_hash = hashlib.sha256(f"shodan:subdomain:{fqdn}".encode()).hexdigest()
            records.append(
                NormalizedRecord(
                    source="SHODAN",
                    source_url=f"https://www.shodan.io/search?query=hostname:{fqdn}",
                    title=f"Shodan DNS observed subdomain: {fqdn}",
                    summary=f"Passive DNS record from Shodan discovered candidate subdomain {fqdn}. Requires scope resolution.",
                    event_type="ASSET_CANDIDATE",
                    published_at=datetime.now(timezone.utc),
                    observed_at=datetime.now(timezone.utc),
                    content_hash=content_hash,
                    evidence_reference=f"shodan:dns:{fqdn}",
                    metadata={
                        "domain": domain,
                        "subdomain": sub,
                        "fqdn": fqdn,
                        "authority_level": "PASSIVE_DNS_DATASET",
                        "evidence_type": "SUBDOMAIN_DISCOVERY",
                    },
                )
            )

        return records
