"""Verification Router — live DB-only telemetry and claim detail endpoints.

All endpoints:
- Require authenticated user (get_current_user)
- Never cache (skipCache behavior built-in at the API level — responses have no-store headers)
- Never return hardcoded or fabricated values
- Return 0 if DB count is 0; never substitute a plausible fake number
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import User
from app.routers.deps import get_current_user
from app.services.verification_engine import VerificationEngine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/verification", tags=["verification"])

# Force no-cache on all responses from this router
NO_CACHE_HEADERS = {
    "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
    "Pragma": "no-cache",
}


@router.get("/telemetry")
def get_verification_telemetry(
    hours: Annotated[int, Query(ge=1, le=168, description="Lookback window in hours (1–168)")] = 1,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    """Live verification telemetry aggregated directly from the database.

    - No caching, no fallback values, no localStorage.
    - If a metric returns 0 from the DB, the response contains 0.
    - If computation fails, returns 503 — never a fake number.

    Returns:
        verified_count: Sources with SUCCESS_CHANGED in window
        observed_count: Sources with SUCCESS_UNCHANGED in window
        corroborated_count: Companies with ≥2 independent successful source types in window
        unverified_count: Sources with FAILED status in window
        conflicting_count: Sources with RATE_LIMITED in window
        recent_diffs_count: Change records detected_at within window
        direct_observations_count: RawSourceSnapshot records retrieved within window
        authorized_targets_count: Total authorized targets (all time)
        company_registry_count: Total companies in registry (all time)
        active_signals_count: ResearchSignal records in active status
        avg_confidence_pct: Average confidence from changes in window (null if none)
        coverage_pct: Percentage of enabled sources checked in window (null if none)
        window_hours: The requested window
        computed_at: ISO 8601 UTC timestamp of computation
        source: Always "database"
    """
    try:
        engine = VerificationEngine(db)
        telemetry = engine.compute_telemetry(window_hours=hours)
        return JSONResponse(content=telemetry, headers=NO_CACHE_HEADERS)
    except Exception as exc:
        logger.error("Verification telemetry computation failed: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Verification telemetry computation failed. Database may be unavailable.",
        )


@router.get("/claims/{claim_id}")
def get_claim_detail(
    claim_id: int,
    claim_type: Annotated[str, Query(description="'signal' or 'change'")] = "signal",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    """Return the 7-step evidence chain and verification state for a single claim.

    The evidence chain proves WHY a state was assigned:
    SOURCE → EVIDENCE → ENTITY → OBSERVATION → CHANGE → SECURITY_CONTEXT → RESEARCH_SIGNAL

    State assignment rules:
    - AI cannot promote a claim above CANDIDATE
    - Score alone cannot establish VERIFIED
    - FAILED or NEVER_CHECKED are never treated as healthy

    Args:
        claim_id: Primary key of the signal or change record
        claim_type: "signal" (default) or "change"
    """
    if claim_type not in ("signal", "change"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="claim_type must be 'signal' or 'change'",
        )
    try:
        engine = VerificationEngine(db)
        detail = engine.get_claim_detail(claim_id, claim_type)
        if "error" in detail:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=detail["error"],
            )
        return JSONResponse(content=detail, headers=NO_CACHE_HEADERS)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Claim detail fetch failed for %s/%d: %s", claim_type, claim_id, exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Claim detail computation failed.",
        )


@router.get("/health")
def get_verification_health(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    """Pipeline health check: last cycle timestamp, worker activity, source coverage.

    Uses only existing DB tables. Never returns fabricated uptime or fake timestamps.
    If a field is unknown (e.g. worker was never run), that field is null — not a plausible fake.
    """
    from sqlalchemy import func
    from app.models.source_registry import SourceCollectionRun, CompanySource

    try:
        # Last successful collection run
        last_run = (
            db.query(SourceCollectionRun)
            .filter(SourceCollectionRun.status.in_(["SUCCESS_CHANGED", "SUCCESS_UNCHANGED"]))
            .order_by(SourceCollectionRun.finished_at.desc())
            .first()
        )

        # Last failed run
        last_failed = (
            db.query(SourceCollectionRun)
            .filter(SourceCollectionRun.status == "FAILED")
            .order_by(SourceCollectionRun.started_at.desc())
            .first()
        )

        # Total runs in last 24h
        from datetime import timedelta
        window_24h = datetime.now(timezone.utc) - timedelta(hours=24)
        runs_24h = (
            db.query(func.count(SourceCollectionRun.id))
            .filter(SourceCollectionRun.started_at >= window_24h)
            .scalar()
        ) or 0

        # Enabled source count
        enabled_sources = (
            db.query(func.count(CompanySource.id))
            .filter(CompanySource.enabled == True)  # noqa: E712
            .scalar()
        ) or 0

        return JSONResponse(
            content={
                "last_successful_run_at": (
                    last_run.finished_at.isoformat()
                    if last_run and last_run.finished_at
                    else None
                ),
                "last_successful_run_id": last_run.id if last_run else None,
                "last_failed_run_at": (
                    last_failed.started_at.isoformat()
                    if last_failed and last_failed.started_at
                    else None
                ),
                "runs_last_24h": runs_24h,
                "enabled_sources": enabled_sources,
                "checked_at": datetime.now(timezone.utc).isoformat(),
                "source": "database",
            },
            headers=NO_CACHE_HEADERS,
        )
    except Exception as exc:
        logger.error("Verification health check failed: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Verification health check failed. Database may be unavailable.",
        )
