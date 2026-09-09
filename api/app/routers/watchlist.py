"""Watchlist router."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import User, WatchlistEntry
from app.routers.deps import get_current_user
from app.schemas import WatchlistAdd, WatchlistOut

router = APIRouter(prefix="/api/v1/watchlist", tags=["watchlist"])


@router.post("", response_model=WatchlistOut, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=WatchlistOut, status_code=status.HTTP_201_CREATED, include_in_schema=False)
def add_to_watchlist(
    body: WatchlistAdd,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WatchlistEntry:
    """Add an entity (target, asset, feature) to user's watchlist."""
    existing = (
        db.query(WatchlistEntry)
        .filter_by(
            user_id=current_user.id,
            entity_type=body.entity_type,
            entity_id=body.entity_id,
        )
        .first()
    )
    if existing:
        return existing

    entry = WatchlistEntry(
        user_id=current_user.id,
        entity_type=body.entity_type,
        entity_id=body.entity_id,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


@router.get("", response_model=list[WatchlistOut])
@router.get("/", response_model=list[WatchlistOut], include_in_schema=False)
def list_watchlist(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[WatchlistEntry]:
    """List watchlist entries for the current user."""
    return (
        db.query(WatchlistEntry)
        .filter_by(user_id=current_user.id)
        .order_by(WatchlistEntry.created_at.desc())
        .all()
    )


@router.delete("/{entry_id}")
def remove_from_watchlist(
    entry_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """Remove an item from the user's watchlist."""
    entry = db.get(WatchlistEntry, entry_id)
    if not entry or entry.user_id != current_user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Watchlist entry not found")

    db.delete(entry)
    db.commit()
    return {"message": "Removed from watchlist"}
