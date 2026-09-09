"""Background job for idempotent public company enrichment."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

import httpx
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models.company import Company
from app.models.security_program import InclusionType, ProgramScopeRule, SecurityProgram
from app.models.signal import ResearchSignal, SignalType
from app.services.company_discovery import CompanyDiscoveryService
from app.services.scope_resolver import ScopeResolver

logger = logging.getLogger(__name__)


async def _enrich_company_async(company_id: int) -> dict:
    """Async orchestration of safe public enrichment for a company."""
    db: Session = SessionLocal()
    try:
        company = db.query(Company).filter(Company.id == company_id).first()
        if not company:
            logger.error("Company %s not found for enrichment", company_id)
            return {"status": "error", "message": "Company not found"}

        logger.info("Starting enrichment for company: %s (%s)", company.name, company.canonical_domain)
        now = datetime.now(timezone.utc)

        # 1. Discover Security Policy & Program Rules
        candidate_assets: list[dict] = []
        # Always register the canonical root domain
        candidate_assets.append({
            "hostname": company.canonical_domain,
            "asset_type": "ROOT_DOMAIN",
            "source_type": "OFFICIAL_WEBSITE",
            "source_url": company.website_url or f"https://{company.canonical_domain}",
            "evidence_text": f"Canonical registered organization root domain for {company.name}.",
            "base_confidence": 0.99,
        })

        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            # Check security.txt
            try:
                sec_info = await CompanyDiscoveryService.discover_security_policy(
                    company.canonical_domain, client
                )
                if sec_info.get("policy_url") or sec_info.get("bug_bounty_url"):
                    if not company.security_policy_url and sec_info.get("policy_url"):
                        company.security_policy_url = sec_info["policy_url"]
                    if not company.bug_bounty_url and sec_info.get("bug_bounty_url"):
                        company.bug_bounty_url = sec_info["bug_bounty_url"]

                    # Ensure SecurityProgram exists
                    sec_prog = (
                        db.query(SecurityProgram)
                        .filter(SecurityProgram.company_id == company.id)
                        .first()
                    )
                    if not sec_prog:
                        sec_prog = SecurityProgram(
                            company_id=company.id,
                            platform="HackerOne" if "hackerone" in (sec_info.get("bug_bounty_url") or "") else "Public Disclosure",
                            policy_url=sec_info.get("policy_url"),
                            program_url=sec_info.get("bug_bounty_url"),
                            source_url=sec_info.get("security_txt_url"),
                            status="ACTIVE",
                            scope_summary=f"Public vulnerability disclosure policy discovered at {sec_info.get('security_txt_url')}",
                            discovered_at=now,
                            last_verified_at=now,
                        )
                        db.add(sec_prog)
                        db.flush()

                        # Add default wildcard include rule
                        rule = ProgramScopeRule(
                            security_program_id=sec_prog.id,
                            pattern=f"*.{company.canonical_domain}",
                            inclusion_type=InclusionType.INCLUDE.value,
                            source_url=sec_info.get("security_txt_url"),
                            evidence="Wildcard scope derived from confirmed security policy",
                            confidence=0.90,
                            last_verified_at=now,
                            created_at=now,
                        )
                        db.add(rule)
                        db.flush()
            except Exception as e:
                logger.warning("Security.txt discovery error for %s: %s", company.canonical_domain, e)

            # Discover public links from root homepage
            try:
                resp = await client.get(f"https://{company.canonical_domain}", timeout=8.0)
                if resp.status_code == 200:
                    found_subdomains = CompanyDiscoveryService.extract_subdomains_from_text(
                        resp.text, company.canonical_domain
                    )
                    for sub in found_subdomains:
                        asset_type = "SUBDOMAIN"
                        if sub.startswith("api."):
                            asset_type = "API"
                        elif sub.startswith("docs.") or sub.startswith("developer."):
                            asset_type = "DOCUMENTATION"
                        elif sub.startswith("auth.") or sub.startswith("accounts.") or sub.startswith("login."):
                            asset_type = "SECURITY_PORTAL"
                        elif sub.startswith("admin."):
                            asset_type = "WEB_APPLICATION"

                        candidate_assets.append({
                            "hostname": sub,
                            "asset_type": asset_type,
                            "source_type": "OFFICIAL_WEBSITE",
                            "source_url": f"https://{company.canonical_domain}",
                            "evidence_text": f"Referenced in public HTML links of official site https://{company.canonical_domain}",
                            "base_confidence": 0.85,
                        })
            except Exception as e:
                logger.warning("Homepage discovery error for %s: %s", company.canonical_domain, e)

        # 2. Fuse candidate assets
        fused_assets = CompanyDiscoveryService.fuse_discovered_assets(
            db, company, candidate_assets
        )

        # 3. Infer products
        products = CompanyDiscoveryService.infer_and_link_products(
            db, company, fused_assets
        )

        # 4. Generate Research Signals for high-interest discovered assets
        for a in fused_assets:
            host = (a.normalized_hostname or "").lower()
            # If an admin portal or auth surface was discovered
            if host.startswith("admin.") or host.startswith("internal."):
                existing_sig = (
                    db.query(ResearchSignal)
                    .filter(
                        ResearchSignal.company_id == company.id,
                        ResearchSignal.asset_id == a.id,
                    )
                    .first()
                )
                if not existing_sig:
                    sig = ResearchSignal(
                        company_id=company.id,
                        asset_id=a.id,
                        title=f"Public Admin Portal Discovered ({host})",
                        signal_type=SignalType.NEW_ASSET.value,
                        summary=f"Discovered administrative host {host} exposed to public ingress with {a.scope_status} scope status.",
                        why_it_matters="Administrative interfaces exposed externally present high-value authentication and authorization research opportunities.",
                        recommended_research_area="Evaluate authentication requirements, MFA enforcement, and access controls.",
                        relevance_score=85,
                        confidence_score=int(a.confidence * 100),
                        priority="HIGH",
                        created_at=now,
                        updated_at=now,
                    )
                    db.add(sig)

        company.last_enriched_at = now
        db.commit()

        logger.info(
            "Enrichment completed for %s: %d assets, %d products",
            company.name, len(fused_assets), len(products)
        )
        return {
            "status": "success",
            "company_id": company.id,
            "assets_count": len(fused_assets),
            "products_count": len(products),
        }
    except Exception as exc:
        db.rollback()
        logger.exception("Company enrichment job failed for %s: %s", company_id, exc)
        return {"status": "failed", "error": str(exc)}
    finally:
        db.close()


def enrich_company(company_id: int) -> dict:
    """Synchronous RQ entry point."""
    return asyncio.run(_enrich_company_async(company_id))
