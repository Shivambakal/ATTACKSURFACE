"""Verification telemetry API.

Exposes computed verification coverage for the researcher UI. Counts are derived
from persisted evidence/changes/signals; there are no display-only constants.
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Change, ChangeEvidence, ResearchSignal, Target
from app.routers.deps import get_current_user
from app.services.verification_engine import VerificationEngine

router = APIRouter(prefix="/api/v1/verification", tags=["verification"])
engine = VerificationEngine()


def _recent_cutoff(hours: int) -> datetime:
    return datetime.now(timezone.utc) - timedelta(hours=hours)


@router.get("/telemetry")
def verification_telemetry(
    hours: int = Query(default=1, ge=1, le=168),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Return conservative verification telemetry for the selected time window."""
    cutoff = _recent_cutoff(hours)
    changes = db.query(Change).filter(Change.detected_at >= cutoff).all()

    total = len(changes)
    with_evidence = 0
    corroborated = 0
    observed = 0
    documented = 0
    unverified = 0
    rejected_or_weak = 0
    avg_conf = 0.0

    for change in changes:
        evidences = db.query(ChangeEvidence).filter(ChangeEvidence.change_id == change.id).all()
        if evidences:
            with_evidence += 1
        states = {str(e.state).upper() for e in evidences}
        payloads = [e.payload or {} for e in evidences]
        has_direct = any(str(p.get("evidence_strength", "")).upper() == "DIRECT_PRODUCTION_OBSERVATION" for p in payloads)
        has_corroboration = len(evidences) >= 2 or any(str(p.get("observation_state", "")).upper() == "CONFIRMED" for p in payloads)
        has_documented = any(s in states for s in {"DOCUMENTED", "DOCUMENTED_NOT_OBSERVED"})
        if has_direct:
            observed += 1
        if has_corroboration:
            corroborated += 1
        if has_documented:
            documented += 1
        if not evidences:
            unverified += 1
        if any(str(p.get("verification_state", "")).upper() in {"UNVERIFIED", "REJECTED"} for p in payloads):
            rejected_or_weak += 1
        avg_conf += float(change.confidence or 0.0)

    avg_conf = round((avg_conf / total) * 100, 1) if total else 0.0
    verified = observed + max(0, corroborated - observed)
    verified = min(verified, total)
    coverage = round((verified / total) * 100, 1) if total else 0.0

    signal_count = db.query(func.count(ResearchSignal.id)).filter(ResearchSignal.created_at >= cutoff).scalar() or 0
    active_targets = db.query(func.count(Target.id)).filter(Target.monitoring_status == "active").scalar() or 0

    return {
        "window_hours": hours,
        "since": cutoff.isoformat(),
        "server_time": datetime.now(timezone.utc).isoformat(),
        "engine_version": VerificationEngine.VERSION,
        "total_recent_changes": total,
        "verified_changes": verified,
        "verified_coverage_pct": coverage,
        "direct_observations": observed,
        "corroborated_changes": corroborated,
        "documented_changes": documented,
        "unverified_changes": unverified,
        "rejected_or_weak_changes": rejected_or_weak,
        "average_change_confidence_pct": avg_conf,
        "recent_research_signals": signal_count,
        "active_targets": active_targets,
        "semantic_status": "NO_RECENT_MEANINGFUL_DIFFS" if total == 0 else "VERIFICATION_STREAM_ACTIVE",
    }


@router.get("/change/{change_id}")
def verify_change(
    change_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Return the evidence chain and conservative verification state for one change."""
    change = db.get(Change, change_id)
    if not change:
        return {"error": "Change not found"}

    evidences = db.query(ChangeEvidence).filter(ChangeEvidence.change_id == change.id).all()
    payloads = [e.payload or {} for e in evidences]
    source_count = len({str(p.get("source_url") or p.get("source") or "").strip() for p in payloads if (p.get("source_url") or p.get("source"))})
    direct = any(str(p.get("evidence_strength", "")).upper() == "DIRECT_PRODUCTION_OBSERVATION" for p in payloads)
    state = "UNVERIFIED"
    if direct:
        state = "CONFIRMED" if source_count >= 2 or len(evidences) >= 2 else "OBSERVED"
    elif len(evidences) >= 2:
        state = "CORROBORATED"
    elif any(str(e.state).upper() in {"DOCUMENTED", "DOCUMENTED_NOT_OBSERVED"} for e in evidences):
        state = "DOCUMENTED"

    return {
        "id": change.id,
        "state": state,
        "confidence_pct": round(float(change.confidence or 0.0) * 100, 1),
        "security_relevance": change.security_relevance,
        "priority": change.priority,
        "source_url": change.source_url,
        "detected_at": change.detected_at.isoformat() if change.detected_at else None,
        "evidence_count": len(evidences),
        "source_count": source_count,
        "evidence": [
            {
                "id": e.id,
                "state": e.state,
                "payload": e.payload,
            }
            for e in evidences
        ],
    }
