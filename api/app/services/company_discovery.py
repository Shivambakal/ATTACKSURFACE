"""Safe Public Discovery and Evidence Fusion Engine.

Resolves companies canonical identity and extracts evidence-backed assets,
products, APIs, and security program policies without invasive scanning.
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

from app.models.company import Company
from app.models.asset import Asset
from app.models.asset_evidence import AssetEvidence
from app.models.product import Product
from app.models.security_program import SecurityProgram, ProgramScopeRule, InclusionType
from app.services.scope_resolver import ScopeResolver
from app.services.target_safety import normalize_domain, is_public_ip

logger = logging.getLogger(__name__)


KNOWN_COMPANY_ROOTS: dict[str, tuple[str, str]] = {
    "google": ("google.com", "Google"),
    "google cloud": ("google.com", "Google Cloud"),
    "alphabet": ("google.com", "Google / Alphabet"),
    "microsoft": ("microsoft.com", "Microsoft"),
    "github": ("github.com", "GitHub"),
    "cloudflare": ("cloudflare.com", "Cloudflare"),
    "stripe": ("stripe.com", "Stripe"),
    "openai": ("openai.com", "OpenAI"),
    "meta": ("meta.com", "Meta"),
    "facebook": ("meta.com", "Meta"),
    "amazon": ("amazon.com", "Amazon"),
    "aws": ("amazon.com", "Amazon Web Services"),
    "apple": ("apple.com", "Apple"),
    "netflix": ("netflix.com", "Netflix"),
    "shopify": ("shopify.com", "Shopify"),
    "slack": ("slack.com", "Slack"),
    "uber": ("uber.com", "Uber"),
    "airbnb": ("airbnb.com", "Airbnb"),
    "atlassian": ("atlassian.com", "Atlassian"),
    "gitlab": ("gitlab.com", "GitLab"),
}


def normalize_company_input(input_val: str) -> tuple[str, str]:
    """Converts a raw user input (URL, domain, or company name) into a canonical domain and name."""
    raw = input_val.strip()
    if not raw:
        raise ValueError("Company input cannot be empty.")

    lower = raw.lower()

    # Check known names first
    if lower in KNOWN_COMPANY_ROOTS:
        return KNOWN_COMPANY_ROOTS[lower]

    # Handle URLs
    if "://" in raw:
        parsed = urlparse(raw)
        host = parsed.netloc or parsed.path
    else:
        # Check if it has path
        host = raw.split("/")[0]

    # Strip port if present
    if ":" in host:
        host = host.split(":")[0]

    host = host.lower().strip().rstrip(".")
    if host.startswith("www."):
        host = host[4:]

    # If it looks like a domain with a dot
    if "." in host and len(host) >= 3:
        try:
            norm_domain = normalize_domain(host)
            # Default guessed name: capitalized domain base
            name_part = norm_domain.split(".")[0].capitalize()
            return norm_domain, name_part
        except Exception:
            pass

    # Treat as company name fallback
    slug = re.sub(r"[^a-z0-9]", "", lower)
    synthetic_domain = f"{slug}.com"
    return synthetic_domain, raw.title()


def resolve_or_create_company(
    db: Session,
    input_val: str,
    description: str | None = None,
) -> tuple[Company, bool]:
    """Idempotently resolves or creates a canonical Company."""
    canonical_domain, guessed_name = normalize_company_input(input_val)

    # 1. Try matching canonical domain
    company = db.query(Company).filter(Company.canonical_domain == canonical_domain).first()
    if company:
        return company, False

    # 2. Try matching name (case-insensitive)
    company = db.query(Company).filter(Company.name.ilike(guessed_name)).first()
    if company:
        return company, False

    # 3. Try matching aliases
    all_companies = db.query(Company).all()
    for c in all_companies:
        if c.aliases:
            for alias in c.aliases:
                if str(alias).lower() == input_val.strip().lower() or str(alias).lower() == canonical_domain:
                    return c, False

    # 4. Create new canonical company
    now = datetime.now(timezone.utc)
    new_company = Company(
        name=guessed_name,
        canonical_domain=canonical_domain,
        website_url=f"https://{canonical_domain}",
        description=description or f"Public attack surface graph for {guessed_name}",
        source_confidence=1.0,
        aliases=[input_val.strip()] if input_val.strip().lower() != canonical_domain else [],
        created_at=now,
        updated_at=now,
    )
    db.add(new_company)
    db.flush()
    return new_company, True


class CompanyDiscoveryService:
    """Safe public discovery service extracting evidence-backed assets."""

    @staticmethod
    def extract_subdomains_from_text(text: str, canonical_domain: str) -> set[str]:
        """Extracts valid subdomains of the canonical domain from text/HTML."""
        found = set()
        escaped_domain = re.escape(canonical_domain)
        # Match subdomain.canonical.com
        pattern = rf"(?:https?://)?([a-zA-Z0-9][-a-zA-Z0-9]*\.)+{escaped_domain}"
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for m in matches:
            val = m.group(0).lower()
            if "://" in val:
                parsed = urlparse(val)
                host = parsed.netloc
            else:
                host = val
            if ":" in host:
                host = host.split(":")[0]
            host = host.strip().rstrip(".")
            if host and (host == canonical_domain or host.endswith("." + canonical_domain)):
                try:
                    normalize_domain(host)
                    found.add(host)
                except Exception:
                    continue
        return found

    @classmethod
    async def discover_security_policy(
        cls,
        canonical_domain: str,
        client: httpx.AsyncClient,
    ) -> dict:
        """Checks /.well-known/security.txt for security contacts and bug bounty programs."""
        results = {
            "policy_url": None,
            "bug_bounty_url": None,
            "security_txt_url": None,
            "contacts": [],
            "acknowledgments": None,
            "raw_text": "",
        }

        urls = [
            f"https://{canonical_domain}/.well-known/security.txt",
            f"https://{canonical_domain}/security.txt",
        ]

        for u in urls:
            try:
                resp = await client.get(u, follow_redirects=True, timeout=5.0)
                if resp.status_code == 200 and ("Contact:" in resp.text or "Policy:" in resp.text or "Acknowledgments:" in resp.text):
                    results["security_txt_url"] = str(resp.url)
                    results["raw_text"] = resp.text
                    for line in resp.text.splitlines():
                        line = line.strip()
                        if line.startswith("Contact:"):
                            contact = line.split(":", 1)[1].strip()
                            results["contacts"].append(contact)
                            if "hackerone.com" in contact or "bugcrowd.com" in contact or "intigriti.com" in contact or "yeswehack.com" in contact:
                                results["bug_bounty_url"] = contact
                        elif line.startswith("Policy:"):
                            results["policy_url"] = line.split(":", 1)[1].strip()
                        elif line.startswith("Acknowledgments:"):
                            results["acknowledgments"] = line.split(":", 1)[1].strip()
                    break
            except Exception:
                continue

        return results

    @classmethod
    def fuse_discovered_assets(
        cls,
        db: Session,
        company: Company,
        discovered_candidates: list[dict],
    ) -> list[Asset]:
        """Fuses multiple discovery sources into deduplicated assets backed by AssetEvidence.

        Each candidate dict contains:
            - hostname: str
            - asset_type: str (e.g. ROOT_DOMAIN, SUBDOMAIN, API, DOCUMENTATION, SECURITY_PORTAL)
            - source_type: str (e.g. OFFICIAL_WEBSITE, SECURITY_POLICY, DOCUMENTATION, GITHUB)
            - source_url: str
            - evidence_text: str
            - base_confidence: float (default 0.70)
        """
        now = datetime.now(timezone.utc)
        assets_by_host: dict[str, Asset] = {}

        # Pre-load existing company assets
        existing_assets = db.query(Asset).filter(Asset.company_id == company.id).all()
        for a in existing_assets:
            host_key = (a.normalized_hostname or a.hostname or "").lower()
            if host_key:
                assets_by_host[host_key] = a

        fused_assets: list[Asset] = []

        for cand in discovered_candidates:
            raw_host = cand.get("hostname", "").strip().lower().rstrip(".")
            if not raw_host:
                continue
            try:
                norm_host = normalize_domain(raw_host)
            except Exception:
                continue

            source_type = cand.get("source_type", "OFFICIAL_WEBSITE")
            source_url = cand.get("source_url", f"https://{norm_host}")
            evidence_text = cand.get("evidence_text", f"Discovered via public reference on {source_url}")
            base_confidence = cand.get("base_confidence", 0.75)
            asset_type = cand.get("asset_type", "SUBDOMAIN")

            if norm_host in assets_by_host:
                # Existing asset: augment confidence and add evidence
                asset = assets_by_host[norm_host]
                # Corroborate confidence
                asset.confidence = min(0.99, round(asset.confidence + 0.10, 2))
                asset.last_seen_at = now
                asset.last_observed = now
            else:
                # New asset
                asset = Asset(
                    company_id=company.id,
                    name=norm_host,
                    hostname=norm_host,
                    normalized_hostname=norm_host,
                    scheme="https",
                    url=f"https://{norm_host}",
                    asset_type=asset_type,
                    parent_domain=company.canonical_domain,
                    source=source_type.lower(),
                    source_url=source_url,
                    confidence=base_confidence,
                    scope_status="UNKNOWN",
                    verification_status="UNVERIFIED",
                    active=True,
                    discovered_at=now,
                    first_observed=now,
                    last_observed=now,
                    last_seen_at=now,
                )
                db.add(asset)
                db.flush()
                assets_by_host[norm_host] = asset

            # Check if this evidence was already added
            existing_ev = (
                db.query(AssetEvidence)
                .filter(
                    AssetEvidence.asset_id == asset.id,
                    AssetEvidence.source_type == source_type,
                    AssetEvidence.source_url == source_url,
                )
                .first()
            )
            if not existing_ev:
                evidence = AssetEvidence(
                    asset_id=asset.id,
                    source_type=source_type,
                    source_url=source_url,
                    evidence_text=evidence_text,
                    confidence=base_confidence,
                    observed_at=now,
                    created_at=now,
                )
                db.add(evidence)

            # Resolve scope using ScopeResolver
            ScopeResolver.resolve_asset(db, asset, company)
            fused_assets.append(asset)

        db.flush()
        return list(assets_by_host.values())

    @classmethod
    def infer_and_link_products(
        cls,
        db: Session,
        company: Company,
        assets: list[Asset],
    ) -> list[Product]:
        """Infers high-level organizational products from confirmed public assets."""
        now = datetime.now(timezone.utc)
        products_map: dict[str, Product] = {}

        # Pre-load existing products
        for p in db.query(Product).filter(Product.company_id == company.id).all():
            products_map[p.name.lower()] = p

        product_keywords = [
            ("api", "API Platform", "REST & GraphQL developer APIs and programmatic access points"),
            ("docs", "Documentation & Developer Portal", "Official documentation, API references, and developer guides"),
            ("developer", "Developer Platform", "Developer resources, SDKs, and platform tooling"),
            ("accounts", "Identity & Authentication", "SSO, OAuth, and user identity management portal"),
            ("auth", "Authentication Service", "Authentication endpoints and authorization gateways"),
            ("admin", "Admin & Internal Console", "Administrative control interfaces"),
            ("status", "Infrastructure Status Portal", "System health and incident reporting portal"),
            ("cloud", "Cloud Services", "Cloud infrastructure and managed service endpoints"),
            ("billing", "Billing & Payments", "Payment processing, subscriptions, and financial capabilities"),
        ]

        for asset in assets:
            host = (asset.normalized_hostname or "").lower()
            for kw, prod_name, desc in product_keywords:
                if host.startswith(kw + ".") or f"-{kw}." in host:
                    prod_key = prod_name.lower()
                    if prod_key not in products_map:
                        new_prod = Product(
                            company_id=company.id,
                            name=prod_name,
                            description=desc,
                            domain_ids=[asset.id],
                            source_urls=[asset.url or f"https://{host}"],
                            confidence=0.85,
                            status="ACTIVE",
                            first_seen_at=now,
                            last_seen_at=now,
                        )
                        db.add(new_prod)
                        db.flush()
                        products_map[prod_key] = new_prod
                    else:
                        prod = products_map[prod_key]
                        d_ids = list(prod.domain_ids or [])
                        if asset.id not in d_ids:
                            d_ids.append(asset.id)
                            prod.domain_ids = d_ids
                            prod.last_seen_at = now
                            db.add(prod)

        db.flush()
        return list(products_map.values())
