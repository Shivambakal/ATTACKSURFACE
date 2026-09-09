"""Provider Adapter and Licensing Registry.

Defines:
- ProviderAdapterMetadata: Machine-readable licensing, terms, rate limits, and capabilities
- ProviderCostTracker: Tracks API credits, request counts, response bytes, and estimated costs
- ProviderRegistry: Unified catalog of all external data connectors and enrichment adapters
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class ProviderMethod(str, Enum):
    REST = "REST"
    GRAPHQL = "GRAPHQL"
    BATCH = "BATCH"
    WEBHOOK = "WEBHOOK"
    STREAM = "STREAM"
    HOURLY_FILES = "HOURLY_FILES"
    JSON = "JSON"
    XML = "XML"


@dataclass
class ProviderAdapterMetadata:
    """Metadata detailing official provider capabilities, terms, and licensing boundaries."""
    provider_id: str
    name: str
    official_docs_url: str
    method: ProviderMethod
    auth_type: str  # API_KEY, OAUTH, PAT, NONE
    license_required: bool
    commercial_allowed: bool
    redistribution_allowed: bool
    storage_allowed: bool
    caching_allowed: bool
    rate_limit_per_min: int
    monthly_quota: int | None = None
    change_capable: bool = False
    historical_capable: bool = False
    batch_capable: bool = False
    realtime_capable: bool = False
    notes: str = ""


# Canonical Provider Table
PROVIDER_REGISTRY: dict[str, ProviderAdapterMetadata] = {
    "BUILTWITH": ProviderAdapterMetadata(
        provider_id="BUILTWITH",
        name="BuiltWith",
        official_docs_url="https://api.builtwith.com/change-api",
        method=ProviderMethod.REST,
        auth_type="API_KEY",
        license_required=True,
        commercial_allowed=True,
        redistribution_allowed=False,
        storage_allowed=True,
        caching_allowed=True,
        rate_limit_per_min=60,
        change_capable=True,
        historical_capable=True,
        batch_capable=True,
        notes="Dedicated Change API (/change1/api.json) for technology additions/removals.",
    ),
    "WAPPALYZER": ProviderAdapterMetadata(
        provider_id="WAPPALYZER",
        name="Wappalyzer",
        official_docs_url="https://www.wappalyzer.com/docs/api/v2/lookup/",
        method=ProviderMethod.REST,
        auth_type="API_KEY",
        license_required=True,
        commercial_allowed=True,
        redistribution_allowed=False,
        storage_allowed=True,
        caching_allowed=True,
        rate_limit_per_min=30,
        change_capable=True,
        historical_capable=True,
        batch_capable=True,
        notes="Supports up to 10 URLs per lookup, async callbacks, and monthly technology history.",
    ),
    "SIMILARWEB": ProviderAdapterMetadata(
        provider_id="SIMILARWEB",
        name="Similarweb",
        official_docs_url="https://docs.similarweb.com/api-v5",
        method=ProviderMethod.REST,
        auth_type="API_KEY",
        license_required=True,
        commercial_allowed=True,
        redistribution_allowed=False,
        storage_allowed=True,
        caching_allowed=True,
        rate_limit_per_min=60,
        historical_capable=True,
        batch_capable=True,
        notes="Technographics, website traffic trends, mobile apps; research context only.",
    ),
    "HG_INSIGHTS": ProviderAdapterMetadata(
        provider_id="HG_INSIGHTS",
        name="HG Insights",
        official_docs_url="https://data-docs.hginsights.com/v2",
        method=ProviderMethod.REST,
        auth_type="API_KEY",
        license_required=True,
        commercial_allowed=True,
        redistribution_allowed=False,
        storage_allowed=True,
        caching_allowed=True,
        rate_limit_per_min=60,
        batch_capable=True,
        notes="Firmographics and technographics; IT spend is not proof of live deployment.",
    ),
    "CENSYS": ProviderAdapterMetadata(
        provider_id="CENSYS",
        name="Censys Platform",
        official_docs_url="https://docs.censys.com/reference/get-started",
        method=ProviderMethod.REST,
        auth_type="PAT",
        license_required=True,
        commercial_allowed=True,
        redistribution_allowed=False,
        storage_allowed=True,
        caching_allowed=True,
        rate_limit_per_min=120,
        historical_capable=True,
        notes="Internet infrastructure observation; attribution must be verified before declaring scope.",
    ),
    "SHODAN": ProviderAdapterMetadata(
        provider_id="SHODAN",
        name="Shodan",
        official_docs_url="https://developer.shodan.io/api",
        method=ProviderMethod.REST,
        auth_type="API_KEY",
        license_required=True,
        commercial_allowed=True,
        redistribution_allowed=False,
        storage_allowed=True,
        caching_allowed=True,
        rate_limit_per_min=60,
        historical_capable=True,
        notes="Host intelligence, port, TLS observations; respects account plan boundaries.",
    ),
    "CHAOS": ProviderAdapterMetadata(
        provider_id="CHAOS",
        name="ProjectDiscovery Chaos",
        official_docs_url="https://docs.projectdiscovery.io/opensource/chaos/overview",
        method=ProviderMethod.REST,
        auth_type="API_KEY",
        license_required=True,
        commercial_allowed=True,
        redistribution_allowed=False,
        storage_allowed=True,
        caching_allowed=True,
        rate_limit_per_min=60,
        notes="Passive DNS and subdomain discovery dataset.",
    ),
    "CERTIFICATE_TRANSPARENCY": ProviderAdapterMetadata(
        provider_id="CERTIFICATE_TRANSPARENCY",
        name="Public Certificate Transparency",
        official_docs_url="https://crt.sh",
        method=ProviderMethod.REST,
        auth_type="NONE",
        license_required=False,
        commercial_allowed=True,
        redistribution_allowed=True,
        storage_allowed=True,
        caching_allowed=True,
        rate_limit_per_min=30,
        change_capable=True,
        notes="Public CT logs for detecting new TLS certificates and hostnames.",
    ),
    "SECURITYTRAILS": ProviderAdapterMetadata(
        provider_id="SECURITYTRAILS",
        name="SecurityTrails",
        official_docs_url="https://docs.securitytrails.com/",
        method=ProviderMethod.REST,
        auth_type="API_KEY",
        license_required=True,
        commercial_allowed=True,
        redistribution_allowed=False,
        storage_allowed=True,
        caching_allowed=True,
        rate_limit_per_min=60,
        historical_capable=True,
        notes="Historical DNS (A, AAAA, MX, NS, TXT) observation.",
    ),
    "GITHUB": ProviderAdapterMetadata(
        provider_id="GITHUB",
        name="GitHub REST API",
        official_docs_url="https://docs.github.com/en/rest",
        method=ProviderMethod.REST,
        auth_type="PAT",
        license_required=False,
        commercial_allowed=True,
        redistribution_allowed=False,
        storage_allowed=True,
        caching_allowed=True,
        rate_limit_per_min=80,
        change_capable=True,
        notes="Organization events, releases, commits, tags, and security advisories.",
    ),
    "GH_ARCHIVE": ProviderAdapterMetadata(
        provider_id="GH_ARCHIVE",
        name="GH Archive",
        official_docs_url="https://www.gharchive.org/",
        method=ProviderMethod.HOURLY_FILES,
        auth_type="NONE",
        license_required=False,
        commercial_allowed=True,
        redistribution_allowed=True,
        storage_allowed=True,
        caching_allowed=True,
        rate_limit_per_min=10,
        historical_capable=True,
        notes="Hourly public GitHub event archives for non-realtime historical analysis.",
    ),
    "DEPS_DEV": ProviderAdapterMetadata(
        provider_id="DEPS_DEV",
        name="deps.dev (Open Source Insights)",
        official_docs_url="https://docs.deps.dev/api/",
        method=ProviderMethod.REST,
        auth_type="NONE",
        license_required=False,
        commercial_allowed=True,
        redistribution_allowed=True,
        storage_allowed=True,
        caching_allowed=True,
        rate_limit_per_min=60,
        notes="Package versions, dependencies, and advisory intelligence.",
    ),
    "OSV": ProviderAdapterMetadata(
        provider_id="OSV",
        name="OSV (Open Source Vulnerabilities)",
        official_docs_url="https://google.github.io/osv.dev/api/",
        method=ProviderMethod.REST,
        auth_type="NONE",
        license_required=False,
        commercial_allowed=True,
        redistribution_allowed=True,
        storage_allowed=True,
        caching_allowed=True,
        rate_limit_per_min=120,
        batch_capable=True,
        notes="Ecosystem package vulnerability database.",
    ),
    "CISA_KEV": ProviderAdapterMetadata(
        provider_id="CISA_KEV",
        name="CISA Known Exploited Vulnerabilities",
        official_docs_url="https://www.cisa.gov/known-exploited-vulnerabilities-catalog",
        method=ProviderMethod.JSON,
        auth_type="NONE",
        license_required=False,
        commercial_allowed=True,
        redistribution_allowed=True,
        storage_allowed=True,
        caching_allowed=True,
        rate_limit_per_min=10,
        notes="Preserves 1,694+ validated entries with SHA-256 integrity.",
    ),
    "NVD": ProviderAdapterMetadata(
        provider_id="NVD",
        name="National Vulnerability Database",
        official_docs_url="https://services.nvd.nist.gov/rest/json/cves/2.0",
        method=ProviderMethod.REST,
        auth_type="API_KEY",
        license_required=False,
        commercial_allowed=True,
        redistribution_allowed=True,
        storage_allowed=True,
        caching_allowed=True,
        rate_limit_per_min=50,
        notes="NVD API 2.0 with incremental date windows.",
    ),
    "PREDICTLEADS": ProviderAdapterMetadata(
        provider_id="PREDICTLEADS",
        name="PredictLeads",
        official_docs_url="https://docs.predictleads.com/",
        method=ProviderMethod.REST,
        auth_type="API_KEY",
        license_required=True,
        commercial_allowed=True,
        redistribution_allowed=False,
        storage_allowed=True,
        caching_allowed=True,
        rate_limit_per_min=60,
        notes="Job/hiring signals used strictly as low-confidence contextual indicators.",
    ),
    "EPO_OPS": ProviderAdapterMetadata(
        provider_id="EPO_OPS",
        name="EPO Open Patent Services",
        official_docs_url="https://developers.epo.org/",
        method=ProviderMethod.XML,
        auth_type="OAUTH",
        license_required=True,
        commercial_allowed=True,
        redistribution_allowed=False,
        storage_allowed=True,
        caching_allowed=True,
        rate_limit_per_min=30,
        historical_capable=True,
        notes="Patent filings represent R&D indicators, not production deployment.",
    ),
    "PRODUCT_HUNT": ProviderAdapterMetadata(
        provider_id="PRODUCT_HUNT",
        name="Product Hunt",
        official_docs_url="https://api.producthunt.com/v2/docs",
        method=ProviderMethod.GRAPHQL,
        auth_type="OAUTH",
        license_required=True,
        commercial_allowed=False,
        redistribution_allowed=False,
        storage_allowed=False,
        caching_allowed=True,
        rate_limit_per_min=30,
        notes="Commercial use restricted by provider terms; discovery context only.",
    ),
    "G2": ProviderAdapterMetadata(
        provider_id="G2",
        name="G2 Official API",
        official_docs_url="https://documentation.g2.com/docs/g2-api",
        method=ProviderMethod.REST,
        auth_type="API_KEY",
        license_required=True,
        commercial_allowed=True,
        redistribution_allowed=False,
        storage_allowed=True,
        caching_allowed=True,
        rate_limit_per_min=60,
        notes="Product categories and market review intelligence.",
    ),
    "DOMAINEE": ProviderAdapterMetadata(
        provider_id="DOMAINEE",
        name="Domainee.dev",
        official_docs_url="https://domainee.dev",
        method=ProviderMethod.REST,
        auth_type="API_KEY",
        license_required=True,
        commercial_allowed=True,
        redistribution_allowed=False,
        storage_allowed=True,
        caching_allowed=True,
        rate_limit_per_min=60,
        notes="Custom domains, routing, and DNS configuration intelligence.",
    ),
    "SUBDOMAINS_FINDER": ProviderAdapterMetadata(
        provider_id="SUBDOMAINS_FINDER",
        name="Subdomains Finder",
        official_docs_url="https://apify.com/dev00/subdomains-finder-api-realtime-dns-subdomain-scanner",
        method=ProviderMethod.REST,
        auth_type="API_KEY",
        license_required=True,
        commercial_allowed=False,
        redistribution_allowed=False,
        storage_allowed=True,
        caching_allowed=True,
        rate_limit_per_min=30,
        notes="Status: UNVERIFIED until official live documentation confirmed.",
    ),
}


class ProviderCostTracker:
    """In-memory and persistent cost accumulator for external provider calls."""

    _usage: dict[str, dict[str, Any]] = {}

    @classmethod
    def record_call(
        cls,
        provider_id: str,
        credits: float = 0.0,
        bytes_count: int = 0,
        estimated_cost: float = 0.0,
        success: bool = True,
    ) -> None:
        stats = cls._usage.setdefault(provider_id, {
            "requests": 0,
            "credits": 0.0,
            "bytes": 0,
            "errors": 0,
            "estimated_cost": 0.0,
        })
        stats["requests"] += 1
        stats["credits"] += credits
        stats["bytes"] += bytes_count
        stats["estimated_cost"] += estimated_cost
        if not success:
            stats["errors"] += 1

    @classmethod
    def get_summary(cls) -> dict[str, Any]:
        return dict(cls._usage)
