"""Public Certificate Transparency (CT) Log Provider.

Queries public CT log datasets (such as crt.sh) to discover newly issued
TLS certificates, hostnames, and domain ownership evolutions.

SAFETY & ETHICAL RULES:
- Strictly passive public log consumption.
- CT entries represent cryptographic certificates, NOT confirmed ownership or scope.
- Must pass Entity Resolution and Scope Resolution before marking IN_SCOPE.
"""
from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from typing import Any

import httpx

from .base import BaseProvider, NormalizedRecord, ProviderHealth, ProviderStatus, RateLimiter

logger = logging.getLogger(__name__)


class CertificateTransparencyProvider(BaseProvider):
    """Adapter for Public Certificate Transparency Logs (crt.sh)."""

    BASE_URL = "https://crt.sh"

    def __init__(self, rate_limiter: RateLimiter | None = None) -> None:
        super().__init__("certificate_transparency", rate_limiter or RateLimiter(max_requests=30, window_seconds=60.0))

    def is_configured(self) -> bool:
        # Public CT logs do not require an API key
        return True

    async def check_health(self) -> ProviderHealth:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    self.BASE_URL,
                    params={"q": "example.com", "output": "json"},
                )
                if resp.status_code == 200:
                    return ProviderHealth(name=self.name, status=ProviderStatus.AVAILABLE)
                elif resp.status_code == 429:
                    return ProviderHealth(
                        name=self.name,
                        status=ProviderStatus.UNAVAILABLE,
                        error_summary="crt.sh rate limit reached.",
                    )
                else:
                    return ProviderHealth(
                        name=self.name,
                        status=ProviderStatus.FAILED,
                        error_summary=f"HTTP {resp.status_code}",
                        recommended_fix="Public crt.sh service may be experiencing high load.",
                    )
        except Exception as exc:
            return ProviderHealth(
                name=self.name,
                status=ProviderStatus.FAILED,
                error_summary=type(exc).__name__,
                recommended_fix="Verify connectivity to crt.sh.",
            )

    async def fetch(
        self,
        target: str = "",
        domain: str | None = None,
        **kwargs: Any,
    ) -> list[NormalizedRecord]:
        """Fetch issued certificates for a domain from public CT logs."""
        lookup_domain = domain or target
        if not lookup_domain:
            return []

        cache_key = self._cache_key(domain=lookup_domain)
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        records: list[NormalizedRecord] = []

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await self._request_with_retry(
                    client,
                    "GET",
                    self.BASE_URL,
                    params={"q": f"%.{lookup_domain}", "output": "json"},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    records.extend(self.normalize_ct_records(data, domain=lookup_domain))

            self._set_cached(cache_key, records)
            return records
        except Exception as exc:
            logger.warning("Certificate Transparency fetch failed: %s", exc)
            return []

    def normalize_ct_records(self, certs: list[dict[str, Any]], domain: str) -> list[NormalizedRecord]:
        """Normalizes crt.sh output into NormalizedRecord objects."""
        records: list[NormalizedRecord] = []
        seen_hashes = set()

        for cert in certs[:50]:  # Limit to 50 most recent
            cert_id = str(cert.get("id", ""))
            issuer = cert.get("issuer_name", "")
            entry_timestamp = cert.get("entry_timestamp")
            names_raw = cert.get("name_value", "")
            names = [n.strip() for n in names_raw.split("\n") if n.strip()]

            content_hash = hashlib.sha256(f"ct:{cert_id}:{names_raw}".encode()).hexdigest()
            if content_hash in seen_hashes:
                continue
            seen_hashes.add(content_hash)

            pub_dt = datetime.fromisoformat(entry_timestamp.replace("Z", "+00:00")) if entry_timestamp else datetime.now(timezone.utc)

            for name in names[:5]:
                records.append(
                    NormalizedRecord(
                        source="CERTIFICATE_TRANSPARENCY",
                        source_url=f"https://crt.sh/?id={cert_id}",
                        title=f"New TLS Certificate observed for {name} (Issuer: {issuer[:40]})",
                        summary=f"Public CT log entry {cert_id} logged for hostname {name}. Does not imply asset is in-scope.",
                        event_type="CERTIFICATE_CHANGE",
                        published_at=pub_dt,
                        observed_at=datetime.now(timezone.utc),
                        content_hash=content_hash,
                        evidence_reference=f"crt.sh:{cert_id}",
                        metadata={
                            "domain": domain,
                            "hostname": name,
                            "cert_id": cert_id,
                            "issuer": issuer,
                            "not_before": cert.get("not_before"),
                            "not_after": cert.get("not_after"),
                            "authority_level": "PUBLIC_CT_LOG",
                            "evidence_type": "CERTIFICATE_LOG_ENTRY",
                        },
                    )
                )

        return records
