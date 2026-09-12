"""API Router for Source Registry and Health Telemetry."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models.source_registry import (
    CompanySource,
    SourceHealth,
    SourceCollectionRun,
    RawSourceSnapshot,
    SourceStatus,
    SourceHealthState,
)
from ..routers.deps import get_current_user, get_optional_user, require_admin
from ..models.user import User
from ..models.company import Company
from ..services.connector_engine import ConnectorEngine

router = APIRouter(tags=["sources"])
engine = ConnectorEngine()


class SourceCreate(BaseModel):
    company_id: int
    name: str
    source_url: str
    source_type: str = "OFFICIAL_PRODUCT_CHANGE"
    authority_level: str = "OFFICIAL_RELEASE"
    product_scope: str | None = None
    platform_scope: str | None = None
    parser_strategy: str = "generic_feed"
    feed_url: str | None = None
    api_url: str | None = None
    poll_interval_seconds: int = 600
    priority: str = "P2"
    notes: str | None = None


class SourceUpdate(BaseModel):
    name: str | None = None
    enabled: bool | None = None
    poll_interval_seconds: int | None = None
    priority: str | None = None
    parser_strategy: str | None = None
    notes: str | None = None


@router.get("/api/v1/sources")
def list_sources(
    company_id: int | None = Query(None),
    source_type: str | None = Query(None),
    authority_level: str | None = Query(None),
    health: str | None = Query(None),
    enabled: bool | None = Query(None),
    q: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
):
    """Lists registered corporate data sources with filters and health state."""
    stmt = select(CompanySource)
    if isinstance(company_id, int):
        stmt = stmt.where(CompanySource.company_id == company_id)
    if isinstance(source_type, str) and source_type and source_type != "ALL":
        stmt = stmt.where(CompanySource.source_type == source_type)
    if isinstance(authority_level, str) and authority_level and authority_level != "ALL":
        stmt = stmt.where(CompanySource.authority_level == authority_level)
    if isinstance(enabled, bool):
        stmt = stmt.where(CompanySource.enabled == enabled)
    if isinstance(q, str) and q.strip():
        search_term = q.strip()
        stmt = stmt.outerjoin(Company, CompanySource.company_id == Company.id).where(
            (CompanySource.name.ilike(f"%{search_term}%"))
            | (CompanySource.source_url.ilike(f"%{search_term}%"))
            | (CompanySource.product_scope.ilike(f"%{search_term}%"))
            | (Company.name.ilike(f"%{search_term}%"))
        )

    safe_limit = limit if isinstance(limit, int) and 1 <= limit <= 200 else 50
    safe_offset = offset if isinstance(offset, int) and offset >= 0 else 0

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    sources = db.scalars(
        stmt.order_by(CompanySource.priority.asc(), CompanySource.id.asc())
        .offset(safe_offset)
        .limit(safe_limit)
    ).all()

    items = []
    for s in sources:
        if s.status == SourceStatus.NEVER_CHECKED.value:
            h_state = "NOT_CONFIGURED" if not (s.feed_url or s.source_url) else "NEVER_CHECKED"
        elif s.status == SourceStatus.FAILED.value:
            h_state = s.health.health_state if (s.health and s.health.health_state != "HEALTHY") else "FAILED"
        elif s.health:
            h_state = s.health.health_state
        else:
            h_state = "UNKNOWN"

        if isinstance(health, str) and health != "ALL" and h_state.upper() != health.upper():
            continue
        items.append({
            "id": s.id,
            "company_id": s.company_id,
            "company_name": s.company.name if s.company else "Unknown",
            "name": s.name,
            "source_url": s.source_url,
            "source_type": s.source_type,
            "authority_level": s.authority_level,
            "product_scope": s.product_scope,
            "platform_scope": s.platform_scope,
            "parser_strategy": s.parser_strategy,
            "collection_method": s.collection_method,
            "feed_url": s.feed_url,
            "api_url": s.api_url,
            "poll_interval_seconds": s.poll_interval_seconds,
            "priority": s.priority,
            "enabled": s.enabled,
            "status": s.status,
            "health_state": h_state,
            "last_checked_at": s.last_checked_at,
            "last_changed_at": s.last_changed_at,
            "last_success_at": s.last_success_at,
            "next_check_at": s.next_check_at,
            "last_http_status": s.last_http_status,
            "last_error": s.last_error,
            "consecutive_failures": s.consecutive_failures,
            "parser_version": s.parser_version,
            "notes": s.notes,
        })

    return {"total": total, "items": items}


@router.post("/api/v1/sources", status_code=201)
def create_source(
    payload: SourceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Registers a new corporate intelligence source."""
    existing = db.scalar(
        select(CompanySource).where(
            CompanySource.company_id == payload.company_id,
            CompanySource.source_url == payload.source_url,
        )
    )
    if existing:
        raise HTTPException(status_code=400, detail="Source URL already registered for this company.")

    src = CompanySource(
        company_id=payload.company_id,
        name=payload.name,
        source_url=payload.source_url,
        source_type=payload.source_type,
        authority_level=payload.authority_level,
        product_scope=payload.product_scope,
        platform_scope=payload.platform_scope,
        parser_strategy=payload.parser_strategy,
        feed_url=payload.feed_url,
        api_url=payload.api_url,
        poll_interval_seconds=payload.poll_interval_seconds,
        priority=payload.priority,
        notes=payload.notes,
        status=SourceStatus.NEVER_CHECKED.value,
        next_check_at=datetime.now(timezone.utc),
    )
    db.add(src)
    db.flush()

    health = SourceHealth(source_id=src.id, health_state=SourceHealthState.HEALTHY.value)
    db.add(health)
    db.commit()
    db.refresh(src)
    return {"id": src.id, "name": src.name, "status": src.status}


