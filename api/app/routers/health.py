from __future__ import annotations

import time
from typing import Any
from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import text
from redis import Redis

from app.config import settings
from app.db import engine
from app.models.base import utcnow
from app.models import User
from app.routers.deps import require_admin
from app.schemas import ProviderHealthOut
from app.services.provider_manager import get_provider_manager

router = APIRouter(tags=["health"])


@router.get("/health")
@router.get("/api/v1/health")
def liveness() -> dict[str, Any]:
    """Lightweight liveness probe indicating the web application process is alive."""
    return {
        "status": "ok",
        "service": "attacksurface-api",
        "application": "alive",
        "timestamp": utcnow().isoformat(),
    }


@router.get("/ready")
@router.get("/api/v1/ready")
def readiness(response: Response) -> dict[str, Any]:
    """Production readiness probe distinguishing application, database, and Redis states.

    Returns HTTP 503 if core dependencies (database) are unreachable.
    """
    db_healthy = False
    db_latency_ms = -1.0
    db_version = "unknown"
    db_error = None

    # 1. Database Check
    try:
        t0 = time.perf_counter()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            try:
                ver = conn.execute(text("SELECT version_num FROM alembic_version")).scalar()
                db_version = str(ver) if ver else "untracked"
            except Exception:
                db_version = "no_alembic_table"
        db_latency_ms = round((time.perf_counter() - t0) * 1000, 2)
        db_healthy = True
    except Exception as exc:
        db_error = str(exc)

    # 2. Redis Check
    redis_healthy = False
    redis_latency_ms = -1.0
    redis_error = None
    try:
        t0 = time.perf_counter()
        r = Redis.from_url(settings.redis_url, socket_timeout=2.0, socket_connect_timeout=2.0)
        if r.ping():
            redis_healthy = True
            redis_latency_ms = round((time.perf_counter() - t0) * 1000, 2)
    except Exception as exc:
        redis_error = str(exc)

    overall_status = "ok" if (db_healthy and redis_healthy) else ("degraded" if db_healthy else "unhealthy")

    if not db_healthy:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "status": overall_status,
        "application": "alive",
        "database": {
            "healthy": db_healthy,
            "latency_ms": db_latency_ms if db_healthy else None,
            "migration_version": db_version,
            "error": db_error,
        },
        "redis": {
            "healthy": redis_healthy,
            "latency_ms": redis_latency_ms if redis_healthy else None,
            "error": redis_error,
        },
        "timestamp": utcnow().isoformat(),
    }


@router.get("/providers", response_model=list[ProviderHealthOut])
async def provider_health(current_user: User = Depends(require_admin)) -> list[ProviderHealthOut]:
    """Check health of all registered providers. Credentials and secrets are NEVER exposed."""
    manager = get_provider_manager()
    results = await manager.health_check_all()

    return [
        ProviderHealthOut(
            name=r.name,
            status=r.status.value if hasattr(r.status, "value") else str(r.status),
            error_summary=r.error_summary,
            recommended_fix=r.recommended_fix,
        )
        for r in results
    ]
