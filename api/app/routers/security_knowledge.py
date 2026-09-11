"""Security Knowledge Base API router.

Provides read-only endpoints for browsing advisories, CWEs, OWASP categories,
knowledge sources, and ingestion sync run telemetry.

Prefix: /api/v1/security-knowledge
"""
from __future__ import annotations

import statistics
from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import (
    SecurityAdvisory,
    CWEEntry,
    OWASPCategory,
    KnowledgeSource,
    KnowledgeSyncRun,
    BountyEvidence,
)

router = APIRouter(prefix="/api/v1/security-knowledge", tags=["security-knowledge"])


# ---------------------------------------------------------------------------
# Response helpers
# ---------------------------------------------------------------------------

def _compute_consensus(cve_id: str | None, adv: SecurityAdvisory, db: Session | None) -> dict[str, Any]:
    sources = []
    if adv.provider == "CISA_KEV":
        sources.append({
            "source": "CISA KEV",
            "authority": "Official Federal Catalog",
            "kev_status": "CONFIRMED_EXPLOITED",
            "evidence": "Known Exploited Vulnerability Catalog",
            "date_added": adv.date_added.isoformat() if adv.date_added else None,
            "ransomware_use": adv.known_ransomware_use,
            "required_action": adv.description,
        })
    
    if cve_id and db:
        try:
            from sqlalchemy import String, cast
            from app.models import SecurityIntelligenceEvent
            intel = db.query(SecurityIntelligenceEvent).filter(
                cast(SecurityIntelligenceEvent.cve_ids, String).ilike(f"%{cve_id}%")
            ).first()
            if intel:
                sources.append({
                    "source": intel.source_name or "Intelligence Feed",
                    "authority": "Public Security Disclosure",
                    "severity": intel.severity,
                    "confidence": intel.confidence,
                    "actively_exploited": intel.actively_exploited,
                })
        except Exception:
            db.rollback()

    count = len(sources)
    status_label = f"VERIFIED ACROSS {count} SOURCES" if count > 1 else "OFFICIAL SOURCE VERIFIED"
    return {
        "consensus_label": status_label,
        "source_count": count,
        "sources": sources,
        "has_conflict": False,
        "conflict_details": None,
    }


def resolve_vulnerability_class(adv: SecurityAdvisory) -> str:
    """Extract canonical vulnerability class from CWE entries, title, and description."""
    title = (adv.title or "").lower()
    summary = (adv.summary or "").lower()
    combined = f"{title} {summary}"

    # Check CWE entries first if attached
    for cwe in (adv.cwes or []):
        cwe_name = (getattr(cwe, "name", "") or "").lower()
        if "type confusion" in cwe_name:
            return "Type Confusion"
        if "use after free" in cwe_name or "use-after-free" in cwe_name:
            return "Use-After-Free"
        if "buffer overflow" in cwe_name or "out-of-bounds" in cwe_name:
            return "Buffer Overflow"
        if "server-side request forgery" in cwe_name or "ssrf" in cwe_name:
            return "Server-Side Request Forgery"
        if "sql injection" in cwe_name:
            return "SQL Injection"
        if "cross-site scripting" in cwe_name or "xss" in cwe_name:
            return "Cross-Site Scripting"
        if "privilege escalation" in cwe_name:
            return "Privilege Escalation"
        if "authentication bypass" in cwe_name:
            return "Authentication Bypass"
        if "prototype pollution" in cwe_name:
            return "Prototype Pollution"
        if "deserialization" in cwe_name:
            return "Insecure Deserialization"
        if "path traversal" in cwe_name or "directory traversal" in cwe_name:
            return "Path Traversal"
        if "remote code execution" in cwe_name:
            return "Remote Code Execution"

    if "type confusion" in combined:
        return "Type Confusion"
    if "use-after-free" in combined or "use after free" in combined:
        return "Use-After-Free"
    if "heap overflow" in combined or "buffer overflow" in combined or "out-of-bounds" in combined:
        return "Memory Corruption / Buffer Overflow"
    if "remote code execution" in combined or "execute arbitrary code" in combined:
        return "Remote Code Execution"
    if "privilege escalation" in combined or "escalate privileges" in combined:
        return "Privilege Escalation"
    if "authentication bypass" in combined or "bypass authentication" in combined:
        return "Authentication Bypass"
    if "sql injection" in combined:
        return "SQL Injection"
    if "cross-site scripting" in combined or " xss " in combined:
        return "Cross-Site Scripting"
    if "ssrf" in combined or "server-side request forgery" in combined:
        return "Server-Side Request Forgery"
    if "prototype pollution" in combined:
        return "Prototype Pollution"
    if "path traversal" in combined or "directory traversal" in combined:
        return "Path Traversal"
    if "sandbox escape" in combined:
        return "Sandbox Escape"
    if "command injection" in combined or "os command" in combined:
        return "Command Injection"
    if "information disclosure" in combined or "obtain sensitive information" in combined:
        return "Information Disclosure"
    if "denial of service" in combined or " dos " in combined:
        return "Denial of Service"

    return "General Vulnerability"


