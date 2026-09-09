"""Detected changes router."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Change, Target, User
from app.routers.deps import get_current_user
from app.schemas import ChangeStatusUpdate

router = APIRouter(prefix="/api/v1/changes", tags=["changes"])


@router.get("", response_model=list[dict])
@router.get("/", response_model=list[dict], include_in_schema=False)
def list_changes(
    limit: int = 50,
    offset: int = 0,
    target_id: int | None = None,
    category: str | None = None,
    priority: str | None = None,
    status: str | None = None,
    search: str | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    """List detected changes across authorized targets."""
    query = db.query(Change)
    if target_id is not None:
        query = query.filter_by(target_id=target_id)
    if category and category.upper() != "ALL":
        query = query.filter(Change.category == category)
    if priority and priority.upper() != "ALL":
        query = query.filter(getattr(Change, "priority") == priority.upper())
    if status and status.upper() != "ALL":
        query = query.filter(getattr(Change, "status") == status)
    if search:
        search_pattern = f"%{search.strip()}%"
        query = query.filter(
            (Change.summary.ilike(search_pattern))
            | (Change.source_url.ilike(search_pattern))
            | (Change.category.ilike(search_pattern))
        )
    changes = query.order_by(Change.detected_at.desc()).offset(offset).limit(limit).all()

    target_ids = {c.target_id for c in changes if c.target_id}
    targets = {t.id: t for t in db.query(Target).filter(Target.id.in_(target_ids)).all()} if target_ids else {}
    return [
        {
            "id": c.id,
            "target_id": c.target_id,
            "target_domain": targets.get(c.target_id).domain if targets.get(c.target_id) else None,
            "company_name": targets.get(c.target_id).company_name if targets.get(c.target_id) else None,
            "category": c.category,
            "confidence": c.confidence,
            "security_relevance": c.security_relevance,
            "priority": getattr(c, "priority", "MEDIUM"),
            "status": getattr(c, "status", "interesting"),
            "summary": c.summary,
            "source_url": c.source_url,
            "detected_at": c.detected_at.isoformat() if c.detected_at else None,
        }
        for c in changes
    ]


@router.get("/stats")
def get_changes_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Return aggregated telemetry and metrics for attack surface changes."""
    from sqlalchemy import func

    total = db.query(func.count(Change.id)).scalar() or 0
    critical_count = db.query(func.count(Change.id)).filter(Change.priority == "CRITICAL").scalar() or 0
    high_count = db.query(func.count(Change.id)).filter(Change.priority == "HIGH").scalar() or 0
    medium_count = db.query(func.count(Change.id)).filter(Change.priority == "MEDIUM").scalar() or 0
    low_count = db.query(func.count(Change.id)).filter(Change.priority == "LOW").scalar() or 0
    info_count = db.query(func.count(Change.id)).filter(Change.priority == "INFO").scalar() or 0
    investigating = db.query(func.count(Change.id)).filter(Change.status == "investigating").scalar() or 0
    resolved = db.query(func.count(Change.id)).filter(Change.status == "resolved").scalar() or 0
    ignored = db.query(func.count(Change.id)).filter(Change.status == "ignored").scalar() or 0
    interesting = db.query(func.count(Change.id)).filter(Change.status == "interesting").scalar() or 0
    unique_targets = db.query(func.count(func.distinct(Change.target_id))).scalar() or 0

    categories = dict(
        db.query(Change.category, func.count(Change.id))
        .group_by(Change.category)
        .all()
    )

    return {
        "total": total,
        "critical": critical_count,
        "high": high_count,
        "medium": medium_count,
        "low": low_count,
        "info": info_count,
        "critical_high": critical_count + high_count,
        "investigating": investigating,
        "resolved": resolved,
        "ignored": ignored,
        "interesting": interesting,
        "unique_targets": unique_targets,
        "categories": categories,
    }


@router.get("/{change_id}")
def get_change(
    change_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Get change detail with associated evidence records."""
    change = db.get(Change, change_id)
    if not change:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Change not found")

    target = db.get(Target, change.target_id)
    target_domain = target.domain if target else None
    company_name = target.company_name if target else None

    return {
        "id": change.id,
        "target_id": change.target_id,
        "target_domain": target_domain,
        "company_name": company_name,
        "snapshot_id": change.snapshot_id,
        "fingerprint": change.fingerprint,
        "category": change.category,
        "confidence": change.confidence,
        "security_relevance": change.security_relevance,
        "priority": getattr(change, "priority", "MEDIUM"),
        "status": getattr(change, "status", "interesting"),
        "summary": change.summary,
        "researcher_note": change.researcher_note,
        "source_url": change.source_url,
        "detected_at": change.detected_at,
        "score_factors": change.score_factors,
        "evidence": [
            {
                "id": e.id,
                "state": e.state,
                "observation_id": e.observation_id,
                "payload": e.payload,
            }
            for e in change.evidence
        ],
    }


@router.post("/{change_id}/status")
def update_change_status(
    change_id: int,
    body: ChangeStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Update research status for a change (interesting/investigating/ignored/resolved)."""
    change = db.get(Change, change_id)
    if not change:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Change not found")

    change.status = body.status
    db.commit()
    db.refresh(change)
    return {
        "id": change.id,
        "status": change.status,
        "message": f"Research status updated to '{change.status}'",
    }
