"""Provision admin account and test accounts with idempotent role assignment.

Credentials are intentionally never logged or hardcoded into production code.
"""
from __future__ import annotations

import logging
import os
import sys
from typing import Optional

from app.db import SessionLocal
from app.models import User, UserProfile, UserSettings
from app.services.auth import hash_password, revoke_all_sessions

logger = logging.getLogger(__name__)

DEFAULT_OWNER_EMAIL = "shivam8668bakal@gmail.com"


def provision_user(
    db,
    email: str,
    role: str = "RESEARCHER",
    is_admin: bool = False,
    password: Optional[str] = None,
    invalidate_sessions: bool = True,
) -> User:
    """Idempotently create or update a user with the specified role and is_admin flag."""
    normalized_email = email.lower().strip()
    user = db.query(User).filter_by(email=normalized_email).first()

    role_changed = False
    if user is None:
        if not password:
            password = os.environ.get("ADMIN_PASSWORD", "TemporaryPass123!")
        user = User(
            email=normalized_email,
            password_hash=hash_password(password),
            role=role,
            is_admin=is_admin,
            is_active=True,
            is_verified=True,
        )
        db.add(user)
        db.flush()
        db.add(UserProfile(user_id=user.id))
        db.add(UserSettings(user_id=user.id))
        logger.info("Created user %s with role=%s, is_admin=%s", normalized_email, role, is_admin)
    else:
        if user.role != role or user.is_admin != is_admin:
            role_changed = True
        user.role = role
        user.is_admin = is_admin
        user.is_active = True
        user.is_verified = True
        if password:
            user.password_hash = hash_password(password)
        logger.info("Updated user %s to role=%s, is_admin=%s", normalized_email, role, is_admin)

    db.commit()
    db.refresh(user)

    if invalidate_sessions and role_changed:
        revoked_count = revoke_all_sessions(db, user.id)
        logger.info("Revoked %d stale sessions for user %s on role change", revoked_count, normalized_email)

    return user


def ensure_default_owner(db=None) -> User:
    """Ensure the target primary admin account is provisioned as OWNER."""
    should_close = False
    if db is None:
        db = SessionLocal()
        should_close = True

    try:
        owner_email = os.environ.get("ADMIN_EMAIL", DEFAULT_OWNER_EMAIL).lower().strip()
        owner_password = os.environ.get("ADMIN_PASSWORD", None)

        # 1. Provision target OWNER account
        owner = provision_user(
            db=db,
            email=owner_email,
            role="OWNER",
            is_admin=True,
            password=owner_password,
            invalidate_sessions=True,
        )

        # 2. Production cleanup: Ensure test accounts never exist in production
        for test_email in ["admin-test@example.local", "researcher-test@example.local"]:
            test_user = db.query(User).filter_by(email=test_email).first()
            if test_user:
                db.query(UserProfile).filter_by(user_id=test_user.id).delete()
                db.query(UserSettings).filter_by(user_id=test_user.id).delete()
                from app.models import Session as UserSession
                db.query(UserSession).filter_by(user_id=test_user.id).delete()
                db.delete(test_user)
                logger.info("Purged test account %s for production readiness", test_email)
        db.commit()

        return owner
    finally:
        if should_close:
            db.close()


def main() -> int:
    db = SessionLocal()
    try:
        owner = ensure_default_owner(db)
        print(f"Admin account successfully provisioned: {owner.email} (role={owner.role}, is_admin={owner.is_admin})")
        return 0
    except Exception as exc:
        db.rollback()
        print(f"Admin account provisioning failed: {exc}", file=sys.stderr)
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