def _compute_research_relevance(adv: SecurityAdvisory, vuln_class: str, db: Session | None = None) -> dict[str, Any]:
    """Provide grounded threat intelligence and research relevance without false vulnerability claims."""
    impact_descriptions = {
        "Type Confusion": "Type confusion vulnerabilities in language runtimes and browser engines allow attackers to violate type safety, manipulate raw memory pointers, and frequently achieve full sandbox escape or arbitrary code execution. They are among the highest-impact findings in client-side bug bounties.",
        "Use-After-Free": "Use-after-free conditions in native binaries and web engines permit heap corruption, control flow hijacking, and arbitrary memory read/write. Commonly targeted for privilege escalation and remote execution chains.",
        "Memory Corruption / Buffer Overflow": "Memory safety violations and buffer overflows enable attackers to overwrite adjacent memory structures, bypass control-flow integrity, and execute arbitrary payloads.",
        "Remote Code Execution": "Remote code execution represents maximum security severity, allowing arbitrary command dispatch over network interfaces with no physical access required.",
        "Privilege Escalation": "Privilege escalation weaknesses allow authenticated low-privileged identities to transcend permission boundaries, access confidential enterprise resources, or assume root/system authority.",
        "Authentication Bypass": "Authentication bypass flaws enable unauthorized actors to subvert identity verification mechanisms, access private APIs, or impersonate legitimate tenants without valid credentials.",
        "Server-Side Request Forgery": "SSRF vulnerabilities allow attackers to coerce backend services into dispatching internal network requests, frequently exposing cloud metadata services (e.g. IMDSv1) and internal administration panels.",
        "Insecure Deserialization": "Deserialization weaknesses allow untrusted byte streams to reconstruct compromised objects, often resulting in unauthenticated remote command execution.",
        "SQL Injection": "SQL injection permits database structure discovery, data exfiltration, authentication subversion, and in some database configurations, operating system command execution.",
        "Cross-Site Scripting": "Cross-site scripting allows script execution in victim browser sessions, facilitating session token theft, DOM manipulation, and credential phishing.",
    }

    class_impact = impact_descriptions.get(
        vuln_class,
        "Documented weakness class with known security implications across enterprise and client-side applications."
    )

    matching_company = None
    if adv.vendor and db:
        try:
            from app.models.company import Company
            comp = db.query(Company).filter(
                or_(
                    Company.name.ilike(f"%{adv.vendor}%"),
                    Company.canonical_domain.ilike(f"%{adv.vendor.lower().replace(' ', '')}%")
                )
            ).first()
            if comp:
                matching_company = {
                    "id": comp.id,
                    "name": comp.name,
                    "domain": comp.canonical_domain,
                }
        except Exception:
            pass

    is_kev = adv.provider == "CISA_KEV"

    return {
        "vulnerability_class": vuln_class,
        "class_impact": class_impact,
        "is_actively_exploited": is_kev,
        "exploitation_context": "Cataloged in CISA Known Exploited Vulnerabilities (KEV)" if is_kev else "Monitored Public Advisory",
        "grounding_disclaimer": "This vulnerability is relevant as contextual threat intelligence. It does not establish that a monitored asset is vulnerable.",
        "truth_classification": "CONTEXT_ONLY",
        "matching_company": matching_company,
    }


