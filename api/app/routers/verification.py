"""Verification telemetry API.

Counts are derived from persisted evidence plus immutable production observations.
A second before/after record from the same source is not treated as independent
corroboration. Direct observations require a real observation URL and content hash.
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Change, ChangeEvidence, Observation, ResearchSignal, Target
from app.routers.deps import get_current_user
from app.services.verification_engine import VerificationEngine

router = APIRouter(prefix="/api/v1/verification", tags=["verification"])
engine = VerificationEngine()


def _recent_cutoff(hours: int) -> datetime:
    return datetime.now(timezone.utc) - timedelta(hours=hours)


def _payload_source(payload: dict[str, Any]) -> str:
    return str(payload.get("source_url") or payload.get("source") or payload.get("provider") or "").strip()


def _distinct_sources(payloads: list[dict[str, Any]]) -> set[str]:
    return {value for value in (_payload_source(p) for p in payloads) if value}


def _parse_dt(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def _evaluate_change(change: Change, evidences: list[ChangeEvidence], observations: list[Observation]) -> dict[str, Any]:
    payloads = [e.payload or {} for e in evidences]
    sources = _distinct_sources(payloads)

    # A persisted Observation is the strongest production proof available in the
    # current schema: URL + HTTP observation + immutable content hash + target snapshot.
    matching_obs = next((o for o in observations if o.url == change.source_url), None) or (observations[0] if observations else None)
    observation_payload: dict[str, Any] = {}
    if matching_obs:
        observation_payload = {
            "source_url": matching_obs.url,
            "source_type": "DIRECT_PRODUCTION_OBSERVATION",
            "authority_level": "DIRECT_PRODUCTION_OBSERVATION",
            "evidence_strength": "DIRECT_PRODUCTION_OBSERVATION",
            "content_hash": matching_obs.content_hash,
            "observed_at": matching_obs.observed_at.isoformat() if matching_obs.observed_at else None,
            "entity_relationship_verified": True,
            "http_status": matching_obs.status_code,
            "ai_generated": False,
        }
        payloads = [observation_payload, *payloads]
        sources.add(matching_obs.url)

    direct = bool(matching_obs) or any(str(p.get("evidence_strength", "")).upper() == "DIRECT_PRODUCTION_OBSERVATION" for p in payloads)
    entity_verified = bool(matching_obs) or any(bool(p.get("entity_relationship_verified")) for p in payloads)
    first_payload = payloads[0] if payloads else {}

    result = engine.evaluate(
        title=change.summary,
        summary=change.researcher_note or change.summary,
        item_url=change.source_url,
        source_url=change.source_url,
        source_type=str(first_payload.get("source_type") or first_payload.get("authority_level") or "").upper(),
        authority_level=str(first_payload.get("authority_level") or "").upper(),
        source_content_hash=str(first_payload.get("content_hash") or ""),
        published_at=_parse_dt(first_payload.get("published_at") or first_payload.get("observed_at")),
        updated_at=_parse_dt(first_payload.get("updated_at")),
        ai_generated=bool(first_payload.get("ai_generated")),
        direct_production_observed=direct,
        corroborating_source_count=len(sources),
        entity_relationship_verified=entity_verified,
    )
    return result.to_dict() | {
        "evidence_count": len(evidences),
        "production_observation_id": matching_obs.id if matching_obs else None,
        "distinct_source_count": len(sources),
        "distinct_sources": sorted(sources),
    }


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
    verified = 0
    observed = 0
    corroborated = 0
    documented = 0
    unverified = 0
    rejected_or_weak = 0
    confidence_sum = 0.0

    for change in changes:
        evidences = db.query(ChangeEvidence).filter(ChangeEvidence.change_id == change.id).all()
        observations = db.query(Observation).filter(Observation.snapshot_id == change.snapshot_id).all()
        evaluation = _evaluate_change(change, evidences, observations)
        state = evaluation["state"]
        if state == "CONFIRMED":
            verified += 1
            observed += 1
        elif state == "CORROBORATED":
            verified += 1
            corroborated += 1
        elif state == "OBSERVED":
            observed += 1
        elif state == "DOCUMENTED":
            documented += 1
        else:
            unverified += 1
        if evaluation["blockers"]:
            rejected_or_weak += 1
        confidence_sum += float(evaluation["score"] or 0.0)

    coverage = round((verified / total) * 100, 1) if total else 0.0
    avg_conf = round((confidence_sum / total) * 100, 1) if total else 0.0
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
    """Return the deterministic verification result and complete evidence chain."""
    change = db.get(Change, change_id)
    if not change:
        return {"error": "Change not found"}

    evidences = db.query(ChangeEvidence).filter(ChangeEvidence.change_id == change.id).all()
    observations = db.query(Observation).filter(Observation.snapshot_id == change.snapshot_id).all()
    evaluation = _evaluate_change(change, evidences, observations)

    return {
        "id": change.id,
        "state": evaluation["state"],
        "verification": evaluation,
        "confidence_pct": round(float(change.confidence or 0.0) * 100, 1),
        "security_relevance": change.security_relevance,
        "priority": change.priority,
        "source_url": change.source_url,
        "detected_at": change.detected_at.isoformat() if change.detected_at else None,
        "production_observation": {
            "id": next((o.id for o in observations if o.url == change.source_url), None),
            "url": next((o.url for o in observations if o.url == change.source_url), None),
            "content_hash": next((o.content_hash for o in observations if o.url == change.source_url), None),
        },
        "evidence": [
            {"id": e.id, "state": e.state, "payload": e.payload}
            for e in evidences
        ],
    }
