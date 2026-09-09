"""CISA Known Exploited Vulnerabilities (KEV) catalog data provider.

Fetches the official CISA KEV JSON catalog:
https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json
Provides contextual threat intelligence on vulnerabilities actively exploited in the wild.
Requires no credentials. Caches the full catalog in memory to minimize network overhead.
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

CISA_KEV_URL = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"


def _parse_cisa_date(val: str | None) -> datetime | None:
    if not val:
        return None
    try:
        dt = datetime.strptime(val.strip(), "%Y-%m-%d")
        return dt.replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return None


class CISAKEVProvider(BaseProvider):
    """Provider for CISA Known Exploited Vulnerabilities (KEV) contextual intelligence."""

    def __init__(self, rate_limiter: RateLimiter | None = None):
        super().__init__(name="cisa_kev", rate_limiter=rate_limiter or RateLimiter(max_requests=10, window_seconds=60.0))
        self._catalog_cache: list[dict[str, Any]] = []
        self._catalog_etag: str | None = None
        self._catalog_last_fetched: float = 0.0
        self._catalog_ttl: float = 3600.0  # 1 hour cache

    def is_configured(self) -> bool:
        """CISA KEV is a public government feed; always configured."""
        return True

    async def _load_catalog(self, client: httpx.AsyncClient) -> list[dict[str, Any]]:
        """Load and cache the full CISA KEV catalog."""
        now = datetime.now(timezone.utc).timestamp()
        if self._catalog_cache and (now - self._catalog_last_fetched < self._catalog_ttl):
            return self._catalog_cache

        headers = {
            "User-Agent": settings.collector_user_agent,
            "Accept": "application/json",
        }
        if self._catalog_etag:
            headers["If-None-Match"] = self._catalog_etag

        try:
            resp = await self._request_with_retry(client, "GET", CISA_KEV_URL, headers=headers, max_retries=3)
            if resp.status_code == 304 and self._catalog_cache:
                self._catalog_last_fetched = now
                return self._catalog_cache

            if resp.status_code == 200:
                data = resp.json()
                vulns = data.get("vulnerabilities", [])
                self._catalog_cache = vulns
                self._catalog_etag = resp.headers.get("etag")
                self._catalog_last_fetched = now
                self.logger.info("Loaded %d CISA KEV vulnerabilities into cache", len(vulns))
                return self._catalog_cache

            self.logger.warning("Unexpected status %d fetching CISA KEV catalog", resp.status_code)
            return self._catalog_cache
        except Exception as exc:
            self.logger.warning("Failed to download CISA KEV catalog: %s", type(exc).__name__)
            return self._catalog_cache

    async def check_health(self) -> ProviderHealth:
        """Verify availability of the CISA KEV catalog."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                catalog = await self._load_catalog(client)

            if catalog:
                return ProviderHealth(
                    name=self.name,
                    status=ProviderStatus.AVAILABLE,
                    error_summary=None,
                    recommended_fix=None,
                )
            return ProviderHealth(
                name=self.name,
                status=ProviderStatus.FAILED,
                error_summary="Failed to fetch CISA KEV catalog or catalog is empty.",
                recommended_fix="Check network connectivity to cisa.gov feeds.",
            )
        except Exception as exc:
            self.logger.warning("CISA KEV health check error: %s", type(exc).__name__)
            return ProviderHealth(
                name=self.name,
                status=ProviderStatus.FAILED,
                error_summary=type(exc).__name__,
                recommended_fix="Verify network connectivity to www.cisa.gov.",
            )

    def _normalize_item(self, item: dict[str, Any]) -> NormalizedRecord:
        """Normalize a single CISA KEV vulnerability dictionary."""
        cve_id = item.get("cveID", "UNKNOWN")
        vendor = item.get("vendorProject", "Unknown Vendor")
        product = item.get("product", "Unknown Product")
        vuln_name = item.get("vulnerabilityName", "")
        date_added = item.get("dateAdded", "")
        due_date = item.get("dueDate", "")
        ransomware_use = item.get("knownRansomwareCampaignUse", "Unknown")
        notes = item.get("notes", "")
        short_desc = item.get("shortDescription", "")
        required_action = item.get("requiredAction", "")

        pub_dt = _parse_cisa_date(date_added)
        observed_at = datetime.now(timezone.utc)

        fingerprint = f"{cve_id}:{date_added}:{vendor}:{product}"
        content_hash = hashlib.sha256(fingerprint.encode()).hexdigest()

        source_url = notes if notes.startswith("http") else "https://www.cisa.gov/known-exploited-vulnerabilities-catalog"

        title = f"CISA KEV: {cve_id} - {vendor} {product} ({vuln_name or 'Exploited Vulnerability'})"
        summary = (
            f"{short_desc} "
            f"[Action: {required_action or 'Patch per vendor'}] "
            f"[Ransomware: {ransomware_use}]"
        ).strip()

        return NormalizedRecord(
            source="cisa_kev",
            source_url=source_url,
            title=title[:120],
            summary=summary[:600],
            event_type="known_exploited_vulnerability",
            published_at=pub_dt,
            observed_at=observed_at,
            content_hash=content_hash,
            evidence_reference=cve_id,
            metadata={
                "cve_id": cve_id,
                "vendor": vendor,
                "product": product,
                "vulnerability_name": vuln_name,
                "date_added": date_added,
                "due_date": due_date,
                "ransomware_use": ransomware_use,
                "required_action": required_action,
                "notes": notes,
            },
        )

    async def fetch(self, **kwargs: Any) -> list[NormalizedRecord]:
        """Query CISA KEV catalog for matching vulnerabilities.

        Supported kwargs:
            cve_id (str): Single CVE ID (e.g. "CVE-2023-38606")
            cves (list[str]): Multiple CVE IDs to filter by
            vendor (str): Case-insensitive vendor search string
            product (str): Case-insensitive product search string
            target (str): Target domain or keyword to check against vendor/product
            limit (int): Max records to return (default: 50)
        """
        async with httpx.AsyncClient(timeout=15.0) as client:
            catalog = await self._load_catalog(client)

        if not catalog:
            return []

        cve_id: str | None = kwargs.get("cve_id")
        cves: list[str] | None = kwargs.get("cves")
        vendor: str | None = kwargs.get("vendor")
        product: str | None = kwargs.get("product")
        target: str | None = kwargs.get("target")
        limit: int = int(kwargs.get("limit", 50))

        target_cves: set[str] = set()
        if cve_id:
            target_cves.add(cve_id.strip().upper())
        if cves:
            target_cves.update(c.strip().upper() for c in cves if c)

        vendor_lower = vendor.lower().strip() if vendor else None
        product_lower = product.lower().strip() if product else None
        target_lower = target.lower().strip() if target else None

        records: list[NormalizedRecord] = []

        for item in catalog:
            item_cve = item.get("cveID", "").upper()
            item_vendor = item.get("vendorProject", "").lower()
            item_product = item.get("product", "").lower()

            match = False
            if target_cves:
                match = item_cve in target_cves
            elif vendor_lower or product_lower:
                vendor_match = not vendor_lower or vendor_lower in item_vendor
                product_match = not product_lower or product_lower in item_product
                match = vendor_match and product_match
            elif target_lower:
                # Domain/keyword matching
                base_target = target_lower.split(".")[0]
                if len(base_target) > 3 and (base_target in item_vendor or base_target in item_product):
                    match = True
            else:
                # No filters provided: return recent additions up to limit
                match = True

            if match:
                records.append(self._normalize_item(item))
                if len(records) >= limit:
                    break

        return records
