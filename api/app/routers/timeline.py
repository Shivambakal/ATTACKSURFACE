"""Target timeline router."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Target, TimelineEvent, User
from app.routers.deps import get_current_user
from app.schemas import TimelineEventOut

router = APIRouter(prefix="/api/v1/targets/{target_id}/timeline", tags=["timeline"])


def _get_authorized_target(target_id: int, user: User, db: Session) -> Target:
    target = db.get(Target, target_id)
    if not target:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Target not found")
    return target


@router.get("", response_model=list[TimelineEventOut])
@router.get("/", response_model=list[TimelineEventOut], include_in_schema=False)
def get_timeline(
    target_id: int,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[TimelineEvent]:
    """Get timeline events for a target ordered by observed_at descending."""
    _get_authorized_target(target_id, current_user, db)

    return (
        db.query(TimelineEvent)
        .filter_by(target_id=target_id)
        .order_by(TimelineEvent.observed_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


@router.get("/since-last-visit", response_model=list[TimelineEventOut])
def get_timeline_since_last_visit(
    target_id: int,
    limit: int = Query(default=100, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[TimelineEvent]:
    """Get timeline events observed since the user's last visited timestamp."""
    target = _get_authorized_target(target_id, current_user, db)

    query = db.query(TimelineEvent).filter_by(target_id=target_id)
    if target.last_visited_at is not None:
        query = query.filter(TimelineEvent.observed_at > target.last_visited_at)

    return query.order_by(TimelineEvent.observed_at.desc()).limit(limit).all()
