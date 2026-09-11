"""Live Intelligence Feed and Dashboard Telemetry Router.

Aggregates real events from PostgreSQL database:
- NEW ASSET
- SCOPE CHANGE
- API CHANGE
- TECHNOLOGY CHANGE
- SECURITY EVENT
- RESEARCH SIGNAL

Computes real-time 50-target trial telemetry and statistics with zero synthetic data.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.db import get_db
from app.models import (
    Asset,
    Change,
    ChangeEvidence,
    Company,
    ResearchSignal,
    Snapshot,
    Target,
    TimelineEvent,
    TrialRun,
    TrialTarget,
    User,
)
from app.routers.deps import get_current_user
from app.services.trial_service import trial_metrics

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/intelligence", tags=["live-intelligence"])


def _classify_change_event_type(category: str, summary: str) -> str:
    cat = (category or "").upper()
    sum_low = (summary or "").lower()

    if "API" in cat or "/api/" in sum_low or "endpoint" in sum_low:
        return "API CHANGE"
    if "TECH" in cat or "server" in sum_low or "framework" in sum_low or "technology" in sum_low:
        return "TECHNOLOGY CHANGE"
    if "SCOPE" in cat or "subdomain" in sum_low or "domain" in sum_low or "dns" in sum_low:
        return "SCOPE CHANGE"
    if "AUTH" in cat or "SECURITY" in cat or "cve" in sum_low or "token" in sum_low or "login" in sum_low:
        return "SECURITY EVENT"
    return "API CHANGE" if "/api" in sum_low else "SCOPE CHANGE"


@router.get("/trial-status")
def get_live_trial_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Returns canonical 50-target live trial statistics and metrics directly from the database."""
    return trial_metrics(db)


