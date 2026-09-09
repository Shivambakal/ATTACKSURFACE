"""Snapshots collection and diffing router."""
from __future__ import annotations

import hashlib
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import (
    Change,
    ChangeEvidence,
    Observation,
    Snapshot,
    Target,
    TimelineEvent,
    User,
    utcnow,
)
from app.routers.deps import get_current_user, require_researcher_or_above
from app.schemas import SnapshotOut
from app.services.pipeline import TargetPipeline
from app.services.target_safety import target_not_authorized

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/targets/{target_id}/snapshots", tags=["snapshots"])


@router.post("", response_model=SnapshotOut, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=SnapshotOut, status_code=status.HTTP_201_CREATED, include_in_schema=False)
async def take_snapshot(
    target_id: int,
    current_user: User = Depends(require_researcher_or_above),
    db: Session = Depends(get_db),
) -> Snapshot:
    """Trigger snapshot collection, compare against previous snapshot, and detect changes using full intelligence pipeline."""
    target = db.get(Target, target_id)
    if not target:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Target not found")
    if not target.authorization_confirmed:
        raise target_not_authorized()

    try:
        pipeline = TargetPipeline()
        result = await pipeline.run(target.id, db)
        snapshot_id = result.get("snapshot_id")
        snapshot = db.get(Snapshot, snapshot_id) if snapshot_id else None
        if not snapshot:
            snapshot = (
                db.query(Snapshot)
                .filter_by(target_id=target.id)
                .order_by(Snapshot.collected_at.desc())
                .first()
            )
        if not snapshot:
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Snapshot record could not be retrieved.")
        return snapshot
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Snapshot collection failed for target %d: %s", target_id, exc)
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            f"Pipeline observation failed: {exc}",
        ) from exc


@router.get("", response_model=list[SnapshotOut])
@router.get("/", response_model=list[SnapshotOut], include_in_schema=False)
def list_snapshots(
    target_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Snapshot]:
    """List all snapshots taken for a target."""
    target = db.get(Target, target_id)
    if not target:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Target not found")

    return (
        db.query(Snapshot)
        .filter_by(target_id=target_id)
        .order_by(Snapshot.collected_at.desc())
        .all()
    )
