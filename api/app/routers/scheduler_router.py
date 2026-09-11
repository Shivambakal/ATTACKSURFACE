"""Corporate Intelligence and Live Pipeline Scheduler Router.

Exposes endpoints to trigger and monitor continuous 10-minute collection cycles:
- GET / POST /api/v1/scheduler/run : Executes due corporate sources and AI intelligence collection
- GET / POST /api/v1/cron/collect : Standard webhook/cron alias for scheduler run
- GET /api/v1/scheduler/status : Real-time scheduler health, Redis state, and queue counts
- POST /api/v1/scheduler/sources/{source_id}/run : Force-trigger collection for a single source
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import desc, func, or_, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models.source_registry import (
    CompanySource,
    SourceCollectionRun,
    SourceHealth,
    SourceStatus,
)
from ..services.corporate_scheduler import CorporateScheduler

logger = logging.getLogger(__name__)

router = APIRouter(tags=["scheduler"])


@router.get("/api/v1/scheduler/status")
def get_scheduler_status(db: Session = Depends(get_db)) -> dict[str, Any]:
    """Returns the operational status of the live intelligence scheduler."""
    now = datetime.now(timezone.utc)
    scheduler = CorporateScheduler()

    # Redis health check
    redis_healthy = False
    redis_error = None
    try:
        r = scheduler.redis
        if r is not None and r.ping():
            redis_healthy = True
        else:
            redis_error = "Redis returned non-truthy ping or is None (using memory locks)"
    except Exception as exc:
        redis_error = str(exc)

    # Database counts
    total_sources = db.scalar(select(func.count(CompanySource.id))) or 0
    enabled_sources = db.scalar(
        select(func.count(CompanySource.id)).where(CompanySource.enabled.is_(True))
    ) or 0
    due_sources = db.scalar(
        select(func.count(CompanySource.id)).where(
            CompanySource.enabled.is_(True),
            CompanySource.status != SourceStatus.DISABLED.value,
            or_(CompanySource.next_check_at.is_(None), CompanySource.next_check_at <= now),
        )
    ) or 0

    # Recent runs
    recent_runs_orm = db.scalars(
        select(SourceCollectionRun)
        .order_by(desc(SourceCollectionRun.started_at))
        .limit(10)
    ).all()
    recent_runs = [
        {
            "id": r.id,
            "source_id": r.source_id,
            "status": r.status,
            "http_status": r.http_status,
            "items_found": r.items_found,
            "items_changed": r.items_changed,
            "duration_ms": r.duration_ms,
            "started_at": r.started_at,
            "finished_at": r.finished_at,
            "error": r.error_message,
        }
        for r in recent_runs_orm
    ]

    last_run = recent_runs[0] if recent_runs else None

    return {
        "status": "HEALTHY" if redis_healthy else "DEGRADED_IN_MEMORY_LOCKS",
        "redis": {
            "connected": redis_healthy,
            "mode": "distributed_redis" if redis_healthy else "in_memory_fallback",
            "error": redis_error,
        },
        "sources": {
            "total": total_sources,
            "enabled": enabled_sources,
            "due_now": due_sources,
        },
        "last_collection_run": last_run,
        "recent_runs": recent_runs,
        "timestamp": now.isoformat(),
    }


@router.get("/api/v1/scheduler/run")
@router.post("/api/v1/scheduler/run")
@router.get("/api/v1/cron/collect")
@router.post("/api/v1/cron/collect")
async def trigger_scheduler_cycle(
    limit: int = Query(default=15, ge=1, le=100, description="Max sources to collect in this cycle"),
    force: bool = Query(default=False, description="Collect enabled sources regardless of next_check_at"),
    run_ai: bool = Query(default=True, description="Whether to also trigger Gemini security news intelligence"),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Executes a live intelligence collection cycle across due sources and AI intelligence."""
    cycle_id = str(uuid.uuid4())
    started_at = datetime.now(timezone.utc)
    logger.info("Starting live intelligence cycle %s (limit=%d, force=%s, run_ai=%s)", cycle_id, limit, force, run_ai)

    scheduler = CorporateScheduler()

    # 1. Execute due corporate sources
    source_stats = await scheduler.run_due_sources(db, max_sources=limit, force=force)

    # 2. Optionally execute Gemini security intelligence cycle
    ai_stats: dict[str, Any] = {"executed": False}
    if run_ai:
        try:
            ai_stats = await scheduler.run_security_intelligence_cycle(db)
            ai_stats["executed"] = True
        except Exception as exc:
            logger.warning("AI security intelligence cycle error in cycle %s: %s", cycle_id, exc)
            ai_stats = {"executed": False, "error": str(exc)}

    finished_at = datetime.now(timezone.utc)
    duration_ms = int((finished_at - started_at).total_seconds() * 1000)

    return {
        "cycle_id": cycle_id,
        "status": "COMPLETED",
        "started_at": started_at.isoformat(),
        "finished_at": finished_at.isoformat(),
        "duration_ms": duration_ms,
        "corporate_sources": source_stats,
        "security_intelligence": ai_stats,
    }


@router.post("/api/v1/scheduler/sources/{source_id}/run")
async def trigger_single_source(
    source_id: int,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Forces immediate collection for a single source by ID."""
    source = db.get(CompanySource, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found.")

    scheduler = CorporateScheduler()
    result = await scheduler.engine.execute_source(source_id, db)

    return {
        "source_id": source.id,
        "source_name": source.name,
        "status": result.status,
        "http_status": result.http_status,
        "items_found": len(result.items),
        "duration_ms": result.duration_ms,
        "error": result.error_message,
    }