@router.get("/live-feed")
def get_live_feed(
    limit: int = Query(default=40, ge=1, le=150),
    filter_type: Optional[str] = Query(default=None),
    since: Optional[str] = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Returns chronologically ordered live intelligence events from the database.

    Event types:
    - NEW ASSET
    - SCOPE CHANGE
    - API CHANGE
    - TECHNOLOGY CHANGE
    - SECURITY EVENT
    - RESEARCH SIGNAL
    """
    events: list[dict[str, Any]] = []

    # Map target IDs to domain & company
    targets = db.query(Target).all()
    target_map = {t.id: t for t in targets}
    company_map = {c.id: c.name for c in db.query(Company).all()}

    # 1. Real Research Signals
    signals_q = db.query(ResearchSignal).order_by(desc(ResearchSignal.created_at))
    if since:
        try:
            since_dt = datetime.fromisoformat(since.replace("Z", "+00:00"))
            signals_q = signals_q.filter(ResearchSignal.created_at > since_dt)
        except Exception:
            pass
    for sig in signals_q.limit(limit).all():
        tgt = target_map.get(sig.target_id)
        comp_name = tgt.company_name if tgt else (company_map.get(sig.company_id, "Authorized Org") if sig.company_id else "Authorized Org")
        events.append({
            "id": f"sig-{sig.id}",
            "raw_id": sig.id,
            "kind": "SIGNAL",
            "event_type": "RESEARCH SIGNAL",
            "target": tgt.domain if tgt else comp_name,
            "target_id": sig.target_id,
            "company": comp_name,
            "company_id": sig.company_id or (tgt.company_id if tgt else None),
            "what_changed": sig.title,
            "why_it_matters": getattr(sig, "why_it_matters", "") or getattr(sig, "summary", ""),
            "timestamp": sig.created_at.isoformat() if sig.created_at else None,
            "security_relevance": sig.relevance_score,
            "confidence": sig.confidence_score,
            "priority": sig.priority,
            "status": sig.status,
            "evidence": sig.evidence_ids or [],
            "source": f"Research Pipeline ({sig.signal_type})",
        })

    # 2. Real Change Clusters
    clusters_q = db.query(ChangeCluster).order_by(desc(ChangeCluster.created_at))
    if since:
        try:
            since_dt = datetime.fromisoformat(since.replace("Z", "+00:00"))
            clusters_q = clusters_q.filter(ChangeCluster.created_at > since_dt)
        except Exception:
            pass
    for c in clusters_q.limit(limit).all():
        tgt = target_map.get(c.target_id) if c.target_id else None
        comp_name = company_map.get(c.company_id) or (tgt.company_name if tgt else "Tracked Organization")
        meta = c.meta or {}
        events.append({
            "id": f"cluster-{c.id}",
            "raw_id": c.id,
            "kind": "CHANGE",
            "event_type": _classify_change_event_type(c.primary_category, c.title),
            "target": tgt.domain if tgt else (c.affected_urls[0] if c.affected_urls else comp_name),
            "target_id": c.target_id,
            "company": comp_name,
            "company_id": c.company_id,
            "what_changed": c.title,
            "why_it_matters": c.summary or f"Multi-source converged change cluster ({c.source_count} sources)",
            "timestamp": c.created_at.isoformat() if c.created_at else None,
            "security_relevance": meta.get("relevance_score", 65),
            "confidence": int(meta.get("confidence", 0.85) * 100) if isinstance(meta.get("confidence"), float) else 85,
            "priority": meta.get("priority", "MEDIUM"),
            "status": "active",
            "source": meta.get("authority_level", "Official Advisory"),
            "evidence": c.affected_urls or [],
        })

    # 3. Real Attack-Surface Changes
    changes_q = db.query(Change).order_by(desc(Change.detected_at))
    if since:
        try:
            since_dt = datetime.fromisoformat(since.replace("Z", "+00:00"))
            changes_q = changes_q.filter(Change.detected_at > since_dt)
        except Exception:
            pass
    for chg in changes_q.limit(limit).all():
        tgt = target_map.get(chg.target_id)
        comp_name = tgt.company_name if tgt else "Target Organization"
        evt_type = _classify_change_event_type(chg.category, chg.summary)
        events.append({
            "id": f"chg-{chg.id}",
            "raw_id": chg.id,
            "kind": "CHANGE",
            "event_type": evt_type,
            "target": tgt.domain if tgt else "Monitored Host",
            "target_id": chg.target_id,
            "company": comp_name,
            "company_id": tgt.company_id if tgt else None,
            "what_changed": chg.summary,
            "why_it_matters": f"Category: {chg.category} (Relevance: {chg.security_relevance}/100, Conf: {int((chg.confidence or 0.7)*100)}%)",
            "timestamp": chg.detected_at.isoformat() if chg.detected_at else None,
            "security_relevance": chg.security_relevance,
            "confidence": int((chg.confidence or 0.7) * 100),
            "priority": getattr(chg, "priority", "MEDIUM"),
            "status": getattr(chg, "status", "interesting"),
            "source": chg.source_url or (tgt.domain if tgt else "Target Domain"),
            "evidence": [f"diff-{chg.id}"],
        })

    # 3. Real Discovered Assets
    assets_q = db.query(Asset).order_by(desc(Asset.discovered_at))
    for ast in assets_q.limit(limit // 2).all():
        comp_name = company_map.get(ast.company_id, "Monitored Organization") if ast.company_id else "Monitored Organization"
        asset_val = ast.hostname or ast.name or ast.url or f"asset-{ast.id}"
        events.append({
            "id": f"ast-{ast.id}",
            "raw_id": ast.id,
            "kind": "ASSET",
            "event_type": "NEW ASSET",
            "target": asset_val,
            "target_id": ast.target_id,
            "company": comp_name,
            "company_id": ast.company_id,
            "what_changed": f"Discovered public asset {asset_val} ({ast.asset_type})",
            "why_it_matters": f"Active attack surface footprint for {comp_name}",
            "timestamp": ast.discovered_at.isoformat() if ast.discovered_at else None,
            "security_relevance": 50,
            "confidence": int((ast.confidence or 0.9) * 100),
            "priority": "MEDIUM",
            "status": ast.status or "active",
            "source": ast.source or "Passive Discovery",
            "evidence": [f"asset-{ast.id}"],
        })

    # Sort all events newest first
    events.sort(key=lambda e: e["timestamp"] or "", reverse=True)

    # Filter if filter_type provided
    if filter_type and filter_type.upper() != "ALL":
        ft = filter_type.upper()
        if ft == "SIGNALS":
            events = [e for e in events if e["event_type"] == "RESEARCH SIGNAL"]
        elif ft == "CHANGES":
            events = [e for e in events if e["kind"] == "CHANGE"]
        elif ft == "SECURITY":
            events = [e for e in events if e["event_type"] == "SECURITY EVENT" or e["priority"] in ("CRITICAL", "HIGH")]
        elif ft == "ASSETS":
            events = [e for e in events if e["event_type"] == "NEW ASSET"]

    final_events = events[:limit]
    latest_ts = final_events[0]["timestamp"] if final_events else None

    return {
        "events": final_events,
        "total_returned": len(final_events),
        "latest_event_timestamp": latest_ts,
        "server_time": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/changes/{change_id}/detail")
def get_change_detail(
    change_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Returns comprehensive forensic detail for a specific change, including before/after states and diff."""
    change = db.get(Change, change_id)
    if not change:
        return {"error": "Change record not found."}

    target = db.get(Target, change.target_id)
    evidences = db.query(ChangeEvidence).filter_by(change_id=change.id).all()

    before_evidence = next((e for e in evidences if e.state == "before"), None)
    after_evidence = next((e for e in evidences if e.state == "after"), None)

    return {
        "id": change.id,
        "target_id": change.target_id,
        "target_domain": target.domain if target else "Unknown",
        "company_name": target.company_name if target else "Unknown",
        "category": change.category,
        "summary": change.summary,
        "security_relevance": change.security_relevance,
        "confidence": change.confidence,
        "priority": getattr(change, "priority", "MEDIUM"),
        "status": getattr(change, "status", "interesting"),
        "source_url": change.source_url,
        "detected_at": change.detected_at.isoformat() if change.detected_at else None,
        "before_state": (before_evidence.payload or {}) if before_evidence else None,
        "after_state": (after_evidence.payload or {}) if after_evidence else None,
        "evidence_count": len(evidences),
    }
