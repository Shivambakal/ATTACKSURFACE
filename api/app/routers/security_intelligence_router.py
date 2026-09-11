"""Security Intelligence API Router.

Provides endpoints for querying AI-discovered, search-grounded security news,
CVE disclosures, zero-days, exploit alerts, and triggering on-demand collections.

Prefix: /api/v1/security-intelligence
"""
from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Company, Product, SecurityAdvisory, SecurityIntelligenceEvent, Technology
from app.services.security_intelligence_collector import SecurityIntelligenceCollector

router = APIRouter(prefix="/api/v1/security-intelligence", tags=["security-intelligence"])


def _event_to_dict(event: SecurityIntelligenceEvent) -> dict[str, Any]:
    """Serialize SecurityIntelligenceEvent into client-friendly dictionary."""
    return {
        "id": event.id,
        "title": event.title,
        "summary": event.summary,
        "event_type": event.event_type,
        "published_at": event.published_at.isoformat() if event.published_at else None,
        "updated_at": event.updated_at.isoformat() if event.updated_at else None,
        "source_url": event.source_url,
        "source_name": event.source_name,
        "additional_sources": event.additional_sources or [],
        "cve_ids": event.cve_ids or [],
        "cwe_ids": event.cwe_ids or [],
        "affected_products": event.affected_products or [],
        "affected_companies": event.affected_companies or [],
        "severity": event.severity,
        "actively_exploited": event.actively_exploited,
        "known_exploitation_evidence": event.known_exploitation_evidence,
        "security_relevance": event.security_relevance,
        "confidence": event.confidence,
        "fingerprint": event.fingerprint,
        "severity_score": event.severity_score,
        "freshness_score": event.freshness_score,
        "exploitation_score": event.exploitation_score,
        "relevance_score": event.relevance_score,
        "priority_score": event.priority_score,
        "priority": event.priority,
        "grounding_metadata": event.grounding_metadata or {},
        "correlated_company_ids": event.correlated_company_ids or [],
        "correlated_product_ids": event.correlated_product_ids or [],
        "correlated_technology_ids": event.correlated_technology_ids or [],
        "correlated_advisory_ids": event.correlated_advisory_ids or [],
        "created_at": event.created_at.isoformat() if event.created_at else None,
    }


class CollectNowRequest(BaseModel):
    target_focus: Optional[str] = Field(None, description="Optional entity or technology focus")
    limit: int = Field(default=15, ge=1, le=50, description="Max items to collect")