@router.get("/api/v1/sources/{source_id}")
def get_source_detail(
    source_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieves full metadata and telemetry for a single source."""
    s = db.get(CompanySource, source_id)
    if not s:
        raise HTTPException(status_code=404, detail="Source not found.")

    return {
        "id": s.id,
        "company_id": s.company_id,
        "company_name": s.company.name if s.company else "Unknown",
        "name": s.name,
        "source_url": s.source_url,
        "source_type": s.source_type,
        "authority_level": s.authority_level,
        "product_scope": s.product_scope,
        "platform_scope": s.platform_scope,
        "parser_strategy": s.parser_strategy,
        "collection_method": s.collection_method,
        "feed_url": s.feed_url,
        "api_url": s.api_url,
        "repository_url": s.repository_url,
        "poll_interval_seconds": s.poll_interval_seconds,
        "priority": s.priority,
        "enabled": s.enabled,
        "status": s.status,
        "health": {
            "state": (
                "NOT_CONFIGURED" if s.status == SourceStatus.NEVER_CHECKED.value and not (s.feed_url or s.source_url)
                else ("NEVER_CHECKED" if s.status == SourceStatus.NEVER_CHECKED.value
                else (s.health.health_state if (s.health and (s.status != SourceStatus.FAILED.value or s.health.health_state != "HEALTHY"))
                else ("FAILED" if s.status == SourceStatus.FAILED.value else "UNKNOWN")))
            ),
            "latency_ms": s.health.latency_ms if s.health else 0,
            "consecutive_failures": s.health.consecutive_failures if s.health else (s.consecutive_failures or 0),
            "last_checked_at": s.health.last_checked_at if s.health else s.last_checked_at,
            "last_success_at": s.health.last_success_at if s.health else s.last_success_at,
        },
        "last_checked_at": s.last_checked_at,
        "last_changed_at": s.last_changed_at,
        "last_success_at": s.last_success_at,
        "next_check_at": s.next_check_at,
        "last_http_status": s.last_http_status,
        "last_error": s.last_error,
        "etag": s.etag,
        "last_modified": s.last_modified,
        "content_hash": s.content_hash,
        "parser_version": s.parser_version,
        "notes": s.notes,
    }


@router.patch("/api/v1/sources/{source_id}")
def update_source(
    source_id: int,
    payload: SourceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Updates configuration parameters of a source."""
    s = db.get(CompanySource, source_id)
    if not s:
        raise HTTPException(status_code=404, detail="Source not found.")

    if payload.name is not None:
        s.name = payload.name
    if payload.enabled is not None:
        s.enabled = payload.enabled
    if payload.poll_interval_seconds is not None:
        s.poll_interval_seconds = payload.poll_interval_seconds
    if payload.priority is not None:
        s.priority = payload.priority
    if payload.parser_strategy is not None:
        s.parser_strategy = payload.parser_strategy
    if payload.notes is not None:
        s.notes = payload.notes

    db.commit()
    return {"status": "success", "id": s.id}


@router.post("/api/v1/sources/{source_id}/check")
async def check_source_now(
    source_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Manually triggers an immediate conditional fetch and parse cycle for a source."""
    s = db.get(CompanySource, source_id)
    if not s:
        raise HTTPException(status_code=404, detail="Source not found.")

    res = await engine.execute_source(s.id, db)
    return {
        "source_id": s.id,
        "status": res.status,
        "http_status": res.http_status,
        "items_found": len(res.items),
        "duration_ms": res.duration_ms,
        "error": res.error_message,
    }


@router.get("/api/v1/sources/{source_id}/runs")
def get_source_runs(
    source_id: int,
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Returns recent execution runs and telemetry for a source."""
    runs = db.scalars(
        select(SourceCollectionRun)
        .where(SourceCollectionRun.source_id == source_id)
        .order_by(desc(SourceCollectionRun.started_at))
        .limit(limit)
    ).all()

    return [
        {
            "id": r.id,
            "started_at": r.started_at,
            "finished_at": r.finished_at,
            "status": r.status,
            "http_status": r.http_status,
            "items_found": r.items_found,
            "items_changed": r.items_changed,
            "duration_ms": r.duration_ms,
            "error_message": r.error_message,
            "credits_used": r.credits_used,
            "response_bytes": r.response_bytes,
        }
        for r in runs
    ]


@router.get("/api/v1/sources/{source_id}/health")
def get_source_health(
    source_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Returns real-time health breakdown for a source."""
    h = db.scalar(select(SourceHealth).where(SourceHealth.source_id == source_id))
    if not h:
        raise HTTPException(status_code=404, detail="Health record not found.")

    return {
        "source_id": h.source_id,
        "health_state": h.health_state,
        "latency_ms": h.latency_ms,
        "consecutive_failures": h.consecutive_failures,
        "failure_rate": h.failure_rate,
        "change_rate": h.change_rate,
        "last_checked_at": h.last_checked_at,
        "last_success_at": h.last_success_at,
        "details": h.details,
    }
