"""Entity Resolution & Alias Disambiguation Service.

Provides conservative entity resolution across Company, Product, Technology,
Asset, Repository, and Vulnerability.

Guarantees:
- Canonical identity with explicit alias registries.
- Never automatically merges ambiguous entities without high-confidence corroborating evidence.
- Full provenance for every resolution decision.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class EntityType(str, Enum):
    COMPANY = "COMPANY"
    PRODUCT = "PRODUCT"
    TECHNOLOGY = "TECHNOLOGY"
    ASSET = "ASSET"
    REPOSITORY = "REPOSITORY"
    VULNERABILITY = "VULNERABILITY"


@dataclass
class ResolvedEntity:
    """The authoritative result of an entity resolution lookup."""
    canonical_name: str
    entity_type: EntityType
    aliases: list[str] = field(default_factory=list)
    resolution_confidence: float = 1.0
    is_ambiguous: bool = False
    evidence_reference: str = ""
    attributes: dict[str, Any] = field(default_factory=dict)


# Known canonical technology mappings with common alias variations
TECHNOLOGY_ALIASES: dict[str, list[str]] = {
    "starlette": ["kludex starlette", "starlette framework", "starlette-framework", "starlette asgi"],
    "fastapi": ["fastapi framework", "tiangolo fastapi", "fast-api"],
    "react": ["react.js", "reactjs", "react framework", "facebook react", "meta react"],
    "next.js": ["nextjs", "next.js framework", "vercel next.js", "next 13", "next 14", "next 15"],
    "nginx": ["nginx web server", "f5 nginx", "engine-x", "nginx/"],
    "apache http server": ["apache httpd", "httpd", "apache2", "apache/2"],
    "apache log4j": ["log4j", "log4j2", "log4j-core", "apache-log4j"],
    "vue.js": ["vuejs", "vue 2", "vue 3", "vue framework"],
    "spring boot": ["spring-boot", "spring framework", "vmware spring", "spring cloud"],
    "postgresql": ["postgres", "pgsql", "postgres-db", "postgresql server"],
    "redis": ["redis-server", "redis cache", "redis key-value store"],
    "docker": ["docker container", "docker engine", "docker runtime"],
    "kubernetes": ["k8s", "kubernetes cluster", "k8s-engine"],
}

# Known vendor / company distinctions to prevent false correlation
VENDOR_DISAMBIGUATION: dict[str, str] = {
    "microsoft": "microsoft",
    "apache": "apache software foundation",
    "oracle": "oracle corporation",
    "vmware": "vmware / broadcom",
    "google": "google llc",
    "apple": "apple inc",
    "cisco": "cisco systems",
}


class EntityResolutionService:
    """Resolves raw names to canonical entities with strict ambiguity detection."""

    @classmethod
    def normalize_string(cls, raw: str) -> str:
        """Strips whitespace, lowercases, and collapses redundant separators."""
        if not raw:
            return ""
        s = raw.strip().lower()
        s = re.sub(r"[\t\r\n]+", " ", s)
        s = re.sub(r"\s{2,}", " ", s)
        return s

    @classmethod
    def resolve_technology(cls, raw_name: str, context: Optional[str] = None) -> ResolvedEntity:
        """Resolves a raw technology name to its canonical identifier.

        Does NOT merge ambiguous names without corroboration.
        """
        norm = cls.normalize_string(raw_name)
        if not norm:
            return ResolvedEntity(
                canonical_name="",
                entity_type=EntityType.TECHNOLOGY,
                resolution_confidence=0.0,
                is_ambiguous=True,
                evidence_reference="Empty input",
            )

        # Check exact canonical matches
        if norm in TECHNOLOGY_ALIASES:
            return ResolvedEntity(
                canonical_name=norm,
                entity_type=EntityType.TECHNOLOGY,
                aliases=TECHNOLOGY_ALIASES[norm],
                resolution_confidence=1.0,
                evidence_reference=f"Exact match on canonical key '{norm}'",
            )

        # Check known alias registries
        for canonical, aliases in TECHNOLOGY_ALIASES.items():
            if norm in aliases or any(alias in norm for alias in aliases):
                return ResolvedEntity(
                    canonical_name=canonical,
                    entity_type=EntityType.TECHNOLOGY,
                    aliases=aliases,
                    resolution_confidence=0.95,
                    evidence_reference=f"Matched registered alias of canonical '{canonical}'",
                )

        # Generic words that are highly ambiguous (e.g. "server", "web", "api", "cloud")
        AMBIGUOUS_TERMS = {"server", "web", "api", "cloud", "core", "auth", "service", "gateway", "proxy"}
        if norm in AMBIGUOUS_TERMS:
            return ResolvedEntity(
                canonical_name=norm,
                entity_type=EntityType.TECHNOLOGY,
                resolution_confidence=0.3,
                is_ambiguous=True,
                evidence_reference=f"Term '{norm}' is generic and cannot be automatically resolved",
            )

        # Unregistered technology: preserve as-is with lower confidence
        return ResolvedEntity(
            canonical_name=norm,
            entity_type=EntityType.TECHNOLOGY,
            aliases=[norm],
            resolution_confidence=0.75,
            is_ambiguous=False,
            evidence_reference=f"Unregistered technology preserved canonically as '{norm}'",
        )

    @classmethod
    def resolve_vulnerability_canonical_id(
        cls, cve_id: Optional[str] = None, ghsa_id: Optional[str] = None, nvd_id: Optional[str] = None
    ) -> ResolvedEntity:
        """Produces a unified canonical vulnerability identity across multiple sources.

        Dominant priority: CVE-YYYY-NNNN+ > GHSA > NVD.
        """
        aliases = []
        if cve_id:
            cve_clean = cve_id.strip().upper()
            if ghsa_id:
                aliases.append(ghsa_id.strip())
            if nvd_id and nvd_id != cve_clean:
                aliases.append(nvd_id.strip())
            return ResolvedEntity(
                canonical_name=cve_clean,
                entity_type=EntityType.VULNERABILITY,
                aliases=aliases,
                resolution_confidence=1.0,
                evidence_reference="Standardized CVE authoritative identity",
            )

        if ghsa_id:
            ghsa_clean = ghsa_id.strip().upper()
            return ResolvedEntity(
                canonical_name=ghsa_clean,
                entity_type=EntityType.VULNERABILITY,
                aliases=aliases,
                resolution_confidence=0.95,
                evidence_reference="GitHub Advisory authoritative identity",
            )

        return ResolvedEntity(
            canonical_name="UNKNOWN_VULNERABILITY",
            entity_type=EntityType.VULNERABILITY,
            resolution_confidence=0.1,
            is_ambiguous=True,
            evidence_reference="No valid identifier provided",
        )

    @classmethod
    def assert_vendor_is_not_company(
        cls, vendor_project: str, company_name: str, company_domain: str
    ) -> tuple[bool, str]:
        """Enforces Vendor != Company boundary.

        Returns (is_direct_match, rationale).
        """
        norm_vendor = cls.normalize_string(vendor_project)
        norm_company = cls.normalize_string(company_name)
        norm_domain = cls.normalize_string(company_domain)

        # Direct domain-level match
        if norm_vendor and (norm_vendor in norm_domain or norm_domain in norm_vendor):
            return True, f"Vendor '{vendor_project}' correlates directly with target domain '{company_domain}'"

        # Explicit name match
        if norm_vendor and norm_company and (norm_vendor == norm_company):
            return True, f"Vendor '{vendor_project}' exactly matches target company name '{company_name}'"

        return False, (
            f"Vendor/Project '{vendor_project}' is distinct from company '{company_name}'. "
            "Any advisories for this vendor represent third-party technology context, NOT confirmed target vulnerabilities."
        )


# Canonical alias for compatibility
EntityResolver = EntityResolutionService

