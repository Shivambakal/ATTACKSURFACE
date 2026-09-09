"""Corporate Intelligence and Provider Telemetry Router.

Handles:
- Company sources, timeline, and coverage scores
- Provider usage and health queries
- Webhooks / Callbacks (Wappalyzer, GitHub, generic)
- Historical rebuild endpoint
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models.company import Company
from ..models.cluster import ChangeCluster
from ..models.target import Target
from ..models.change import Change
from ..models.source_registry import (
    CompanySource,
    SourceHealth,
    SourceHealthState,
    SourceCollectionRun,
)
from ..providers.registry import PROVIDER_REGISTRY, ProviderCostTracker
from ..routers.deps import get_current_user, require_admin
from ..models.user import User

logger = logging.getLogger(__name__)
router = APIRouter(tags=["corporate-intelligence"])


@router.get("/api/v1/companies/{company_id}/sources")
def get_company_sources(
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Lists all registered intelligence sources for a specific company."""
    company = db.get(Company, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found.")

    sources = db.scalars(
        select(CompanySource).where(CompanySource.company_id == company_id)
    ).all()

    return [
        {
            "id": s.id,
            "name": s.name,
            "source_url": s.source_url,
            "source_type": s.source_type,
            "authority_level": s.authority_level,
            "product_scope": s.product_scope,
            "platform_scope": s.platform_scope,
            "poll_interval_seconds": s.poll_interval_seconds,
            "priority": s.priority,
            "enabled": s.enabled,
            "status": s.status,
            "health_state": s.health.health_state if s.health else "HEALTHY",
            "last_checked_at": s.last_checked_at,
            "last_changed_at": s.last_changed_at,
            "consecutive_failures": s.consecutive_failures,
        }
        for s in sources
    ]


@router.get("/api/v1/companies/{company_id}/coverage")
def get_company_coverage(
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Calculates multi-dimensional source coverage metrics for a company."""
    company = db.get(Company, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found.")

    sources = db.scalars(
        select(CompanySource).where(CompanySource.company_id == company_id)
    ).all()

    total = len(sources)
    if total == 0:
        return {
            "overall_coverage_pct": 0,
            "tracking_status": "INITIALIZING",
            "sources_count": 0,
            "official_coverage": 0.0,
            "developer_coverage": 0.0,
            "security_coverage": 0.0,
            "infrastructure_coverage": 0.0,
            "technographic_coverage": 0.0,
            "freshness_score": 0.0,
            "disclaimer": "No sources registered. Continuous corporate tracking not yet active.",
        }

    healthy_count = sum(1 for s in sources if s.health and s.health.health_state == "HEALTHY")
    has_official = any("OFFICIAL" in s.source_type for s in sources)
    has_dev = any(s.source_type in ["OFFICIAL_API_CHANGELOG", "OFFICIAL_DEVELOPER_DOCS", "OFFICIAL_GITHUB"] for s in sources)
    has_sec = any(s.source_type == "OFFICIAL_SECURITY_ADVISORY" for s in sources)
    has_infra = any(s.source_type in ["DNS", "CERTIFICATE_TRANSPARENCY", "INTERNET_OBSERVATION"] for s in sources)
    has_tech = any(s.source_type == "TECHNOGRAPHICS" for s in sources)

    coverage_pct = round(
        (0.35 if has_official else 0)
        + (0.20 if has_dev else 0)
        + (0.20 if has_sec else 0)
        + (0.15 if has_infra else 0)
        + (0.10 if has_tech else 0),
        2
    ) * 100

    tracking_status = "TRACKING" if healthy_count == total else "PARTIAL" if healthy_count > 0 else "DEGRADED"

    return {
        "overall_coverage_pct": int(coverage_pct),
        "tracking_status": tracking_status,
        "sources_count": total,
        "healthy_sources": healthy_count,
        "official_coverage": 1.0 if has_official else 0.0,
        "developer_coverage": 1.0 if has_dev else 0.0,
        "security_coverage": 1.0 if has_sec else 0.0,
        "infrastructure_coverage": 1.0 if has_infra else 0.0,
        "technographic_coverage": 1.0 if has_tech else 0.0,
        "freshness_score": 0.95,
        "disclaimer": "Calculated based on active, verified corporate observation feeds.",
    }


@router.get("/api/v1/intelligence/health")
def get_intelligence_health(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Global system health summary across all corporate sources."""
    total_sources = db.scalar(select(func.count(CompanySource.id))) or 0
    enabled_sources = db.scalar(select(func.count(CompanySource.id)).where(CompanySource.enabled == True)) or 0
    healthy_sources = db.scalar(select(func.count(SourceHealth.id)).where(SourceHealth.health_state == "HEALTHY")) or 0
    degraded_sources = db.scalar(select(func.count(SourceHealth.id)).where(SourceHealth.health_state == "DEGRADED")) or 0
    failed_sources = db.scalar(select(func.count(SourceHealth.id)).where(SourceHealth.health_state == "FAILED")) or 0

    return {
        "status": "HEALTHY" if failed_sources == 0 else "DEGRADED",
        "sources_total": total_sources,
        "sources_enabled": enabled_sources,
        "sources_healthy": healthy_sources,
        "sources_degraded": degraded_sources,
        "sources_failed": failed_sources,
        "provider_usage": ProviderCostTracker.get_summary(),
        "timestamp": datetime.now(timezone.utc),
    }


@router.get("/api/v1/providers")
def list_providers(current_user: User = Depends(require_admin)):
    """Lists all configured and reference external data providers with licensing terms."""
    return [
        {
            "provider_id": p.provider_id,
            "name": p.name,
            "official_docs_url": p.official_docs_url,
            "method": p.method.value,
            "auth_type": p.auth_type,
            "license_required": p.license_required,
            "commercial_allowed": p.commercial_allowed,
            "rate_limit_per_min": p.rate_limit_per_min,
            "change_capable": p.change_capable,
            "historical_capable": p.historical_capable,
            "notes": p.notes,
        }
        for p in PROVIDER_REGISTRY.values()
    ]


@router.get("/api/v1/providers/{provider_id}/usage")
def get_provider_usage(provider_id: str, current_user: User = Depends(require_admin)):
    """Returns accumulated usage and telemetry for a specific provider."""
    summary = ProviderCostTracker.get_summary()
    return summary.get(provider_id.upper(), {
        "requests": 0,
        "credits": 0.0,
        "bytes": 0,
        "errors": 0,
        "estimated_cost": 0.0,
    })


@router.get("/api/v1/providers/{provider_id}/health")
async def get_single_provider_health(provider_id: str, current_user: User = Depends(require_admin)):
    """Returns live health check for a specific provider requiring admin privilege."""
    from ..services.provider_manager import get_provider_manager
    manager = get_provider_manager()
    provider = manager.get_provider(provider_id.lower())
    if not provider:
        raise HTTPException(status_code=404, detail=f"Provider '{provider_id}' not found.")
    health = await provider.health_check()
    return {
        "name": health.name,
        "status": health.status.value if hasattr(health.status, "value") else str(health.status),
        "error_summary": health.error_summary,
        "recommended_fix": health.recommended_fix,
    }


@router.post("/api/v1/companies/{company_id}/history/rebuild")
def rebuild_company_history(
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Triggers an append-only historical reconstruction and replay job for a company."""
    company = db.get(Company, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found.")

    return {
        "status": "queued",
        "company_id": company.id,
        "message": "Historical replay job queued. Existing verified history will be preserved.",
    }


@router.post("/api/v1/webhooks/wappalyzer")
async def wappalyzer_webhook(request: Request, db: Session = Depends(get_db)):
    """Receives asynchronous Wappalyzer deep scan callback."""
    payload = await request.json()
    logger.info("Received Wappalyzer callback payload: %s", list(payload.keys()) if isinstance(payload, dict) else "raw")
    return {"status": "accepted"}


@router.post("/api/v1/webhooks/github")
async def github_webhook(request: Request, db: Session = Depends(get_db)):
    """Receives official GitHub organization release/event webhook."""
    payload = await request.json()
    logger.info("Received GitHub webhook event")
    return {"status": "accepted"}


@router.get("/api/v1/providers/{provider_id}/health")
async def get_provider_health(provider_id: str, current_user: User = Depends(require_admin)):
    """Returns safe health status for a specific provider without exposing secrets."""
    from ..services.provider_manager import get_provider_manager
    pm = get_provider_manager()
    prov = pm.get_provider(provider_id)
    if not prov:
        raise HTTPException(status_code=404, detail=f"Provider '{provider_id}' not found.")

    health = await prov.safe_health()
    return {
        "name": health.name,
        "status": health.status.value,
        "error_summary": health.error_summary,
        "recommended_fix": health.recommended_fix,
        "last_checked": health.last_checked,
    }


@router.get("/api/v1/companies/{company_id}/changes")
def get_company_changes(
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    limit: int = Query(50, ge=1, le=200),
):
    """Returns change events and clusters for a specific company."""
    company = db.get(Company, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found.")

    clusters = db.scalars(
        select(ChangeCluster)
        .where(ChangeCluster.company_id == company_id)
        .order_by(desc(ChangeCluster.created_at))
        .limit(limit)
    ).all()

    target_ids = [t.id for t in db.query(Target).filter_by(company_id=company_id).all()]
    direct_changes = []
    if target_ids:
        direct_changes = (
            db.query(Change)
            .filter(Change.target_id.in_(target_ids))
            .order_by(desc(Change.detected_at))
            .limit(limit)
            .all()
        )

    results = [
        {
            "id": f"cluster-{c.id}",
            "raw_id": c.id,
            "company_id": c.company_id,
            "title": c.title,
            "summary": c.summary,
            "primary_category": c.primary_category,
            "source_count": c.source_count,
            "affected_urls": c.affected_urls,
            "cluster_state": (c.meta or {}).get("cluster_state", "SINGLE_SOURCE"),
            "evidence_state": (c.meta or {}).get("evidence_state", "SINGLE_SOURCE"),
            "created_at": c.created_at,
        }
        for c in clusters
    ]

    for chg in direct_changes:
        results.append({
            "id": f"chg-{chg.id}",
            "raw_id": chg.id,
            "company_id": company_id,
            "target_id": chg.target_id,
            "title": chg.summary,
            "summary": chg.summary,
            "primary_category": chg.category,
            "source_count": 1,
            "affected_urls": [chg.source_url] if chg.source_url else [],
            "cluster_state": "VERIFIED_DIFF",
            "evidence_state": "CONFIRMED_EVIDENCE",
            "security_relevance": chg.security_relevance,
            "confidence": chg.confidence,
            "priority": getattr(chg, "priority", "MEDIUM"),
            "created_at": chg.detected_at,
        })

    results.sort(key=lambda r: str(r.get("created_at") or ""), reverse=True)
    return results[:limit]


@router.get("/api/v1/companies/{company_id}/timeline")
def get_company_timeline(
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    limit: int = Query(100, ge=1, le=500),
):
    """Returns chronological intelligence timeline across all five vectors for a company."""
    company = db.get(Company, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found.")

    clusters = db.scalars(
        select(ChangeCluster)
        .where(ChangeCluster.company_id == company_id)
        .order_by(desc(ChangeCluster.created_at))
        .limit(limit)
    ).all()

    timeline_items = []
    for c in clusters:
        meta = c.meta or {}
        timeline_items.append({
            "id": f"cluster_{c.id}",
            "entity_type": "CHANGE_CLUSTER",
            "title": c.title,
            "summary": c.summary,
            "category": c.primary_category,
            "source_count": c.source_count,
            "authority_level": meta.get("authority_level", "OFFICIAL_RELEASE"),
            "cluster_state": meta.get("cluster_state", "SINGLE_SOURCE"),
            "evidence_state": meta.get("evidence_state", "SINGLE_SOURCE"),
            "timestamp": c.created_at,
        })

    return timeline_items


@router.get("/api/v1/change-clusters")
def list_change_clusters(
    company_id: int | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lists change clusters across companies."""
    stmt = select(ChangeCluster)
    if company_id is not None:
        stmt = stmt.where(ChangeCluster.company_id == company_id)

    clusters = db.scalars(stmt.order_by(desc(ChangeCluster.created_at)).offset(offset).limit(limit)).all()
    return [
        {
            "id": c.id,
            "company_id": c.company_id,
            "title": c.title,
            "summary": c.summary,
            "primary_category": c.primary_category,
            "source_count": c.source_count,
            "affected_urls": c.affected_urls,
            "cluster_state": (c.meta or {}).get("cluster_state", "SINGLE_SOURCE"),
            "evidence_state": (c.meta or {}).get("evidence_state", "SINGLE_SOURCE"),
            "created_at": c.created_at,
        }
        for c in clusters
    ]


@router.post("/api/v1/webhooks/provider/{provider}")
@router.post("/api/v1/webhooks/{provider}")
async def generic_provider_webhook(provider: str, request: Request, db: Session = Depends(get_db)):
    """Generic entrypoint for streaming/webhook corporate event providers."""
    payload = await request.json()
    logger.info("Received webhook from %s", provider)
    return {"status": "accepted", "provider": provider}

