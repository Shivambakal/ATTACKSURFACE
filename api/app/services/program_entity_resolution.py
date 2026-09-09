"""Program Entity Resolution and Canonical Identity Service.

Resolves public security programs and bug-bounty registries to canonical
companies with strict data-truth validation. Preserves existing companies,
targets, assets, and signals while deduplicating multi-platform programs.
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
from datetime import datetime, timezone
from urllib.parse import urlparse
from typing import Any, Optional

from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.base import utcnow
from app.models.company import Company
from app.models.security_program import (
    SecurityProgram,
    ProgramScopeRule,
    ProgramSnapshot,
    ProgramChangeEvent,
    InclusionType,
)
from app.models.timeline import TimelineEvent
from app.services.target_safety import is_public_ip

logger = logging.getLogger(__name__)

# Known multi-part public suffixes to properly identify registrable root domains
MULTI_PART_TLDS = {
    "co.uk", "org.uk", "gov.uk", "ac.uk", "net.uk", "ltd.uk", "me.uk", "plc.uk",
    "com.au", "net.au", "org.au", "edu.au", "gov.au",
    "co.nz", "net.nz", "org.nz", "govt.nz",
    "co.jp", "ne.jp", "or.jp", "go.jp", "ac.jp",
    "com.br", "net.br", "org.br", "gov.br",
    "com.mx", "org.mx", "gob.mx", "edu.mx",
    "co.in", "net.in", "org.in", "gen.in", "firm.in", "ind.in", "nic.in", "gov.in",
    "co.za", "net.za", "org.za", "gov.za",
    "com.sg", "net.sg", "org.sg", "edu.sg", "gov.sg",
    "com.hk", "net.hk", "org.hk", "edu.hk", "gov.hk",
    "com.tw", "org.tw", "gov.tw", "net.tw",
    "com.tr", "net.tr", "org.tr", "gov.tr", "edu.tr",
    "co.kr", "ne.kr", "or.kr", "re.kr", "pe.kr", "go.kr",
    "com.ar", "net.ar", "org.ar", "gob.ar",
    "com.co", "net.co", "org.co", "gov.co",
    "com.pe", "net.pe", "org.pe", "gob.pe",
    "com.ph", "net.ph", "org.ph", "gov.ph",
    "com.my", "net.my", "org.my", "gov.my", "edu.my",
    "com.ng", "net.ng", "org.ng", "gov.ng",
    "co.id", "net.id", "or.id", "go.id",
    "co.il", "org.il", "net.il", "gov.il",
    "com.ua", "net.ua", "org.ua", "gov.ua",
    "co.th", "ac.th", "go.th", "net.th", "or.th",
    "com.pk", "net.pk", "org.pk", "gov.pk",
    "com.bd", "net.bd", "org.bd", "gov.bd",
    "com.vn", "net.vn", "org.vn", "gov.vn",
    "com.sa", "net.sa", "org.sa", "gov.sa",
    "com.eg", "net.eg", "org.eg", "gov.eg",
}

# Domains of bug bounty platforms and third-party hosting providers
# that MUST NOT be used as the canonical domain of a customer program.
PLATFORM_AND_THIRD_PARTY_DOMAINS = {
    "hackerone.com",
    "bugcrowd.com",
    "intigriti.com",
    "yeswehack.com",
    "federacy.com",
    "hackenproof.com",
    "openbugbounty.org",
    "synack.com",
    "immunefi.com",
    "github.com",
    "github.io",
    "gitlab.com",
    "bitbucket.org",
    "google.com",
    "docs.google.com",
    "drive.google.com",
    "play.google.com",
    "apple.com",
    "apps.apple.com",
    "itunes.apple.com",
    "microsoft.com",
    "azure.com",
    "amazonaws.com",
    "aws.amazon.com",
    "cloudfront.net",
    "cloudflare.com",
    "facebook.com",
    "fb.com",
    "twitter.com",
    "x.com",
    "linkedin.com",
    "instagram.com",
    "youtube.com",
    "t.me",
    "telegram.org",
    "discord.com",
    "discord.gg",
    "medium.com",
    "notion.so",
    "notion.site",
    "zendesk.com",
    "atlassian.net",
    "jira.com",
    "confluence.com",
    "slack.com",
    "zoom.us",
    "salesforce.com",
    "force.com",
    "hubspot.com",
    "shopify.com",
    "myshopify.com",
    "wordpress.com",
    "wix.com",
    "squarespace.com",
    "s3.amazonaws.com",
}

# Legal suffixes to strip when normalizing company names
LEGAL_SUFFIXES_REGEX = re.compile(
    r"(?i)\b(inc\.?|incorporated|llc\.?|l\.l\.c\.?|ltd\.?|limited|corp\.?|corporation|co\.?|"
    r"gmbh|s\.?a\.?|s\.?l\.?|b\.?v\.?|pty\.?\s+ltd\.?|ag|s\.?p\.?a\.?|plc|holding|holdings|"
    r"group|technologies|technology|labs|systems|software|security|solutions)\b"
)

PROGRAM_ANNOTATIONS_REGEX = re.compile(
    r"(?i)\s*[-–—/|]?\s*[\(\[\{]?(bug\s*bounty(\s*program)?|vulnerability\s*disclosure(\s*program)?|vdp|bbp|security)[\)\]\}]?\s*$"
)


def extract_root_domain(raw_val: str | None) -> str | None:
    """Extracts a valid registrable root domain from an arbitrary target string or URL.

    Returns None if the value is invalid, an IP, a third-party platform host,
    or a non-domain token.
    """
    if not raw_val or not isinstance(raw_val, str):
        return None

    s = raw_val.strip().lower()
    if not s or s.startswith(("#", "//", "mailto:", "tel:", "javascript:")):
        return None

    # Handle URL parsing
    if "://" in s:
        try:
            parsed = urlparse(s)
            host = parsed.netloc or parsed.path
        except Exception:
            host = s
    else:
        # Strip path / query
        host = s.split("/")[0].split("?")[0].split("#")[0]

    # Strip port
    if ":" in host:
        host = host.split(":")[0]

    # Strip wildcards (*.example.com -> example.com)
    host = host.lstrip("*.")
    host = host.strip(".")

    # Quick rejection
    if not host or len(host) > 253 or " " in host:
        return None

    # Strip leading www.
    if host.startswith("www."):
        host = host[4:]

    # Check if host is IP address or private
    if is_public_ip(host):
        return None
    try:
        # Reject if valid IP (v4 or v6)
        import ipaddress
        ipaddress.ip_address(host)
        return None
    except ValueError:
        pass

    # Reject Android package IDs (e.g. com.company.app) if looks like package name without TLD
    labels = host.split(".")
    if len(labels) < 2:
        return None

    # Verify each label is valid hostname label
    for label in labels:
        if not label or len(label) > 63:
            return None
        if not label.replace("-", "").isalnum():
            return None
        if label.startswith("-") or label.endswith("-"):
            return None

    # Reject reverse-notation package IDs (e.g. com.company.app, org.project.app)
    if labels[0] in {"com", "org", "net", "io", "app"} and len(labels) >= 3:
        return None

    tld = labels[-1]
    # TLD must be alphabetic and at least 2 chars (e.g. com, org, io)
    if not tld.isalpha() or len(tld) < 2:
        return None

    # Check multi-part TLDs (e.g., sub.example.co.uk)
    if len(labels) >= 3:
        two_part_tld = f"{labels[-2]}.{labels[-1]}"
        if two_part_tld in MULTI_PART_TLDS:
            root = f"{labels[-3]}.{two_part_tld}"
            if root in PLATFORM_AND_THIRD_PARTY_DOMAINS:
                return None
            return root

    # Standard 2-label root domain (e.g. example.com)
    root = f"{labels[-2]}.{labels[-1]}"
    if root in PLATFORM_AND_THIRD_PARTY_DOMAINS:
        return None

    return root


def clean_company_name(raw_name: str | None, fallback_domain: str | None = None) -> str:
    """Cleans and standardizes a company name for canonical deduplication.

    Strips legal boilerplate and program suffixes like ' (Bug Bounty Program)'.
    """
    if not raw_name or not isinstance(raw_name, str):
        if fallback_domain:
            return fallback_domain.split(".")[0].capitalize()
        return "Unknown Organization"

    name = raw_name.strip()

    # Remove program annotations
    name = PROGRAM_ANNOTATIONS_REGEX.sub("", name).strip()
    name = re.sub(r"(?i)\s*-\s*(bug\s*bounty|vdp|security)\s*$", "", name).strip()

    # Strip legal boilerplate repeatedly until clean
    while True:
        old = name
        name = re.sub(
            r"(?i)[,.\s]+(inc\.?|incorporated|llc\.?|l\.l\.c\.?|ltd\.?|limited|corp\.?|corporation|co\.?|gmbh|s\.?a\.?|s\.?l\.?|b\.?v\.?|pty\.?\s+ltd\.?|ag|s\.?p\.?a\.?|plc|technologies|technology)\b",
            "",
            name,
        ).strip()
        name = re.sub(r"[,.\s\-–—/|]+$", "", name).strip()
        if name == old:
            break

    # Collapse multiple spaces
    name = re.sub(r"\s+", " ", name)

    # If empty after cleanup, fallback to domain base
    if not name or len(name) < 2:
        if fallback_domain:
            return fallback_domain.split(".")[0].capitalize()
        return "Unknown Organization"

    return name


def normalize_name_for_matching(name: str) -> str:
    """Generates an alphanumeric-only lowercase token for fuzzy company name matching."""
    cleaned = clean_company_name(name)
    # Strip legal suffixes for matching token
    token = LEGAL_SUFFIXES_REGEX.sub("", cleaned)
    token = re.sub(r"[^a-z0-9]", "", token.lower())
    return token or cleaned.lower()


def compute_scope_hash(scope_rules: list[dict]) -> str:
    """Computes a deterministic MD5/SHA256 fingerprint for a program's scope rules."""
    normalized = []
    for r in sorted(scope_rules, key=lambda x: (x.get("target") or x.get("asset_identifier") or "")):
        pat = (r.get("target") or r.get("asset_identifier") or "").strip().lower()
        inc = (r.get("inclusion_type") or ("INCLUDE" if r.get("eligible_for_submission", True) else "EXCLUDE")).upper()
        typ = (r.get("type") or r.get("asset_type") or "URL").upper()
        bounty = bool(r.get("eligible_for_bounty") or r.get("bounty", False))
        normalized.append(f"{inc}|{typ}|{pat}|{bounty}")

    blob = "\n".join(normalized).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()[:32]


