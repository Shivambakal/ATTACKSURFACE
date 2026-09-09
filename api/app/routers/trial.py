"""50 Target Trial control-plane endpoints."""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import User
from app.routers.deps import require_admin
from app.services.trial_service import REGISTRY_PATH, start_trial, trial_metrics

router = APIRouter(prefix="/api/v1/trial", tags=["50 Target Trial"])


@router.post("/start")
def begin_trial(user: User = Depends(require_admin), db: Session = Depends(get_db)) -> dict:
    try:
        return start_trial(db, user, Path(REGISTRY_PATH))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/metrics")
def get_trial_metrics(
    run_id: int | None = None,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    return trial_metrics(db, run_id)
