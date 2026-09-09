"""User settings and active sessions router."""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session as DBSession

from app.db import get_db
from app.models import Session as SessionModel, User, UserSettings, utcnow
from app.routers.deps import get_current_user
from app.schemas import SessionOut, SettingsOut, SettingsUpdate

router = APIRouter(prefix="/api/v1/settings", tags=["settings"])


def _get_or_create_settings(user: User, db: DBSession) -> UserSettings:
    if user.settings:
        return user.settings

    settings = db.query(UserSettings).filter_by(user_id=user.id).first()
    if not settings:
        settings = UserSettings(user_id=user.id)
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return settings


@router.get("", response_model=SettingsOut)
@router.get("/", response_model=SettingsOut, include_in_schema=False)
def get_settings(
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
) -> UserSettings:
    """Get application settings for the current user."""
    return _get_or_create_settings(current_user, db)


@router.put("", response_model=SettingsOut)
@router.put("/", response_model=SettingsOut, include_in_schema=False)
@router.patch("", response_model=SettingsOut)
@router.patch("/", response_model=SettingsOut, include_in_schema=False)
def update_settings(
    body: SettingsUpdate,
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
) -> UserSettings:
    """Update settings (appearance, notifications, research, privacy)."""
    settings = _get_or_create_settings(current_user, db)

    if body.appearance is not None:
        current_app = settings.appearance or {}
        current_app.update(body.appearance)
        settings.appearance = dict(current_app)

    if body.notifications is not None:
        current_notif = settings.notifications or {}
        current_notif.update(body.notifications)
        settings.notifications = dict(current_notif)

    if body.research is not None:
        current_res = settings.research or {}
        current_res.update(body.research)
        settings.research = dict(current_res)

    if body.privacy is not None:
        current_priv = settings.privacy or {}
        current_priv.update(body.privacy)
        settings.privacy = dict(current_priv)

    settings.updated_at = utcnow()
    db.commit()
    db.refresh(settings)
    return settings


@router.get("/sessions", response_model=list[SessionOut])
def list_active_sessions(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
) -> list[dict]:
    """List active sessions for current user. Secrets and hashes are NEVER exposed."""
    raw_token = request.cookies.get("session_token")
    if not raw_token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            raw_token = auth_header[7:].strip()

    current_hash = (
        hashlib.sha256(raw_token.encode()).hexdigest() if raw_token else None
    )

    now = datetime.now(timezone.utc)
    sessions = (
        db.query(SessionModel)
        .filter(
            SessionModel.user_id == current_user.id,
            SessionModel.revoked == False,
            SessionModel.expires_at > now,
        )
        .order_by(SessionModel.created_at.desc())
        .all()
    )

    return [
        {
            "id": s.id,
            "ip_address": s.ip_address,
            "user_agent": s.user_agent,
            "created_at": s.created_at,
            "expires_at": s.expires_at,
            "is_current": (s.token_hash == current_hash) if current_hash else False,
        }
        for s in sessions
    ]


@router.delete("/sessions/{session_id}")
def revoke_user_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
) -> dict[str, str]:
    """Revoke a specific active session."""
    session = db.get(SessionModel, session_id)
    if not session or session.user_id != current_user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Session not found")

    session.revoked = True
    db.commit()
    return {"message": "Session revoked successfully"}
