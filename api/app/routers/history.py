"""Historical Intelligence API Routers.

Exposes endpoints for historical reconstruction, temporal coverage,
releases, feature evolution, asset lifecycle, security history,
and date-to-date attack surface comparisons.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.db import get_db
from app.models.company import Company
from app.models.asset import Asset
from app.models.product import Product
from app.models.feature import Feature
from app.models.api_surface import ApiSurface
from app.models.security import SecurityEvent
from app.models.security_program import SecurityProgram, ProgramScopeRule
from app.models.timeline import TimelineEvent
from app.models.history import HistoricalCoverage, HistoricalRelease
from app.services.historical_reconstruction_service import HistoricalReconstructionService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/companies", tags=["history"])


@router.get("/{company_id}/history")
def get_company_history_overview(
    company_id: int,
    time_range: str = Query("all", alias="range", description="1m, 3m, 6m, 1y, 3y, or all"),
    category: Optional[str] = Query(None, description="APIS, AUTH, FEATURES, ASSETS, TECHNOLOGIES, SECURITY"),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """Retrieves unified historical timeline, weakness fingerprint, and coverage for a company."""
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    coverage = (
        db.query(HistoricalCoverage)
        .filter(HistoricalCoverage.company_id == company.id)
        .first()
    )
    fingerprint = HistoricalReconstructionService.build_weakness_fingerprint(db, company.id)

    # Timeline events query
    query = db.query(TimelineEvent).filter(TimelineEvent.company_id == company.id)

    # Apply time range filter
    now = datetime.now(timezone.utc)
    if time_range == "1m":
        query = query.filter(TimelineEvent.observed_at >= now - timedelta(days=30))
    elif time_range == "3m":
        query = query.filter(TimelineEvent.observed_at >= now - timedelta(days=90))
    elif time_range == "6m":
        query = query.filter(TimelineEvent.observed_at >= now - timedelta(days=180))
    elif time_range == "1y":
        query = query.filter(TimelineEvent.observed_at >= now - timedelta(days=365))
    elif time_range == "3y":
        query = query.filter(TimelineEvent.observed_at >= now - timedelta(days=365 * 3))

    if category:
        cat_upper = category.upper()
        if cat_upper == "APIS":
            query = query.filter(or_(TimelineEvent.event_type.ilike("%api%"), TimelineEvent.title.ilike("%api%")))
        elif cat_upper == "AUTH":
            query = query.filter(or_(TimelineEvent.title.ilike("%auth%"), TimelineEvent.title.ilike("%login%"), TimelineEvent.title.ilike("%sso%")))
        elif cat_upper == "SECURITY":
            query = query.filter(TimelineEvent.event_type.ilike("%security%"))
        elif cat_upper == "FEATURES":
            query = query.filter(TimelineEvent.event_type.ilike("%feature%"))

    events = query.order_by(TimelineEvent.observed_at.desc()).limit(limit).all()

    return {
        "company": {
            "id": company.id,
            "name": company.name,
            "canonical_domain": company.canonical_domain,
        },
        "coverage": {
            "coverage_start": coverage.coverage_start if coverage else None,
            "coverage_end": coverage.coverage_end if coverage else None,
            "confidence": coverage.confidence if coverage else 0.0,
            "sources_count": coverage.sources_count if coverage else 0,
            "confirmed_events_count": coverage.confirmed_events_count if coverage else 0,
            "estimated_events_count": coverage.estimated_events_count if coverage else 0,
            "notes": coverage.notes if coverage else "Historical intelligence reconstructed from publicly available evidence.",
        },
        "weakness_fingerprint": fingerprint,
        "timeline_events": [
            {
                "id": e.id,
                "event_type": e.event_type,
                "title": e.title,
                "summary": e.summary,
                "source": e.source,
                "source_url": e.source_url,
                "provenance_category": e.provenance_category,
                "temporal_category": e.temporal_category,
                "quality_badge": e.quality_badge,
                "observed_at": e.observed_at,
                "published_at": e.published_at,
                "effective_at": e.effective_at,
                "confidence": e.confidence,
                "priority": e.priority,
            }
            for e in events
        ],
    }


@router.get("/{company_id}/history/coverage")
def get_company_history_coverage(company_id: int, db: Session = Depends(get_db)):
    """Retrieves explicit historical coverage boundaries and evidence provenance."""
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    coverage = (
        db.query(HistoricalCoverage)
        .filter(HistoricalCoverage.company_id == company.id)
        .first()
    )
    if not coverage:
        coverage = HistoricalReconstructionService.update_historical_coverage(db, company)

    return {
        "company_id": company.id,
        "canonical_domain": company.canonical_domain,
        "coverage_start": coverage.coverage_start,
        "coverage_end": coverage.coverage_end,
        "confidence": coverage.confidence,
        "sources_count": coverage.sources_count,
        "confirmed_events_count": coverage.confirmed_events_count,
        "estimated_events_count": coverage.estimated_events_count,
        "partial_periods": coverage.partial_periods,
        "last_synced_at": coverage.last_synced_at,
        "disclaimer": "Historical intelligence reconstructed from publicly available evidence. Visibility may be partial.",
    }


@router.get("/{company_id}/history/releases")
def get_company_history_releases(
    company_id: int,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """Lists historical releases, tags, and semantic extracted artifacts."""
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    releases = (
        db.query(HistoricalRelease)
        .filter(HistoricalRelease.company_id == company.id)
        .order_by(HistoricalRelease.published_at.desc())
        .limit(limit)
        .all()
    )

    return [
        {
            "id": r.id,
            "version": r.version,
            "tag": r.tag,
            "title": r.title,
            "body": r.body,
            "published_at": r.published_at,
            "source_url": r.source_url,
            "confidence": r.confidence,
            "semantic_changes": r.semantic_changes,
        }
        for r in releases
    ]


@router.get("/{company_id}/history/features")
def get_company_feature_history(company_id: int, db: Session = Depends(get_db)):
    """Returns chronologically ordered feature introductions with first_seen dates."""
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    features = (
        db.query(Feature)
        .filter(Feature.company_id == company.id)
        .order_by(Feature.first_observed.asc())
        .all()
    )

    return [
        {
            "id": f.id,
            "name": f.name,
            "category": f.category,
            "description": f.description,
            "first_observed": f.first_observed,
            "last_observed": f.last_observed,
            "confidence": f.confidence,
            "product_id": f.product_id,
        }
        for f in features
    ]


@router.get("/{company_id}/history/assets")
def get_company_asset_history(company_id: int, db: Session = Depends(get_db)):
    """Returns historical assets with lifecycle status (FIRST_SEEN, ACTIVE, REMOVED, REAPPEARED)."""
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    assets = (
        db.query(Asset)
        .filter(Asset.company_id == company.id)
        .order_by(Asset.first_observed.asc())
        .all()
    )

    return [
        {
            "id": a.id,
            "hostname": a.normalized_hostname or a.name,
            "asset_type": a.asset_type,
            "scope_status": a.scope_status,
            "lifecycle_status": a.lifecycle_status,
            "first_observed": a.first_observed,
            "last_seen_at": a.last_seen_at,
            "confidence": a.confidence,
        }
        for a in assets
    ]


@router.get("/{company_id}/history/security")
def get_company_security_history_summary(company_id: int, db: Session = Depends(get_db)):
    """Returns normalized security events and weakness fingerprint."""
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    fingerprint = HistoricalReconstructionService.build_weakness_fingerprint(db, company.id)
    events = (
        db.query(SecurityEvent)
        .filter(SecurityEvent.company_id == company.id)
        .order_by(SecurityEvent.published.desc())
        .all()
    )

    return {
        "weakness_fingerprint": fingerprint,
        "security_events": [
            {
                "id": s.id,
                "cve_id": s.cve_id,
                "vulnerability_class": s.vulnerability_class,
                "severity": s.severity,
                "summary": s.summary,
                "published": s.published,
                "source": s.source,
                "source_url": s.source_url,
                "confidence": s.confidence,
            }
            for s in events
        ],
    }


@router.get("/{company_id}/history/compare")
def compare_company_history(
    company_id: int,
    from_date: str = Query(..., alias="from", description="ISO datetime for start date (e.g. 2025-01-01)"),
    to_date: str = Query(..., alias="to", description="ISO datetime for end date (e.g. 2026-09-01)"),
    db: Session = Depends(get_db),
):
    """Compares public attack surface states between two historical timestamps."""
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    try:
        dt_from = datetime.fromisoformat(from_date.replace("Z", "+00:00"))
        dt_to = datetime.fromisoformat(to_date.replace("Z", "+00:00"))
    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=f"Invalid ISO datetime format: {val_err}")

    if dt_from > dt_to:
        raise HTTPException(status_code=400, detail="'from' timestamp must precede 'to' timestamp")

    return HistoricalReconstructionService.compare_dates(db, company.id, dt_from, dt_to)


@router.post("/{company_id}/history/reconstruct", status_code=status.HTTP_202_ACCEPTED)
def trigger_historical_reconstruction(
    company_id: int,
    stage: int = Query(1, ge=1, le=3),
    db: Session = Depends(get_db),
):
    """Enqueues or runs staged historical intelligence reconstruction."""
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    try:
        from app.jobs.historical_reconstruction_job import reconstruct_company_history_job
        result = reconstruct_company_history_job(company.id, stage=stage, db=db)

        return {"status": "accepted", "result": result}
    except Exception as exc:
        logger.warning("Historical reconstruction error: %s", exc)
        return {"status": "error", "message": str(exc)}