@router.get("")
@router.get("/")
def list_security_intelligence_events(
    severity: Optional[str] = Query(None, description="Filter by severity (CRITICAL, HIGH, etc.)"),
    actively_exploited: Optional[bool] = Query(None, description="Filter by active exploitation status"),
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    priority: Optional[str] = Query(None, description="Filter by priority (CRITICAL, HIGH, etc.)"),
    company_id: Optional[int] = Query(None, description="Filter by correlated company ID"),
    q: Optional[str] = Query(None, description="Search term in title, summary, CVE or product"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """List paginated security intelligence events with multi-criteria filtering."""
    query = select(SecurityIntelligenceEvent)

    if severity:
        query = query.where(SecurityIntelligenceEvent.severity == severity.upper())

    if actively_exploited is not None:
        query = query.where(SecurityIntelligenceEvent.actively_exploited.is_(actively_exploited))

    if event_type:
        query = query.where(SecurityIntelligenceEvent.event_type == event_type.upper())

    if priority:
        query = query.where(SecurityIntelligenceEvent.priority == priority.upper())

    if company_id is not None:
        # Check if company_id is present in JSON array
        query = query.where(
            SecurityIntelligenceEvent.correlated_company_ids.contains([company_id])
        )

    if q:
        pattern = f"%{q.strip()}%"
        query = query.where(
            or_(
                SecurityIntelligenceEvent.title.ilike(pattern),
                SecurityIntelligenceEvent.summary.ilike(pattern),
                SecurityIntelligenceEvent.source_name.ilike(pattern),
            )
        )

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = db.execute(count_query).scalar_one()

    # Sort by priority score DESC, published_at DESC
    query = query.order_by(
        SecurityIntelligenceEvent.priority_score.desc(),
        SecurityIntelligenceEvent.published_at.desc(),
    ).offset(offset).limit(limit)

    events = db.execute(query).scalars().all()

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": [_event_to_dict(e) for e in events],
    }


@router.get("/latest")
def get_latest_events(
    limit: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    """Retrieve the most recently published security intelligence events."""
    query = (
        select(SecurityIntelligenceEvent)
        .order_by(SecurityIntelligenceEvent.published_at.desc())
        .limit(limit)
    )
    events = db.execute(query).scalars().all()
    return [_event_to_dict(e) for e in events]


@router.get("/high-priority")
def get_high_priority_events(
    limit: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    """Retrieve items requiring immediate researcher attention (CRITICAL/HIGH or Actively Exploited)."""
    query = (
        select(SecurityIntelligenceEvent)
        .where(
            or_(
                SecurityIntelligenceEvent.priority.in_(["CRITICAL", "HIGH"]),
                SecurityIntelligenceEvent.actively_exploited.is_(True),
            )
        )
        .order_by(
            SecurityIntelligenceEvent.priority_score.desc(),
            SecurityIntelligenceEvent.published_at.desc(),
        )
        .limit(limit)
    )
    events = db.execute(query).scalars().all()
    return [_event_to_dict(e) for e in events]


@router.get("/stats")
def get_security_intelligence_stats(
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Retrieve aggregate telemetry and threat statistics."""
    total = db.execute(select(func.count(SecurityIntelligenceEvent.id))).scalar_one() or 0
    actively_exploited = (
        db.execute(
            select(func.count(SecurityIntelligenceEvent.id)).where(
                SecurityIntelligenceEvent.actively_exploited.is_(True)
            )
        ).scalar_one()
        or 0
    )

    # By severity
    sev_rows = db.execute(
        select(SecurityIntelligenceEvent.severity, func.count(SecurityIntelligenceEvent.id))
        .group_by(SecurityIntelligenceEvent.severity)
    ).all()
    by_severity = {row[0]: row[1] for row in sev_rows}

    # By priority
    pri_rows = db.execute(
        select(SecurityIntelligenceEvent.priority, func.count(SecurityIntelligenceEvent.id))
        .group_by(SecurityIntelligenceEvent.priority)
    ).all()
    by_priority = {row[0]: row[1] for row in pri_rows}

    # By event type
    type_rows = db.execute(
        select(SecurityIntelligenceEvent.event_type, func.count(SecurityIntelligenceEvent.id))
        .group_by(SecurityIntelligenceEvent.event_type)
    ).all()
    by_event_type = {row[0]: row[1] for row in type_rows}

    return {
        "total_events": total,
        "actively_exploited_count": actively_exploited,
        "by_severity": by_severity,
        "by_priority": by_priority,
        "by_event_type": by_event_type,
    }


@router.post("/collect-now")
async def trigger_collection_now(
    payload: Optional[CollectNowRequest] = None,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Trigger an on-demand AI search-grounded intelligence collection cycle."""
    target_focus = payload.target_focus if payload else None
    limit = payload.limit if payload else 15

    collector = SecurityIntelligenceCollector()
    if not collector.is_configured():
        raise HTTPException(
            status_code=503,
            detail="Gemini AI is not configured. GEMINI_API_KEY must be set.",
        )

    events = await collector.collect(db, target_focus=target_focus, max_items=limit)

    return {
        "status": "success",
        "collected_count": len(events),
        "events": [_event_to_dict(e) for e in events],
    }


@router.get("/feed")
def get_security_intelligence_feed(
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Retrieve security intelligence feed items."""
    query = (
        select(SecurityIntelligenceEvent)
        .order_by(
            SecurityIntelligenceEvent.priority_score.desc(),
            SecurityIntelligenceEvent.published_at.desc(),
        )
        .limit(limit)
    )
    events = db.execute(query).scalars().all()
    return {
        "total": len(events),
        "items": [_event_to_dict(e) for e in events],
    }


@router.get("/{event_id}")
def get_single_event(
    event_id: int,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Retrieve full details for a single security intelligence event."""
    event = db.get(SecurityIntelligenceEvent, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Security intelligence event not found.")

    res = _event_to_dict(event)

    # Hydrate correlated entities for rich UI presentation
    if event.correlated_company_ids:
        companies = db.execute(
            select(Company.id, Company.name, Company.domain).where(
                Company.id.in_(event.correlated_company_ids)
            )
        ).all()
        res["correlated_companies"] = [
            {"id": c[0], "name": c[1], "domain": c[2]} for c in companies
        ]
    else:
        res["correlated_companies"] = []

    if event.correlated_product_ids:
        products = db.execute(
            select(Product.id, Product.name).where(Product.id.in_(event.correlated_product_ids))
        ).all()
        res["correlated_products"] = [{"id": p[0], "name": p[1]} for p in products]
    else:
        res["correlated_products"] = []

    if event.correlated_technology_ids:
        techs = db.execute(
            select(Technology.id, Technology.name).where(
                Technology.id.in_(event.correlated_technology_ids)
            )
        ).all()
        res["correlated_technologies"] = [{"id": t[0], "name": t[1]} for t in techs]
    else:
        res["correlated_technologies"] = []

    if event.correlated_advisory_ids:
        advisories = db.execute(
            select(SecurityAdvisory.id, SecurityAdvisory.cve_id, SecurityAdvisory.title).where(
                SecurityAdvisory.id.in_(event.correlated_advisory_ids)
            )
        ).all()
        res["correlated_advisories"] = [
            {"id": a[0], "cve_id": a[1], "title": a[2]} for a in advisories
        ]
    else:
        res["correlated_advisories"] = []

    return res