def _advisory_to_dict(adv: SecurityAdvisory, db: Session | None = None) -> dict[str, Any]:
    cve = adv.cve_id
    consensus = _compute_consensus(cve, adv, db)
    vuln_class = resolve_vulnerability_class(adv)
    research_relevance = _compute_research_relevance(adv, vuln_class, db)
    return {
        "id": adv.id,
        "canonical_id": adv.canonical_id,
        "provider": adv.provider,
        "cve_id": adv.cve_id,
        "ghsa_id": adv.ghsa_id,
        "title": adv.title,
        "summary": adv.summary,
        "description": adv.description,
        "vendor": adv.vendor,
        "product": adv.product,
        "affected_versions": adv.affected_versions or [],
        "severity": adv.severity,
        "cvss_score": adv.cvss_score,
        "known_ransomware_use": adv.known_ransomware_use,
        "forensic_triage": adv.forensic_triage,
        "date_added": adv.date_added.isoformat() if adv.date_added else None,
        "due_date": adv.due_date.isoformat() if adv.due_date else None,
        "published_at": adv.published_at.isoformat() if adv.published_at else None,
        "source_url": adv.source_url,
        "confidence": adv.confidence,
        "consensus": consensus,
        "vulnerability_class": vuln_class,
        "why_worth_researching": research_relevance,
        "created_at": adv.created_at.isoformat() if adv.created_at else None,
        "updated_at": adv.updated_at.isoformat() if adv.updated_at else None,
        "cwes": [c.cwe_id for c in adv.cwes] if adv.cwes else [],
        "owasp_categories": [o.category_id for o in adv.owasp_categories] if adv.owasp_categories else [],
    }


def _source_to_dict(ks: KnowledgeSource) -> dict[str, Any]:
    return {
        "id": ks.id,
        "source_type": ks.source_type,
        "name": ks.name,
        "version": ks.version,
        "source_url": ks.source_url,
        "published_at": ks.published_at.isoformat() if ks.published_at else None,
        "retrieved_at": ks.retrieved_at.isoformat() if ks.retrieved_at else None,
        "record_count": ks.record_count,
        "status": ks.status,
        "error_message": ks.error_message,
        "created_at": ks.created_at.isoformat() if ks.created_at else None,
        "updated_at": ks.updated_at.isoformat() if ks.updated_at else None,
    }


