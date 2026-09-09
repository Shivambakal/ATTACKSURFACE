"""OSV (Open Source Vulnerabilities) data provider.

Queries the free OSV API (https://api.osv.dev/v1/query) for package vulnerabilities
across supported ecosystems: npm, PyPI, Maven, Go, Rust (crates.io), NuGet, etc.
Requires no API credentials.
Caches query responses to avoid redundant lookups and respect community infrastructure.
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

ECOSYSTEM_MAP = {
    "npm": "npm",
    "pypi": "PyPI",
    "python": "PyPI",
    "pip": "PyPI",
    "maven": "Maven",
    "java": "Maven",
    "go": "Go",
    "golang": "Go",
    "rust": "crates.io",
    "cargo": "crates.io",
    "crates.io": "crates.io",
    "nuget": "NuGet",
    "dotnet": "NuGet",
    "packagist": "Packagist",
    "php": "Packagist",
    "rubygems": "RubyGems",
    "ruby": "RubyGems",
}


def _parse_timestamp(val: str | None) -> datetime | None:
    if not val:
        return None
    try:
        dt = datetime.fromisoformat(val.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except (ValueError, TypeError):
        return None


class OSVProvider(BaseProvider):
    """Provider for querying Open Source Vulnerabilities (OSV.dev)."""

    API_BASE = "https://api.osv.dev/v1"

    def __init__(self, rate_limiter: RateLimiter | None = None):
        super().__init__(name="osv", rate_limiter=rate_limiter or RateLimiter(max_requests=60, window_seconds=60.0))
        self._cache_ttl = 1800.0  # 30 minutes cache for vulnerability queries

    def is_configured(self) -> bool:
        """OSV is a public, unauthenticated service; always configured."""
        return True

    async def check_health(self) -> ProviderHealth:
        """Verify connectivity to OSV API with a dummy query."""
        url = f"{self.API_BASE}/query"
        headers = {
            "User-Agent": settings.collector_user_agent,
            "Content-Type": "application/json",
        }
        body = {"package": {"name": "nonexistent-healthcheck-pkg-12345", "ecosystem": "npm"}}

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(url, headers=headers, json=body)

            if response.status_code == 200:
                return ProviderHealth(
                    name=self.name,
                    status=ProviderStatus.AVAILABLE,
                    error_summary=None,
                    recommended_fix=None,
                )
            return ProviderHealth(
                name=self.name,
                status=ProviderStatus.FAILED,
                error_summary=f"OSV API returned HTTP {response.status_code}",
                recommended_fix="Check api.osv.dev status and outbound network access.",
            )
        except Exception as exc:
            self.logger.warning("OSV health check failed: %s", type(exc).__name__)
            return ProviderHealth(
                name=self.name,
                status=ProviderStatus.FAILED,
                error_summary=type(exc).__name__,
                recommended_fix="Verify network connectivity to api.osv.dev.",
            )

    async def _query_single_package(
        self, client: httpx.AsyncClient, package: str, ecosystem: str | None = None, version: str | None = None
    ) -> list[dict[str, Any]]:
        """Query OSV for a single package with caching."""
        eco = ECOSYSTEM_MAP.get(ecosystem.lower(), ecosystem) if ecosystem else None
        cache_k = self._cache_key(pkg=package, eco=eco or "", ver=version or "")
        cached = self._get_cached(cache_k)
        if cached is not None:
            return cached

        req_body: dict[str, Any] = {"package": {"name": package}}
        if eco:
            req_body["package"]["ecosystem"] = eco
        if version:
            req_body["version"] = version

        headers = {
            "User-Agent": settings.collector_user_agent,
            "Content-Type": "application/json",
        }
        url = f"{self.API_BASE}/query"

        try:
            resp = await self._request_with_retry(
                client, "POST", url, headers=headers, json_body=req_body, max_retries=3
            )
            if resp.status_code == 200:
                data = resp.json()
                vulns = data.get("vulns", [])
                self._set_cached(cache_k, vulns)
                return vulns
            self.logger.debug("OSV query status %s for package %s", resp.status_code, package)
            return []
        except Exception as exc:
            self.logger.warning("OSV query failed for %s: %s", package, type(exc).__name__)
            return []

    async def _get_vuln_by_id(self, client: httpx.AsyncClient, vuln_id: str) -> dict[str, Any] | None:
        """Fetch full vulnerability record by ID with caching."""
        cache_k = self._cache_key(vuln_id=vuln_id)
        cached = self._get_cached(cache_k)
        if cached is not None:
            return cached

        url = f"{self.API_BASE}/vulns/{vuln_id}"
        headers = {"User-Agent": settings.collector_user_agent}

        try:
            resp = await self._request_with_retry(client, "GET", url, headers=headers, max_retries=3)
            if resp.status_code == 200:
                data = resp.json()
                self._set_cached(cache_k, data)
                return data
            return None
        except Exception as exc:
            self.logger.warning("OSV vuln lookup failed for %s: %s", vuln_id, type(exc).__name__)
            return None

    def _normalize_vuln(
        self,
        vuln: dict[str, Any],
        package_hint: str = "",
        ecosystem_hint: str = "",
        version_hint: str = "",
    ) -> NormalizedRecord:
        """Normalize an OSV vulnerability dictionary into a NormalizedRecord."""
        vuln_id = vuln.get("id", "UNKNOWN")
        summary = vuln.get("summary") or ""
        details = vuln.get("details") or ""
        aliases = vuln.get("aliases", [])
        cve_alias = next((a for a in aliases if a.startswith("CVE-")), None)
        primary_id = cve_alias or vuln_id

        published = _parse_timestamp(vuln.get("published"))
        modified = vuln.get("modified") or ""
        retrieved_at = datetime.now(timezone.utc)

        # Extract severity metrics if present
        severity_list = vuln.get("severity", [])
        severity_score = ""
        for sev in severity_list:
            score = sev.get("score")
            if score:
                severity_score = str(score)
                break

        # Extract references
        raw_refs = vuln.get("references", [])
        references = [r.get("url") for r in raw_refs if isinstance(r, dict) and r.get("url")]

        # Determine package and ecosystem from affected array if not provided
        affected_list = vuln.get("affected", [])
        eco = ecosystem_hint
        pkg = package_hint
        if affected_list and (not eco or not pkg):
            aff_pkg = affected_list[0].get("package", {})
            eco = eco or aff_pkg.get("ecosystem", "")
            pkg = pkg or aff_pkg.get("name", "")

        raw_fingerprint = f"{vuln_id}:{modified}:{pkg}:{eco}"
        content_hash = hashlib.sha256(raw_fingerprint.encode()).hexdigest()

        title_desc = summary or (details.split("\n")[0] if details else f"Vulnerability in {pkg or 'dependency'}")
        title = f"OSV: [{primary_id}] {title_desc[:70]}"
        full_summary = summary or (details[:500] if details else f"Vulnerability {vuln_id} affecting {pkg}")

        return NormalizedRecord(
            source="osv",
            source_url=f"https://osv.dev/vulnerability/{vuln_id}",
            title=title,
            summary=full_summary,
            event_type="vulnerability",
            published_at=published,
            observed_at=retrieved_at,
            content_hash=content_hash,
            evidence_reference=primary_id,
            metadata={
                "vuln_id": vuln_id,
                "cve_alias": cve_alias,
                "aliases": aliases,
                "ecosystem": eco,
                "package": pkg,
                "version": version_hint,
                "severity": severity_score,
                "summary": summary,
                "published": vuln.get("published"),
                "modified": modified,
                "references": references,
                "retrieved_at": retrieved_at.isoformat(),
            },
        )

    async def fetch(self, **kwargs: Any) -> list[NormalizedRecord]:
        """Fetch and normalize vulnerability records from OSV.

        Supported kwargs:
            package (str): Single package name
            ecosystem (str): Ecosystem (npm, PyPI, Maven, Go, crates.io, NuGet)
            version (str): Package version
            packages (list[dict]): List of dicts with 'name', 'ecosystem', and optional 'version'
            vuln_id (str): Direct vulnerability lookup by OSV or CVE ID
        """
        records: list[NormalizedRecord] = []
        observed_ids: set[str] = set()

        async with httpx.AsyncClient(timeout=15.0) as client:
            # 1. Direct vulnerability lookup
            vuln_id = kwargs.get("vuln_id") or kwargs.get("cve_id")
            if vuln_id:
                vuln_data = await self._get_vuln_by_id(client, str(vuln_id))
                if vuln_data:
                    rec = self._normalize_vuln(vuln_data)
                    records.append(rec)
                    observed_ids.add(rec.evidence_reference)

            # 2. Single package query
            package = kwargs.get("package")
            if package:
                ecosystem = kwargs.get("ecosystem")
                version = kwargs.get("version")
                vulns = await self._query_single_package(
                    client, str(package), str(ecosystem) if ecosystem else None, str(version) if version else None
                )
                for v in vulns:
                    v_id = v.get("id", "")
                    if v_id and v_id not in observed_ids:
                        rec = self._normalize_vuln(
                            v,
                            package_hint=str(package),
                            ecosystem_hint=str(ecosystem) if ecosystem else "",
                            version_hint=str(version) if version else "",
                        )
                        records.append(rec)
                        observed_ids.add(v_id)

            # 3. Batch packages query
            packages_list = kwargs.get("packages")
            if packages_list and isinstance(packages_list, list):
                for p_info in packages_list:
                    p_name = p_info.get("name")
                    if not p_name:
                        continue
                    p_eco = p_info.get("ecosystem")
                    p_ver = p_info.get("version")
                    vulns = await self._query_single_package(
                        client, str(p_name), str(p_eco) if p_eco else None, str(p_ver) if p_ver else None
                    )
                    for v in vulns:
                        v_id = v.get("id", "")
                        if v_id and v_id not in observed_ids:
                            rec = self._normalize_vuln(
                                v,
                                package_hint=str(p_name),
                                ecosystem_hint=str(p_eco) if p_eco else "",
                                version_hint=str(p_ver) if p_ver else "",
                            )
                            records.append(rec)
                            observed_ids.add(v_id)

        return records
