"""Alerts and notification preferences router."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Alert, AlertPreference, User
from app.routers.deps import get_current_user
from app.schemas import AlertOut, AlertPreferenceUpdate

router = APIRouter(prefix="/api/v1/alerts", tags=["alerts"])


@router.get("", response_model=list[AlertOut])
@router.get("/", response_model=list[AlertOut], include_in_schema=False)
def list_alerts(
    unread_only: bool = Query(default=False),
    limit: int = Query(default=50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Alert]:
    """List alerts for current user."""
    query = db.query(Alert).filter_by(user_id=current_user.id)
    if unread_only:
        query = query.filter_by(read=False)
    return query.order_by(Alert.created_at.desc()).limit(limit).all()


@router.post("/{alert_id}/read")
def mark_alert_read(
    alert_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Mark an alert as read."""
    alert = db.get(Alert, alert_id)
    if not alert or alert.user_id != current_user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Alert not found")

    alert.read = True
    db.commit()
    return {"message": "Alert marked as read", "id": alert.id, "read": True}


@router.post("/read-all")
def mark_all_alerts_read(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Mark all unread alerts as read for current user."""
    count = (
        db.query(Alert)
        .filter_by(user_id=current_user.id, read=False)
        .update({"read": True})
    )
    db.commit()
    return {"message": "All alerts marked as read", "updated_count": count}


@router.get("/preferences")
def get_alert_preferences(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    """Get alert preferences for current user."""
    prefs = db.query(AlertPreference).filter_by(user_id=current_user.id).all()
    return [
        {"id": p.id, "alert_type": p.alert_type, "frequency": p.frequency}
        for p in prefs
    ]


@router.put("/preferences")
def update_alert_preference(
    body: AlertPreferenceUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Update or create an alert preference for current user."""
    pref = (
        db.query(AlertPreference)
        .filter_by(user_id=current_user.id, alert_type=body.alert_type)
        .first()
    )
    if pref:
        pref.frequency = body.frequency
    else:
        pref = AlertPreference(
            user_id=current_user.id,
            alert_type=body.alert_type,
            frequency=body.frequency,
        )
        db.add(pref)

    db.commit()
    db.refresh(pref)
    return {
        "id": pref.id,
        "alert_type": pref.alert_type,
        "frequency": pref.frequency,
    }
