"""Authentication and authorization dependencies."""
from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import User
from app.services.auth import validate_session


def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
) -> User:
    """Validate session cookie and return the authenticated user.

    Raises 401 HTTPException if session cookie is missing or invalid.
    """
    token = request.cookies.get("session_token")
    if not token:
        # Fallback to Authorization Bearer header if cookies are not used
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    user = validate_session(db, token)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session",
        )

    return user


def get_optional_user(
    request: Request,
    db: Session = Depends(get_db),
) -> User | None:
    """Validate session cookie and return the user, or None if unauthenticated."""
    token = request.cookies.get("session_token")
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()

    if not token:
        return None

    user = validate_session(db, token)
    if not user or not user.is_active:
        return None

    return user


def require_role(*allowed_roles: str):
    """Enforce that authenticated user possesses one of the allowed roles."""
    def role_dependency(user: User = Depends(get_current_user)) -> User:
        user_role = getattr(user, "role", "RESEARCHER")
        is_admin_flag = getattr(user, "is_admin", False)

        # OWNER and ADMIN bypass if allowed
        if is_admin_flag and ("ADMIN" in allowed_roles or "OWNER" in allowed_roles):
            return user

        if user_role in allowed_roles or (user_role == "OWNER" and "ADMIN" in allowed_roles):
            return user

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Operation requires one of the following roles: {', '.join(allowed_roles)}. Current role: {user_role}.",
        )
    return role_dependency


def require_admin(user: User = Depends(get_current_user)) -> User:
    """Enforce that user is OWNER or ADMIN."""
    user_role = getattr(user, "role", "RESEARCHER")
    is_admin_flag = getattr(user, "is_admin", False)

    if user_role in ("RESEARCHER", "VIEWER"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrative access required.",
        )

    if user_role in ("OWNER", "ADMIN") or is_admin_flag:
        return user

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Administrative access required.",
    )


def require_researcher_or_above(user: User = Depends(get_current_user)) -> User:
    """Enforce that user is RESEARCHER, ADMIN, or OWNER (VIEWER cannot mutate)."""
    user_role = getattr(user, "role", "RESEARCHER")
    is_admin_flag = getattr(user, "is_admin", False)

    if is_admin_flag or user_role in ("OWNER", "ADMIN", "RESEARCHER"):
        return user

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Researcher or administrative role required. Read-only viewer accounts cannot perform this action.",
    )