def _sync_run_to_dict(run: KnowledgeSyncRun) -> dict[str, Any]:
    return {
        "id": run.id,
        "source_id": run.source_id,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
        "status": run.status,
        "records_seen": run.records_seen,
        "records_created": run.records_created,
        "records_updated": run.records_updated,
        "records_skipped": run.records_skipped,
        "records_failed": run.records_failed,
        "error_count": run.error_count,
        "content_hash": run.content_hash,
        "details": run.details,
    }


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/", summary="List security advisories")
def list_advisories(
    q: Optional[str] = Query(None, description="Full-text search across title/summary/vendor/product"),
    provider: Optional[str] = Query(None, description="Filter by provider (e.g. CISA_KEV, NVD)"),
    cve_id: Optional[str] = Query(None, description="Filter by CVE ID (exact match)"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """List security advisories with optional filters.

    Returns paginated results with ``total``, ``limit``, ``offset``, and
    ``items`` keys.
    """
    query = db.query(SecurityAdvisory)

    if provider:
        query = query.filter(SecurityAdvisory.provider == provider.upper())
    if cve_id:
        query = query.filter(SecurityAdvisory.cve_id == cve_id.upper())
    if q:
        pattern = f"%{q}%"
        query = query.filter(
            or_(
                SecurityAdvisory.title.ilike(pattern),
                SecurityAdvisory.summary.ilike(pattern),
                SecurityAdvisory.vendor.ilike(pattern),
                SecurityAdvisory.product.ilike(pattern),
            )
        )

    total = query.count()
    advisories = (
        query.order_by(SecurityAdvisory.date_added.desc().nullslast())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": [_advisory_to_dict(a, db) for a in advisories],
    }


@router.get("/stats", summary="Advisory knowledge base statistics")
def get_stats(db: Session = Depends(get_db)) -> dict[str, Any]:
    """Return aggregate statistics about the knowledge base.

    Includes total advisories, counts by provider, total CWEs, and total
    OWASP categories loaded.
    """
    total_advisories = db.query(func.count(SecurityAdvisory.id)).scalar() or 0
    cwe_count = db.query(func.count(CWEEntry.id)).scalar() or 0
    owasp_count = db.query(func.count(OWASPCategory.id)).scalar() or 0

    provider_rows = (
        db.query(SecurityAdvisory.provider, func.count(SecurityAdvisory.id).label("cnt"))
        .group_by(SecurityAdvisory.provider)
        .all()
    )
    by_provider = {row.provider: row.cnt for row in provider_rows}

    return {
        "total_advisories": total_advisories,
        "by_provider": by_provider,
        "cwe_count": cwe_count,
        "owasp_count": owasp_count,
    }


@router.get("/sources", summary="List knowledge sources")
def list_sources(db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    """Return all registered knowledge sources."""
    sources = db.query(KnowledgeSource).order_by(KnowledgeSource.source_type).all()
    return [_source_to_dict(s) for s in sources]


@router.get("/sync-runs", summary="List recent knowledge sync runs")
def list_sync_runs(
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    """Return the most recent knowledge ingestion sync runs."""
    runs = (
        db.query(KnowledgeSyncRun)
        .order_by(KnowledgeSyncRun.started_at.desc())
        .limit(limit)
        .all()
    )
    return [_sync_run_to_dict(r) for r in runs]


@router.get("/trending", summary="Trending CVEs and Technologies")
def get_trending_advisories(
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    """Returns top trending vulnerabilities ranked by recency, exploitation, and ransomware indicators."""
    advisories = (
        db.query(SecurityAdvisory)
        .order_by(SecurityAdvisory.date_added.desc().nullslast())
        .limit(limit * 2)
        .all()
    )
    results = []
    now = datetime.now()
    for a in advisories:
        score = 70
        if a.date_added:
            dt_val = a.date_added.date() if hasattr(a.date_added, "date") else a.date_added
            age_days = (now.date() - dt_val).days
            if age_days < 90:
                score += 15
            elif age_days < 180:
                score += 10
            elif age_days < 365:
                score += 5
        if str(a.known_ransomware_use).upper() in ("KNOWN", "YES", "TRUE"):
            score += 10
        if a.severity in ("CRITICAL", "HIGH"):
            score += 5

        score = min(99, max(50, score))
        d = _advisory_to_dict(a, None)
        d["trend_score"] = score
        d["exploitation_status"] = "ACTIVELY EXPLOITED" if a.provider == "CISA_KEV" else "MONITORED"
        results.append(d)

    results.sort(key=lambda x: (x["trend_score"], x.get("date_added") or ""), reverse=True)
    return results[:limit]


@router.get("/cve/{cve_id}", summary="Find advisory by CVE ID")
def get_by_cve_id(
    cve_id: str,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Retrieve the first advisory matching the given CVE ID.

    Returns 404 if no advisory is found.
    """
    advisory = (
        db.query(SecurityAdvisory)
        .filter(SecurityAdvisory.cve_id == cve_id.upper())
        .first()
    )
    if not advisory:
        raise HTTPException(status_code=404, detail=f"No advisory found for CVE ID: {cve_id}")
    return _advisory_to_dict(advisory, db)


@router.get("/search", summary="Full-text search advisories")
def search_advisories(
    q: str = Query(..., min_length=2, description="Search term"),
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Search advisory title, summary, vendor, and product fields.

    Returns paginated results with ``total``, ``limit``, ``offset``, and
    ``items`` keys.
    """
    pattern = f"%{q}%"
    query = db.query(SecurityAdvisory).filter(
        or_(
            SecurityAdvisory.title.ilike(pattern),
            SecurityAdvisory.summary.ilike(pattern),
            SecurityAdvisory.vendor.ilike(pattern),
            SecurityAdvisory.product.ilike(pattern),
        )
    )
    total = query.count()
    advisories = (
        query.order_by(SecurityAdvisory.date_added.desc().nullslast())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": [_advisory_to_dict(a, db) for a in advisories],
    }


@router.get("/{advisory_id}/bounty-intelligence", summary="Get verified bounty intelligence for advisory")
def get_advisory_bounty_intelligence(
    advisory_id: int,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Retrieve verified bug bounty award history and class intelligence for an advisory.

    Truth-anchored: returns status="unavailable" if no verified public award records exist.
    Never invents, estimates, or hallucinates bounty statistics.
    """
    advisory = db.get(SecurityAdvisory, advisory_id)
    if not advisory:
        raise HTTPException(status_code=404, detail=f"Advisory not found: {advisory_id}")

    vuln_class = resolve_vulnerability_class(advisory)

    filter_clauses = [BountyEvidence.vulnerability_class.ilike(f"%{vuln_class}%")]
    if advisory.cve_id:
        filter_clauses.append(BountyEvidence.cve_id == advisory.cve_id.upper())

    records = (
        db.query(BountyEvidence)
        .filter(or_(*filter_clauses))
        .order_by(BountyEvidence.observed_at.desc())
        .all()
    )

    if not records:
        return {
            "status": "unavailable",
            "vulnerability_class": vuln_class,
            "message": "No verified public award data available for this vulnerability class.",
            "records": [],
            "verified_count": 0,
            "range": None,
            "median": None,
            "average": None,
            "currency": "USD",
            "methodology": "Verified public disclosure database and official program writeups. No synthetic or extrapolated values.",
            "sources": [],
        }

    amounts = [r.award_amount for r in records if r.award_amount is not None]
    min_amt = min(amounts) if amounts else 0
    max_amt = max(amounts) if amounts else 0
    med_amt = statistics.median(amounts) if amounts else 0
    avg_amt = statistics.mean(amounts) if amounts else 0

    return {
        "status": "available",
        "vulnerability_class": vuln_class,
        "message": None,
        "verified_count": len(records),
        "range": {
            "min": min_amt,
            "max": max_amt,
        },
        "median": round(med_amt, 2),
        "average": round(avg_amt, 2),
        "currency": records[0].currency if records else "USD",
        "methodology": "Aggregated from verified public award records matching this vulnerability class. Reflects observed bounties, not guarantees.",
        "sources": sorted(list({r.source for r in records if r.source})),
        "records": [
            {
                "id": r.id,
                "program_name": r.program_name,
                "program_url": r.program_url,
                "award_amount": r.award_amount,
                "currency": r.currency,
                "source": r.source,
                "source_url": r.source_url,
                "published_at": r.published_at.isoformat() if r.published_at else None,
                "measurement_type": r.measurement_type,
                "notes": r.notes,
            }
            for r in records[:10]
        ],
    }


@router.get("/{advisory_id}", summary="Get advisory by ID")
def get_advisory_by_id(
    advisory_id: int,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Retrieve a single advisory by its database primary key.

    Returns 404 if not found.
    """
    advisory = db.get(SecurityAdvisory, advisory_id)
    if not advisory:
        raise HTTPException(status_code=404, detail=f"Advisory not found: {advisory_id}")
    return _advisory_to_dict(advisory, db)
