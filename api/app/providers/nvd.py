"""National Vulnerability Database (NVD) data provider.

Queries the official NIST NVD API 2.0 (https://services.nvd.nist.gov/rest/json/cves/2.0).
Supports optional NVD_API_KEY for higher rate limits (50 requests/30s vs 5 requests/30s).
Implements precise rate limiting, caching, and graceful failure handling.
Never logs or exposes the apiKey header.
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

NVD_API_BASE = "https://services.nvd.nist.gov/rest/json/cves/2.0"


def _parse_nvd_timestamp(val: str | None) -> datetime | None:
    if not val:
        return None
    try:
        dt = datetime.fromisoformat(val.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except (ValueError, TypeError):
        return None


class NVDProvider(BaseProvider):
    """Provider for querying the NIST National Vulnerability Database (NVD 2.0)."""

    def __init__(self, rate_limiter: RateLimiter | None = None):
        # 50 req/30s with apiKey, 5 req/30s without apiKey per NIST policy
        max_requests = 50 if settings.nvd_api_key else 5
        limiter = rate_limiter or RateLimiter(max_requests=max_requests, window_seconds=30.0)
        super().__init__(name="nvd", rate_limiter=limiter)
        self._cache_ttl = 3600.0  # 1 hour cache for CVE records

    def is_configured(self) -> bool:
        """Whether an NVD API key is configured."""
        return bool(settings.nvd_api_key)

    def _get_headers(self) -> dict[str, str]:
        """Generate request headers without exposing the API key in logs."""
        headers = {
            "Accept": "application/json",
            "User-Agent": settings.collector_user_agent,
        }
        if settings.nvd_api_key:
            headers["apiKey"] = settings.nvd_api_key
        return headers

    async def check_health(self) -> ProviderHealth:
        """Verify NVD API availability with a minimal 1-result query."""
        url = NVD_API_BASE
        headers = self._get_headers()
        params = {"resultsPerPage": 1}

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(url, headers=headers, params=params)

            if response.status_code == 200:
                status = ProviderStatus.AUTHENTICATED if self.is_configured() else ProviderStatus.AVAILABLE
                return ProviderHealth(
                    name=self.name,
                    status=status,
                    error_summary=None,
                    recommended_fix=None,
                )
            elif response.status_code in (401, 403):
                return ProviderHealth(
                    name=self.name,
                    status=ProviderStatus.FAILED,
                    error_summary="NVD API key invalid or unauthorized.",
                    recommended_fix="Verify NVD_API_KEY in your environment or apply for an API key at nvd.nist.gov.",
                )
            elif response.status_code == 429:
                return ProviderHealth(
                    name=self.name,
                    status=ProviderStatus.UNAVAILABLE,
                    error_summary="NVD rate limit reached.",
                    recommended_fix="Reduce request frequency or set NVD_API_KEY for 50 req/30s rate limits.",
                )
            else:
                return ProviderHealth(
                    name=self.name,
                    status=ProviderStatus.FAILED,
                    error_summary=f"NVD API returned HTTP {response.status_code}",
                    recommended_fix="Check status.nist.gov or network connectivity to services.nvd.nist.gov.",
                )
        except Exception as exc:
            self.logger.warning("NVD health check error: %s", type(exc).__name__)
            return ProviderHealth(
                name=self.name,
                status=ProviderStatus.FAILED,
                error_summary=type(exc).__name__,
                recommended_fix="Verify network connectivity to services.nvd.nist.gov.",
            )

    def _normalize_cve_item(self, item: dict[str, Any]) -> NormalizedRecord:
        """Normalize an NVD CVE record into a NormalizedRecord."""
        cve = item.get("cve", {})
        cve_id = cve.get("id", "UNKNOWN")
        published_dt = _parse_nvd_timestamp(cve.get("published"))
        last_modified = cve.get("lastModified", "")
        vuln_status = cve.get("vulnStatus", "")
        observed_at = datetime.now(timezone.utc)

        # Extract English description
        descriptions = cve.get("descriptions", [])
        desc_text = ""
        for d in descriptions:
            if d.get("lang") == "en":
                desc_text = d.get("value", "")
                break
        if not desc_text and descriptions:
            desc_text = descriptions[0].get("value", "")

        # Extract CVSS metrics (v3.1, v3.0, or v2)
        metrics = cve.get("metrics", {})
        cvss_score: float | None = None
        cvss_severity: str = ""
        cvss_vector: str = ""

        v31 = metrics.get("cvssMetricV31", [])
        v30 = metrics.get("cvssMetricV30", [])
        v2 = metrics.get("cvssMetricV2", [])

        if v31:
            data = v31[0].get("cvssData", {})
            cvss_score = data.get("baseScore")
            cvss_severity = data.get("baseSeverity", "")
            cvss_vector = data.get("vectorString", "")
        elif v30:
            data = v30[0].get("cvssData", {})
            cvss_score = data.get("baseScore")
            cvss_severity = data.get("baseSeverity", "")
            cvss_vector = data.get("vectorString", "")
        elif v2:
            data = v2[0].get("cvssData", {})
            cvss_score = data.get("baseScore")
            cvss_severity = v2[0].get("baseSeverity", "")
            cvss_vector = data.get("vectorString", "")

        # Extract CWEs
        cwes: list[str] = []
        for w in cve.get("weaknesses", []):
            for d in w.get("description", []):
                val = d.get("value")
                if val and val != "NVD-CWE-noinfo":
                    cwes.append(val)

        # Extract References
        references = [r.get("url") for r in cve.get("references", []) if r.get("url")]

        fingerprint = f"{cve_id}:{last_modified}:{cvss_score}"
        content_hash = hashlib.sha256(fingerprint.encode()).hexdigest()

        score_label = f" (CVSS {cvss_score} {cvss_severity})" if cvss_score is not None else ""
        title = f"NVD: {cve_id}{score_label}"

        return NormalizedRecord(
            source="nvd",
            source_url=f"https://nvd.nist.gov/vuln/detail/{cve_id}",
            title=title[:120],
            summary=desc_text[:500] if desc_text else f"NVD record for {cve_id}",
            event_type="vulnerability",
            published_at=published_dt,
            observed_at=observed_at,
            content_hash=content_hash,
            evidence_reference=cve_id,
            metadata={
                "cve_id": cve_id,
                "vuln_status": vuln_status,
                "cvss_score": cvss_score,
                "cvss_severity": cvss_severity,
                "cvss_vector": cvss_vector,
                "cwes": cwes,
                "last_modified": last_modified,
                "references": references[:10],
            },
        )

    async def fetch(self, **kwargs: Any) -> list[NormalizedRecord]:
        """Fetch and normalize vulnerability records from NVD.

        Supported kwargs:
            cve_id (str): Specific CVE ID to fetch (e.g. "CVE-2021-44228")
            keyword_search (str): Keyword to search within vulnerability descriptions
            cpe_name (str): CPE 2.3 URI name to match
            results_per_page (int): Maximum records to retrieve (default: 10)
        """
        cve_id: str | None = kwargs.get("cve_id")
        keyword: str | None = kwargs.get("keyword_search") or kwargs.get("keyword")
        cpe_name: str | None = kwargs.get("cpe_name")
        results_per_page: int = min(int(kwargs.get("results_per_page", 10)), 50)

        # Check cache
        cache_k = self._cache_key(cve=cve_id or "", kw=keyword or "", cpe=cpe_name or "", limit=results_per_page)
        cached = self._get_cached(cache_k)
        if cached is not None:
            return cached

        params: dict[str, Any] = {"resultsPerPage": results_per_page}
        if cve_id:
            params["cveId"] = cve_id.strip().upper()
        if keyword:
            params["keywordSearch"] = keyword.strip()
        if cpe_name:
            params["cpeName"] = cpe_name.strip()

        headers = self._get_headers()
        records: list[NormalizedRecord] = []

        try:
            async with httpx.AsyncClient(timeout=25.0) as client:
                resp = await self._request_with_retry(
                    client, "GET", NVD_API_BASE, headers=headers, params=params, max_retries=3
                )

            if resp.status_code == 200:
                data = resp.json()
                vuln_items = data.get("vulnerabilities", [])
                for item in vuln_items:
                    records.append(self._normalize_cve_item(item))
                self._set_cached(cache_k, records)
            else:
                self.logger.warning("NVD API returned status %d for params %s", resp.status_code, params)
        except Exception as exc:
            self.logger.warning("NVD fetch failed: %s", type(exc).__name__)

        return records
