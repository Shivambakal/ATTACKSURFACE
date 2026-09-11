"""Research Signals API router.

Exposes high-value research leads, change clusters, and researcher feedback loops.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import select, desc

from app.db import get_db
from app.models import (
    User,
    Target,
    ResearchSignal,
    ResearchSignalFeedback,
    ChangeCluster,
    SignalStatus,
    FeedbackType,
)
from app.models.base import utcnow
from .deps import get_current_user

router = APIRouter(tags=["signals"])


# ── Pydantic Request / Response Schemas ──────────────────────────────
class SignalFeedbackCreate(BaseModel):
    feedback: str
    reason: str | None = None


class SignalStatusUpdate(BaseModel):
    status: str


class ResearchSignalOut(BaseModel):
    id: int
    company_id: int | None = None
    target_id: int | None = None
    product_id: int | None = None
    asset_id: int | None = None
    change_id: int | None = None
    cluster_id: int | None = None
    title: str
    signal_type: str
    summary: str
    why_it_matters: str
    recommended_research_area: str | None = None
    relevance_score: int = 50
    confidence_score: int = 70
    security_context_score: int = 50
    priority: str = "MEDIUM"
    status: str = "new"
    security_context: dict[str, Any] | None = None
    historical_context: dict[str, Any] | None = None
    affected_assets: list[str] | None = None
    evidence_ids: list[str] | None = None
    source_count: int = 1
    created_at: datetime
    updated_at: datetime | None = None

    class Config:
        from_attributes = True


class ChangeClusterOut(BaseModel):
    id: int
    company_id: int | None = None
    target_id: int | None = None
    title: str
    summary: str
    primary_category: str
    affected_urls: list[str] | None = None
    source_count: int = 1
    confidence: float = 0.8
    relevance_score: int = 50
    priority: str = "MEDIUM"
    created_at: datetime

    class Config:
        from_attributes = True


# ── Target Signal Endpoints ──────────────────────────────────────────
@router.get("/api/v1/targets/{target_id}/signals", response_model=list[ResearchSignalOut])
def get_target_signals(
    target_id: int,
    priority: str | None = Query(None),
    signal_type: str | None = Query(None),
    status: str | None = Query(None),
    min_relevance: int = Query(0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve prioritized research signals for an authorized target."""
    target = db.get(Target, target_id)
    if not target:
        raise HTTPException(status_code=404, detail="Target not found.")

    query = select(ResearchSignal).where(ResearchSignal.target_id == target_id)

    if priority:
        query = query.where(ResearchSignal.priority == priority.upper())
    if signal_type:
        query = query.where(ResearchSignal.signal_type == signal_type)
    if status:
        query = query.where(ResearchSignal.status == status.lower())
    if min_relevance > 0:
        query = query.where(ResearchSignal.relevance_score >= min_relevance)

    query = query.order_by(desc(ResearchSignal.relevance_score), desc(ResearchSignal.created_at))
    return db.scalars(query).all()