class ProgramEntityResolutionService:
    """Authoritative entity resolution engine for public bug-bounty ecosystems."""

    def __init__(self, db: Session):
        self.db = db
        self._load_existing_indexes()

    def _load_existing_indexes(self):
        """Loads in-memory lookup caches of existing canonical companies and programs."""
        self.companies_by_domain: dict[str, Company] = {}
        self.companies_by_name_token: dict[str, Company] = {}
        self.companies_by_id: dict[int, Company] = {}

        # Fetch all existing companies
        existing_companies = self.db.query(Company).all()
        for comp in existing_companies:
            self.companies_by_id[comp.id] = comp
            if comp.canonical_domain:
                norm_d = comp.canonical_domain.strip().lower()
                self.companies_by_domain[norm_d] = comp

            if comp.name:
                token = normalize_name_for_matching(comp.name)
                if token:
                    self.companies_by_name_token[token] = comp

            # Also index known aliases
            if comp.aliases:
                for alias in comp.aliases:
                    if isinstance(alias, str):
                        alias_token = normalize_name_for_matching(alias)
                        if alias_token and alias_token not in self.companies_by_name_token:
                            self.companies_by_name_token[alias_token] = comp

        # Fetch all existing security programs
        self.programs_by_key: dict[tuple[int, str, str], SecurityProgram] = {}
        existing_programs = self.db.query(SecurityProgram).all()
        for prog in existing_programs:
            handle = (prog.program_handle or "").strip().lower()
            plat = (prog.platform or "").strip().lower()
            self.programs_by_key[(prog.company_id, plat, handle)] = prog

    def resolve_candidate_company(
        self,
        program_data: dict[str, Any],
    ) -> tuple[Optional[Company], Optional[str], str]:
        """Resolves a program to an existing canonical company or extracts valid attributes for a new one.

        Returns (company_or_none, canonical_domain, canonical_name).
        """
        raw_name = program_data.get("program_name") or program_data.get("name") or ""
        website = program_data.get("website") or ""
        program_url = program_data.get("program_url") or program_data.get("url") or ""
        in_scope = program_data.get("in_scope") or []

        # 1. Candidate domains from website, targets, or URL
        candidate_domain = extract_root_domain(website)
        if not candidate_domain and in_scope:
            for item in in_scope:
                target_str = item.get("target") or item.get("asset_identifier") or ""
                dom = extract_root_domain(target_str)
                if dom:
                    candidate_domain = dom
                    break

        canonical_name = clean_company_name(raw_name, candidate_domain)

        # 2. Match by exact canonical root domain
        if candidate_domain and candidate_domain in self.companies_by_domain:
            return self.companies_by_domain[candidate_domain], candidate_domain, canonical_name

        # 3. Match by normalized name token
        name_token = normalize_name_for_matching(canonical_name)
        if name_token and name_token in self.companies_by_name_token:
            matched = self.companies_by_name_token[name_token]
            return matched, matched.canonical_domain, matched.name

        return None, candidate_domain, canonical_name

    def ingest_program_record(
        self,
        program_data: dict[str, Any],
    ) -> tuple[Optional[SecurityProgram], bool, bool]:
        """Ingests a single normalized program record, resolving or creating the canonical company.

        Returns (program, company_created, program_created).
        """
        matched_company, canonical_domain, canonical_name = self.resolve_candidate_company(program_data)
        company_created = False
        program_created = False

        if not matched_company:
            # If no existing company and no valid domain, we cannot create a company without violating Zero Fabrication
            if not canonical_domain:
                logger.debug("Skipping program with no valid root domain: %s", program_data.get("name"))
                return None, False, False

            # Check again against DB domain uniqueness
            if canonical_domain in self.companies_by_domain:
                matched_company = self.companies_by_domain[canonical_domain]
            else:
                # Create verified canonical company
                matched_company = Company(
                    name=canonical_name,
                    canonical_domain=canonical_domain,
                    website_url=program_data.get("website") or f"https://{canonical_domain}",
                    bug_bounty_url=program_data.get("program_url") or program_data.get("url"),
                    industry="Technology / Internet",
                    tracking_status="ACTIVE",
                    source_confidence=1.0,
                    aliases=[canonical_name, canonical_domain],
                    meta={
                        "ingested_from": program_data.get("platform", "PUBLIC_ECOSYSTEM"),
                        "ingested_at": utcnow().isoformat(),
                        "verified_public_program": True,
                    },
                )
                self.db.add(matched_company)
                self.db.flush()  # Generate ID

                # Update in-memory indexes
                self.companies_by_id[matched_company.id] = matched_company
                self.companies_by_domain[canonical_domain] = matched_company
                name_token = normalize_name_for_matching(canonical_name)
                if name_token:
                    self.companies_by_name_token[name_token] = matched_company
                company_created = True

        # Now resolve or create SecurityProgram
        platform = program_data.get("platform") or "Self-Hosted"
        handle = (program_data.get("program_handle") or program_data.get("handle") or "").strip()
        prog_key = (matched_company.id, platform.lower(), handle.lower())

        security_program = self.programs_by_key.get(prog_key)

        prog_name = program_data.get("program_name") or program_data.get("name") or canonical_name
        prog_url = program_data.get("program_url") or program_data.get("url")
        is_public = bool(program_data.get("is_public", True))
        offers_bounties = bool(program_data.get("offers_bounties") or program_data.get("bounty", False))
        min_bounty = program_data.get("min_bounty")
        max_bounty = program_data.get("max_bounty")
        currency = program_data.get("currency") or "USD"
        submission_state = program_data.get("submission_state") or "OPEN"

        in_scope = program_data.get("in_scope") or []
        out_of_scope = program_data.get("out_of_scope") or []
        total_scope_count = len(in_scope) + len(out_of_scope)
        scope_summary = f"{len(in_scope)} in-scope targets, {len(out_of_scope)} out-of-scope targets"

        if not security_program:
            security_program = SecurityProgram(
                company_id=matched_company.id,
                platform=platform,
                program_name=prog_name,
                program_handle=handle or None,
                program_type="BUG_BOUNTY" if offers_bounties else "VULNERABILITY_DISCLOSURE",
                program_url=prog_url,
                policy_url=program_data.get("policy_url"),
                source_url=program_data.get("source_url") or prog_url,
                status="ACTIVE",
                is_public=is_public,
                offers_bounties=offers_bounties,
                min_bounty=float(min_bounty) if min_bounty is not None else None,
                max_bounty=float(max_bounty) if max_bounty is not None else None,
                currency=currency,
                submission_state=submission_state,
                scope_summary=scope_summary,
                meta={
                    "last_synced_at": utcnow().isoformat(),
                    "platform": platform,
                    "offers_bounties": offers_bounties,
                },
                last_verified_at=utcnow(),
            )
            self.db.add(security_program)
            self.db.flush()
            self.programs_by_key[prog_key] = security_program
            program_created = True
        else:
            # Update existing program attributes
            security_program.program_name = prog_name
            security_program.offers_bounties = offers_bounties
            if min_bounty is not None:
                security_program.min_bounty = float(min_bounty)
            if max_bounty is not None:
                security_program.max_bounty = float(max_bounty)
            security_program.submission_state = submission_state
            security_program.scope_summary = scope_summary
            security_program.last_verified_at = utcnow()

        # Scope Rules & Snapshot Diffing
        current_hash = compute_scope_hash(in_scope + out_of_scope)

        # Check existing latest snapshot
        latest_snapshot = (
            self.db.query(ProgramSnapshot)
            .filter(ProgramSnapshot.security_program_id == security_program.id)
            .order_by(ProgramSnapshot.created_at.desc())
            .first()
        )

        has_scope_changed = False
        if not latest_snapshot or latest_snapshot.snapshot_hash != current_hash:
            has_scope_changed = True
            # Create new snapshot
            new_snapshot = ProgramSnapshot(
                security_program_id=security_program.id,
                snapshot_hash=current_hash,
                scope_count=total_scope_count,
                scope_summary=scope_summary,
                bounty_table={
                    "min_bounty": min_bounty,
                    "max_bounty": max_bounty,
                    "currency": currency,
                    "offers_bounties": offers_bounties,
                },
                raw_payload_reference={"total_targets": total_scope_count},
            )
            self.db.add(new_snapshot)

            # Record ProgramChangeEvent if there was a previous snapshot
            if latest_snapshot:
                change_type = "PROGRAM_SCOPE_CHANGED"
                summary = f"Program scope updated for {prog_name} ({platform}): {total_scope_count} items."
                if total_scope_count > latest_snapshot.scope_count:
                    change_type = "PROGRAM_SCOPE_ADDED"
                    summary = f"Scope expanded for {prog_name} ({platform}): +{total_scope_count - latest_snapshot.scope_count} targets."
                elif total_scope_count < latest_snapshot.scope_count:
                    change_type = "PROGRAM_SCOPE_REMOVED"
                    summary = f"Scope reduced for {prog_name} ({platform}): -{latest_snapshot.scope_count - total_scope_count} targets."

                change_event = ProgramChangeEvent(
                    security_program_id=security_program.id,
                    company_id=matched_company.id,
                    change_type=change_type,
                    summary=summary,
                    diff_details={
                        "previous_scope_count": latest_snapshot.scope_count,
                        "current_scope_count": total_scope_count,
                    },
                    confidence=1.0,
                )
                self.db.add(change_event)

                # Generate TimelineEvent for public intelligence timeline
                timeline_evt = TimelineEvent(
                    company_id=matched_company.id,
                    event_type="PUBLIC_PROGRAM_SCOPE_CHANGE",
                    title=f"Security Program Scope Changed: {matched_company.name}",
                    summary=summary,
                    source=f"Public Program ({platform})",
                    source_url=prog_url,
                    provenance_category="PUBLIC_SECURITY_PROGRAM",
                    temporal_category="CURRENT",
                    confidence=1.0,
                    relevance_score=75,
                    priority="INFO",
                )
                self.db.add(timeline_evt)

        # Ingest Scope Rules if changed or first time
        if has_scope_changed and in_scope:
            # Delete existing rules for this program to ensure clean sync
            self.db.query(ProgramScopeRule).filter(
                ProgramScopeRule.security_program_id == security_program.id
            ).delete()

            # Insert top 50 in-scope rules per program to keep DB balanced
            for item in in_scope[:50]:
                pat = (item.get("target") or item.get("asset_identifier") or "").strip()
                if not pat:
                    continue
                asset_type = item.get("type") or item.get("asset_type") or "URL"
                rule = ProgramScopeRule(
                    security_program_id=security_program.id,
                    pattern=pat[:255],
                    asset_type=asset_type[:64],
                    inclusion_type=InclusionType.INCLUDE.value,
                    source_url=prog_url,
                    confidence=0.95,
                    last_verified_at=utcnow(),
                )
                self.db.add(rule)

        return security_program, company_created, program_created
