"""Deterministic Entity Resolution Service for CISA KEV Vulnerabilities.

Enforces the non-negotiable rule:
    CISA KEV membership DOES NOT automatically mean a company is vulnerable.

Maps CISA (vendorProject, product, cveID) to canonical Company and Product records
using strict multi-factor deterministic logic and explicit relationship categories.

Allowed relationship states:
- DIRECT_VENDOR_MATCH (Confirmed)
- DIRECT_PRODUCT_MATCH (Confirmed)
- OFFICIAL_VENDOR_RELATIONSHIP (Confirmed)
- EXPLICIT_COMPANY_PRODUCT_RELATIONSHIP (Confirmed)
- POSSIBLE_MATCH (Unconfirmed — NEVER creates company vulnerability)
- UNVERIFIED (Unconfirmed — NEVER creates company vulnerability)
- NO_RELATIONSHIP (Unconfirmed)
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models.company import Company
from ..models.product import Product
from ..models.security import SecurityEvent
from ..models.cisa_kev import CISAKEVItem

logger = logging.getLogger(__name__)

# Known high-confidence vendor aliases mapping CISA vendor strings to canonical names/domains
KNOWN_VENDOR_ALIASES: dict[str, str] = {
    "google": "google.com",
    "google chrome": "google.com",
    "chromium": "google.com",
    "android": "google.com",
    "amd": "amd.com",
    "advanced micro devices": "amd.com",
    "microsoft": "microsoft.com",
    "apple": "apple.com",
    "adobe": "adobe.com",
    "cisco": "cisco.com",
    "oracle": "oracle.com",
    "amazon": "amazon.com",
    "aws": "amazon.com",
    "meta": "meta.com",
    "facebook": "meta.com",
    "cloudflare": "cloudflare.com",
    "fastly": "fastly.com",
    "atlassian": "atlassian.com",
    "gitlab": "gitlab.com",
    "github": "github.com",
    "zoom": "zoom.us",
    "salesforce": "salesforce.com",
    "ibm": "ibm.com",
    "red hat": "redhat.com",
    "vmware": "vmware.com",
    "splunk": "splunk.com",
    "servicenow": "servicenow.com",
    "palo alto networks": "paloaltonetworks.com",
    "fortinet": "fortinet.com",
    "f5": "f5.com",
    "juniper": "juniper.net",
    "sophos": "sophos.com",
    "checkpoint": "checkpoint.com",
    "sonicwall": "sonicwall.com",
    "trend micro": "trendmicro.com",
    "symantec": "broadcom.com",
    "broadcom": "broadcom.com",
    "qualcomm": "qualcomm.com",
    "intel": "intel.com",
    "nvidia": "nvidia.com",
}

CONFIRMED_RELATIONSHIPS = {
    "DIRECT_VENDOR_MATCH",
    "DIRECT_PRODUCT_MATCH",
    "OFFICIAL_VENDOR_RELATIONSHIP",
    "EXPLICIT_COMPANY_PRODUCT_RELATIONSHIP",
}


@dataclass
class EntityResolutionResult:
    company_id: int | None
    company_name: str | None
    canonical_domain: str | None
    product_id: int | None
    product_name: str | None
    relationship_type: str
    confidence: float
    evidence: str
    is_confirmed: bool


class CISAEntityResolver:
    """Resolves CISA KEV entries against canonical Companies and Products with zero fabrication."""

    def __init__(self, db: Session):
        self.db = db
        self._load_catalog_cache()

    def _normalize_string(self, text: str) -> str:
        """Lowercases, removes punctuation, and strips whitespace."""
        return re.sub(r"[^a-z0-9\s]", "", text.lower()).strip()

    def _load_catalog_cache(self) -> None:
        """Loads canonical companies and products into fast memory indexes."""
        companies = self.db.scalars(select(Company)).all()
        self.companies_by_domain: dict[str, Company] = {}
        self.companies_by_norm_name: dict[str, Company] = {}
        self.companies_by_id: dict[int, Company] = {c.id: c for c in companies}

        for c in companies:
            if c.canonical_domain:
                self.companies_by_domain[c.canonical_domain.lower()] = c
            norm_name = self._normalize_string(c.name)
            self.companies_by_norm_name[norm_name] = c

            # Index aliases from metadata
            meta = c.meta or {}
            aliases = meta.get("aliases", [])
            if isinstance(aliases, list):
                for alias in aliases:
                    if alias and isinstance(alias, str):
                        self.companies_by_norm_name[self._normalize_string(alias)] = c

        # Load products
        products = self.db.scalars(select(Product)).all()
        self.products_by_company: dict[int, list[Product]] = {}
        self.products_by_norm_name: dict[str, list[Product]] = {}

        for p in products:
            self.products_by_company.setdefault(p.company_id, []).append(p)
            norm_pname = self._normalize_string(p.name)
            self.products_by_norm_name.setdefault(norm_pname, []).append(p)

    def resolve(self, vendor_project: str, product_name: str, cve_id: str) -> EntityResolutionResult:
        """Determines deterministic relationship between CISA fields and canonical corporate entities."""
        norm_vendor = self._normalize_string(vendor_project)
        norm_product = self._normalize_string(product_name)

        matched_company: Company | None = None
        matched_product: Product | None = None
        rel_type = "UNVERIFIED"
        confidence = 0.0
        evidence_parts: list[str] = []

        # Step 1: Check known vendor aliases mapping directly to canonical domain
        if norm_vendor in KNOWN_VENDOR_ALIASES:
            domain = KNOWN_VENDOR_ALIASES[norm_vendor]
            if domain in self.companies_by_domain:
                matched_company = self.companies_by_domain[domain]
                rel_type = "DIRECT_VENDOR_MATCH"
                confidence = 0.85
                evidence_parts.append(f"CISA vendor '{vendor_project}' mapped via verified corporate domain alias '{domain}'.")

        # Step 2: Check exact normalized company name or known alias
        if not matched_company and norm_vendor in self.companies_by_norm_name:
            matched_company = self.companies_by_norm_name[norm_vendor]
            rel_type = "DIRECT_VENDOR_MATCH"
            confidence = 0.85
            evidence_parts.append(f"CISA vendor '{vendor_project}' matches canonical company '{matched_company.name}'.")

        # Step 3: Product-level verification if company matched
        if matched_company:
            comp_products = self.products_by_company.get(matched_company.id, [])
            for p in comp_products:
                norm_p = self._normalize_string(p.name)
                if norm_p == norm_product or norm_p in norm_product or norm_product in norm_p:
                    matched_product = p
                    rel_type = "DIRECT_PRODUCT_MATCH"
                    confidence = 0.95
                    evidence_parts.append(f"CISA product '{product_name}' matches verified product '{p.name}' under {matched_company.name}.")
                    break

        # Step 4: If no company matched yet, check if product matches a known unique product
        if not matched_company and norm_product in self.products_by_norm_name:
            candidates = self.products_by_norm_name[norm_product]
            if len(candidates) == 1:
                p = candidates[0]
                matched_company = self.companies_by_id.get(p.company_id)
                if matched_company:
                    matched_product = p
                    rel_type = "EXPLICIT_COMPANY_PRODUCT_RELATIONSHIP"
                    confidence = 0.80
                    evidence_parts.append(f"CISA product '{product_name}' uniquely matches product '{p.name}' owned by {matched_company.name}.")

        # Step 5: Heuristic fuzzy check (POSSIBLE_MATCH — strictly unconfirmed)
        if not matched_company:
            for cname, comp in self.companies_by_norm_name.items():
                if len(cname) > 4 and (cname in norm_vendor or norm_vendor in cname):
                    matched_company = comp
                    rel_type = "POSSIBLE_MATCH"
                    confidence = 0.40
                    evidence_parts.append(f"Fuzzy name proximity between '{vendor_project}' and '{comp.name}' (unconfirmed).")
                    break

        if not matched_company:
            rel_type = "NO_RELATIONSHIP"
            confidence = 0.0
            evidence_parts.append(f"No canonical entity correlation found for vendor '{vendor_project}' and product '{product_name}'.")

        is_confirmed = rel_type in CONFIRMED_RELATIONSHIPS

        return EntityResolutionResult(
            company_id=matched_company.id if matched_company else None,
            company_name=matched_company.name if matched_company else None,
            canonical_domain=matched_company.canonical_domain if matched_company else None,
            product_id=matched_product.id if matched_product else None,
            product_name=matched_product.name if matched_product else None,
            relationship_type=rel_type,
            confidence=confidence,
            evidence=" | ".join(evidence_parts),
            is_confirmed=is_confirmed,
        )

    def sync_confirmed_events(self, limit: int = 2000) -> dict[str, int]:
        """Iterates through CISA KEV items and creates confirmed SecurityEvent records only when evidence is solid."""
        items = self.db.scalars(
            select(CISAKEVItem)
            .where(CISAKEVItem.is_active == True)  # noqa: E712
            .limit(limit)
        ).all()

        confirmed_count = 0
        skipped_unconfirmed = 0
        already_linked = 0

        for item in items:
            resolution = self.resolve(item.vendor_project, item.product, item.cve_id)

            # Strict guard: POSSIBLE_MATCH and UNVERIFIED NEVER become company vulnerabilities
            if not resolution.is_confirmed or not resolution.company_id:
                skipped_unconfirmed += 1
                continue

            # Check if SecurityEvent already exists for this CVE + Company
            existing = self.db.scalars(
                select(SecurityEvent).where(
                    SecurityEvent.company_id == resolution.company_id,
                    SecurityEvent.cve_id == item.cve_id,
                )
            ).first()

            if existing:
                already_linked += 1
                continue

            event = SecurityEvent(
                company_id=resolution.company_id,
                product_id=resolution.product_id,
                cve_id=item.cve_id,
                relationship_type=resolution.relationship_type,
                vulnerability_class="KNOWN_EXPLOITED_VULNERABILITY",
                affected_component=item.product,
                affected_versions=[],  # Empty list — zero fabrication of unprovided versions
                confidence=resolution.confidence,
                evidence=resolution.evidence,
                source="CISA_KEV",
                source_url=f"https://www.cisa.gov/known-exploited-vulnerabilities-catalog?search_api_fulltext={item.cve_id}",
                severity="CRITICAL" if item.known_ransomware_campaign_use == "Known" else "HIGH",
                summary=item.short_description,
                published=item.date_added,
                modified=item.last_seen_at,
                references=[f"https://nvd.nist.gov/vuln/detail/{item.cve_id}"],
                meta={
                    "data_origin": "SOURCE_VERIFIED",
                    "cisa_required_action": item.required_action,
                    "cisa_due_date": item.due_date.isoformat() if item.due_date else None,
                    "cisa_ransomware_use": item.known_ransomware_campaign_use,
                    "cisa_notes": item.notes,
                    "cisa_cwes": item.cwes,
                    "entity_resolution": {
                        "relationship_type": resolution.relationship_type,
                        "confidence": resolution.confidence,
                        "evidence": resolution.evidence,
                    },
                },
            )
            self.db.add(event)
            confirmed_count += 1

        self.db.commit()
        logger.info(
            "CISA Entity Resolution completed: %d confirmed events created, %d skipped unconfirmed, %d already linked",
            confirmed_count, skipped_unconfirmed, already_linked
        )
        return {
            "confirmed_created": confirmed_count,
            "skipped_unconfirmed": skipped_unconfirmed,
            "already_linked": already_linked,
        }