@router.get("/api/v1/targets/{target_id}/signals/top", response_model=list[ResearchSignalOut])
def get_top_signals(
    target_id: int,
    limit: int = Query(3, ge=1, le=10),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve top research recommendations for immediate investigation."""
    target = db.get(Target, target_id)
    if not target:
        raise HTTPException(status_code=404, detail="Target not found.")

    query = (
        select(ResearchSignal)
        .where(ResearchSignal.target_id == target_id)
        .where(ResearchSignal.status.in_(["new", "interesting", "investigating"]))
        .order_by(desc(ResearchSignal.relevance_score), desc(ResearchSignal.created_at))
        .limit(limit)
    )
    return db.scalars(query).all()


@router.get("/api/v1/targets/{target_id}/signals/since-last-visit", response_model=list[ResearchSignalOut])
def get_signals_since_last_visit(
    target_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve high-value research signals detected since user's last target visit."""
    target = db.get(Target, target_id)
    if not target:
        raise HTTPException(status_code=404, detail="Target not found.")

    since_time = target.last_visited_at
    query = select(ResearchSignal).where(ResearchSignal.target_id == target_id)
    if since_time:
        query = query.where(ResearchSignal.created_at >= since_time)

    query = query.order_by(desc(ResearchSignal.relevance_score), desc(ResearchSignal.created_at))
    return db.scalars(query).all()


@router.get("/api/v1/targets/{target_id}/clusters", response_model=list[ChangeClusterOut])
def get_target_clusters(
    target_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve clustered product release events for a target."""
    target = db.get(Target, target_id)
    if not target:
        raise HTTPException(status_code=404, detail="Target not found.")

    query = (
        select(ChangeCluster)
        .where(ChangeCluster.target_id == target_id)
        .order_by(desc(ChangeCluster.created_at))
    )
    return db.scalars(query).all()


# ── Global Signal Endpoints ──────────────────────────────────────────
@router.get("/api/v1/signals/top", response_model=list[ResearchSignalOut])
def get_global_top_signals(
    limit: int = Query(6, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve top prioritized research recommendations across all authorized targets."""
    query = (
        select(ResearchSignal)
        .where(ResearchSignal.status.in_(["new", "interesting", "investigating"]))
        .order_by(desc(ResearchSignal.relevance_score), desc(ResearchSignal.created_at))
        .limit(limit)
    )
    return db.scalars(query).all()


@router.get("/api/v1/signals", response_model=list[ResearchSignalOut])
def list_signals(
    limit: int = Query(50, ge=1, le=200),
    priority: str | None = Query(None),
    status: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List research signals across all targets."""
    query = select(ResearchSignal)
    if priority:
        query = query.where(ResearchSignal.priority == priority.upper())
    if status:
        query = query.where(ResearchSignal.status == status.lower())
    query = query.order_by(desc(ResearchSignal.relevance_score), desc(ResearchSignal.created_at)).limit(limit)
    return db.scalars(query).all()


# ── Individual Signal Endpoints ──────────────────────────────────────
@router.get("/api/v1/signals/{signal_id}", response_model=ResearchSignalOut)
def get_signal_detail(
    signal_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve full forensic detail for a research signal."""
    sig = db.get(ResearchSignal, signal_id)
    if not sig:
        raise HTTPException(status_code=404, detail="Research signal not found.")

    target = db.get(Target, sig.target_id)
    if not target:
        raise HTTPException(status_code=403, detail="Unauthorized access to signal.")

    return sig


@router.post("/api/v1/signals/{signal_id}/status", response_model=ResearchSignalOut)
def update_signal_status(
    signal_id: int,
    payload: SignalStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update research status (investigating, saved, ignored, resolved)."""
    sig = db.get(ResearchSignal, signal_id)
    if not sig:
        raise HTTPException(status_code=404, detail="Research signal not found.")

    target = db.get(Target, sig.target_id)
    if not target:
        raise HTTPException(status_code=403, detail="Unauthorized.")

    sig.status = payload.status.lower()
    sig.updated_at = utcnow()
    db.commit()
    db.refresh(sig)
    return sig


@router.post("/api/v1/signals/{signal_id}/feedback")
def submit_signal_feedback(
    signal_id: int,
    payload: SignalFeedbackCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Submit researcher feedback to train ranking and filter false positives."""
    sig = db.get(ResearchSignal, signal_id)
    if not sig:
        raise HTTPException(status_code=404, detail="Research signal not found.")

    fb = ResearchSignalFeedback(
        signal_id=sig.id,
        user_id=current_user.id,
        feedback=payload.feedback.upper(),
        reason=payload.reason,
        created_at=utcnow(),
    )
    db.add(fb)

    # If marked FALSE_POSITIVE, NOT_RELEVANT, or NOT_USEFUL, auto-update signal status to ignored
    norm_feedback = payload.feedback.upper()
    if norm_feedback in ("FALSE_POSITIVE", "NOT_RELEVANT", "NOT_USEFUL", "NOT_IN_SCOPE"):
        sig.status = SignalStatus.IGNORED.value

    db.commit()
    return {"status": "success", "message": "Feedback recorded successfully."}


@router.get("/api/v1/targets/{target_id}/signals/metrics")
def get_signal_quality_metrics(
    target_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Calculates real-world signal quality and feedback precision metrics for a target."""
    target = db.get(Target, target_id)
    if not target:
        raise HTTPException(status_code=404, detail="Target not found.")

    signals = db.scalars(select(ResearchSignal).where(ResearchSignal.target_id == target_id)).all()
    total_signals = len(signals)

    if total_signals == 0:
        return {
            "signals_generated": 0,
            "signals_opened": 0,
            "signals_dismissed": 0,
            "false_positive_rate": 0.0,
            "duplicate_rate": 0.0,
            "investigation_rate": 0.0,
            "high_priority_precision": 0.0,
        }

    signal_ids = [s.id for s in signals]
    feedbacks = db.scalars(
        select(ResearchSignalFeedback).where(ResearchSignalFeedback.signal_id.in_(signal_ids))
    ).all()

    opened_count = sum(1 for s in signals if s.status != SignalStatus.NEW.value)
    dismissed_count = sum(1 for s in signals if s.status == SignalStatus.IGNORED.value)
    investigating_count = sum(1 for s in signals if s.status in (SignalStatus.INVESTIGATING.value, SignalStatus.SAVED.value))

    fp_count = sum(1 for f in feedbacks if f.feedback == "FALSE_POSITIVE")
    dup_count = sum(1 for f in feedbacks if f.feedback == "DUPLICATE")
    useful_count = sum(1 for f in feedbacks if f.feedback in ("USEFUL", "INTERESTING"))

    high_pri_signals = [s for s in signals if s.priority in ("CRITICAL", "HIGH")]
    high_pri_useful = 0
    if high_pri_signals:
        high_pri_ids = {s.id for s in high_pri_signals}
        high_pri_useful = sum(1 for f in feedbacks if f.signal_id in high_pri_ids and f.feedback in ("USEFUL", "INTERESTING"))

    fp_rate = round(fp_count / total_signals, 3) if total_signals else 0.0
    dup_rate = round(dup_count / total_signals, 3) if total_signals else 0.0
    inv_rate = round(investigating_count / total_signals, 3) if total_signals else 0.0
    high_pri_precision = round(high_pri_useful / len(high_pri_signals), 3) if high_pri_signals else 0.0

    return {
        "signals_generated": total_signals,
        "signals_opened": opened_count,
        "signals_dismissed": dismissed_count,
        "false_positive_rate": fp_rate,
        "duplicate_rate": dup_rate,
        "investigation_rate": inv_rate,
        "high_priority_precision": high_pri_precision,
    }
