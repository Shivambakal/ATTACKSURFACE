"""Public Security Programs & Bug Bounty Registry API Router.

Provides searchable, filterable endpoints for public security programs,
bounty tables, scope rules, point-in-time snapshots, and scope change events.
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func, or_

from app.db import get_db
from app.models.company import Company
from app.models.security_program import (
    SecurityProgram,
    ProgramScopeRule,
    ProgramSnapshot,
    ProgramChangeEvent,
)
from app.routers.deps import get_optional_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/programs", tags=["programs"])


@router.get("/stats")
def get_programs_stats(db: Session = Depends(get_db)):
    """Returns platform-wide statistics for public bug bounty & security disclosure programs."""
    total_programs = db.query(SecurityProgram).count()
    bounty_programs = db.query(SecurityProgram).filter(SecurityProgram.offers_bounties.is_(True)).count()
    vdp_programs = total_programs - bounty_programs
    total_scope_rules = db.query(ProgramScopeRule).count()
    total_snapshots = db.query(ProgramSnapshot).count()
    total_change_events = db.query(ProgramChangeEvent).count()

    # Platform breakdown
    platform_counts_raw = (
        db.query(SecurityProgram.platform, func.count(SecurityProgram.id))
        .group_by(SecurityProgram.platform)
        .all()
    )
    platform_breakdown = {plat or "Unknown": cnt for plat, cnt in platform_counts_raw}

    # Canonical companies with at least one public program
    companies_with_programs = (
        db.query(func.count(func.distinct(SecurityProgram.company_id))).scalar() or 0
    )

    return {
        "total_programs": total_programs,
        "bounty_programs": bounty_programs,
        "vdp_programs": vdp_programs,
        "platform_breakdown": platform_breakdown,
        "total_scope_rules": total_scope_rules,
        "total_snapshots": total_snapshots,
        "total_change_events": total_change_events,
        "canonical_companies_with_programs": companies_with_programs,
    }


@router.get("")
def list_programs(
    q: Optional[str] = Query(None, description="Search by program name, handle, company name, or domain"),
    platform: Optional[str] = Query(None, description="Filter by platform (HackerOne, Bugcrowd, etc.)"),
    bounty_only: Optional[bool] = Query(None, description="Filter programs that offer financial bounties"),
    company_id: Optional[int] = Query(None, description="Filter by company ID"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """Lists public security programs with rich filtering, search, and company attribution."""
    query = (
        db.query(SecurityProgram, Company)
        .join(Company, SecurityProgram.company_id == Company.id)
    )

    if q:
        term = f"%{q.strip()}%"
        query = query.filter(
            or_(
                SecurityProgram.program_name.ilike(term),
                SecurityProgram.program_handle.ilike(term),
                Company.name.ilike(term),
                Company.canonical_domain.ilike(term),
            )
        )

    if platform:
        query = query.filter(SecurityProgram.platform.ilike(f"%{platform.strip()}%"))

    if bounty_only is True:
        query = query.filter(SecurityProgram.offers_bounties.is_(True))
    elif bounty_only is False:
        query = query.filter(SecurityProgram.offers_bounties.is_(False))

    if company_id is not None:
        query = query.filter(SecurityProgram.company_id == company_id)

    total = query.count()
    rows = query.order_by(Company.name.asc(), SecurityProgram.program_name.asc()).offset(offset).limit(limit).all()

    # Batch scope rules counts
    prog_ids = [sp.id for sp, _ in rows]
    rule_counts = {}
    if prog_ids:
        rule_counts = dict(
            db.query(ProgramScopeRule.security_program_id, func.count(ProgramScopeRule.id))
            .filter(ProgramScopeRule.security_program_id.in_(prog_ids))
            .group_by(ProgramScopeRule.security_program_id)
            .all()
        )

    items = []
    for sp, comp in rows:
        items.append({
            "id": sp.id,
            "company_id": comp.id,
            "company_name": comp.name,
            "company_domain": comp.canonical_domain,
            "company_website": comp.website_url,
            "platform": sp.platform,
            "program_name": sp.program_name or comp.name,
            "program_handle": sp.program_handle,
            "program_type": sp.program_type,
            "program_url": sp.program_url,
            "policy_url": sp.policy_url,
            "is_public": sp.is_public,
            "offers_bounties": sp.offers_bounties,
            "min_bounty": sp.min_bounty,
            "max_bounty": sp.max_bounty,
            "currency": sp.currency,
            "submission_state": sp.submission_state,
            "scope_summary": sp.scope_summary,
            "scope_rules_count": rule_counts.get(sp.id, 0),
            "discovered_at": sp.discovered_at,
            "last_verified_at": sp.last_verified_at,
        })

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": items,
    }


@router.get("/{program_id}")
def get_program_detail(program_id: int, db: Session = Depends(get_db)):
    """Retrieves full program details including in-scope rules, snapshots, and change events."""
    sp = db.query(SecurityProgram).filter(SecurityProgram.id == program_id).first()
    if not sp:
        raise HTTPException(status_code=404, detail="Security program not found")

    comp = db.query(Company).filter(Company.id == sp.company_id).first()

    rules = (
        db.query(ProgramScopeRule)
        .filter(ProgramScopeRule.security_program_id == sp.id)
        .order_by(ProgramScopeRule.id.asc())
        .limit(200)
        .all()
    )

    snapshots = (
        db.query(ProgramSnapshot)
        .filter(ProgramSnapshot.security_program_id == sp.id)
        .order_by(ProgramSnapshot.created_at.desc())
        .limit(5)
        .all()
    )

    change_events = (
        db.query(ProgramChangeEvent)
        .filter(ProgramChangeEvent.security_program_id == sp.id)
        .order_by(ProgramChangeEvent.created_at.desc())
        .limit(10)
        .all()
    )

    return {
        "id": sp.id,
        "company": {
            "id": comp.id if comp else None,
            "name": comp.name if comp else "Unknown Organization",
            "canonical_domain": comp.canonical_domain if comp else "",
            "website_url": comp.website_url if comp else None,
            "industry": comp.industry if comp else None,
        },
        "platform": sp.platform,
        "program_name": sp.program_name,
        "program_handle": sp.program_handle,
        "program_type": sp.program_type,
        "program_url": sp.program_url,
        "policy_url": sp.policy_url,
        "is_public": sp.is_public,
        "offers_bounties": sp.offers_bounties,
        "min_bounty": sp.min_bounty,
        "max_bounty": sp.max_bounty,
        "currency": sp.currency,
        "submission_state": sp.submission_state,
        "scope_summary": sp.scope_summary,
        "discovered_at": sp.discovered_at,
        "last_verified_at": sp.last_verified_at,
        "scope_rules": [
            {
                "id": r.id,
                "pattern": r.pattern,
                "asset_type": r.asset_type,
                "inclusion_type": r.inclusion_type,
                "confidence": r.confidence,
                "source_url": r.source_url,
                "last_verified_at": r.last_verified_at,
            }
            for r in rules
        ],
        "snapshots": [
            {
                "id": s.id,
                "snapshot_hash": s.snapshot_hash,
                "scope_count": s.scope_count,
                "scope_summary": s.scope_summary,
                "bounty_table": s.bounty_table,
                "created_at": s.created_at,
            }
            for s in snapshots
        ],
        "change_events": [
            {
                "id": ce.id,
                "change_type": ce.change_type,
                "summary": ce.summary,
                "diff_details": ce.diff_details,
                "created_at": ce.created_at,
            }
            for ce in change_events
        ],
    }


@router.post("/sync")
def trigger_programs_sync(background_tasks: BackgroundTasks, user=Depends(get_optional_user)):
    """Triggers an asynchronous background synchronization of public bug-bounty registries."""
    from app.sync_programs import run_sync

    background_tasks.add_task(run_sync)
    return {
        "status": "initiated",
        "message": "Public security programs background sync has been triggered.",
    }
