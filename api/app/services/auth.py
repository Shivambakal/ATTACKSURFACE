"""Authentication service — password hashing, session management, token generation.

NEVER logs, prints, or exposes passwords, hashes, tokens, or session secrets.
"""
from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
from sqlalchemy.orm import Session as DBSession

from ..models.user import User, Session, VerificationToken, PasswordResetToken, UserProfile
from ..models.settings import UserSettings


# ── Password hashing ────────────────────────────────────────────────

def hash_password(password: str) -> str:
    """Hash a password with bcrypt. Never log the input or output."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against its hash. Never log the input or output."""
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


# ── Token generation ────────────────────────────────────────────────

def _generate_token() -> tuple[str, str]:
    """Generate a random token and its SHA-256 hash.

    Returns (raw_token, token_hash). Only the hash is stored;
    the raw token is given to the user once.
    """
    raw = secrets.token_urlsafe(48)
    token_hash = hashlib.sha256(raw.encode()).hexdigest()
    return raw, token_hash


def _hash_token(raw: str) -> str:
    """Hash a raw token for database lookup."""
    return hashlib.sha256(raw.encode()).hexdigest()


# ── User creation ───────────────────────────────────────────────────

def create_user(db: DBSession, email: str, password: str, role: str = "RESEARCHER") -> User:
    """Create a new user with hashed password, role, default profile, and settings."""
    normalized_email = email.lower().strip()
    # Sole administrator constraint: only shivam8668bakal@gmail.com is granted OWNER / admin privileges
    if normalized_email == "shivam8668bakal@gmail.com":
        assigned_role = "OWNER"
        is_admin_user = True
        is_verified = True
    else:
        assigned_role = "RESEARCHER"
        is_admin_user = False
        is_verified = False

    user = User(
        email=normalized_email,
        password_hash=hash_password(password),
        role=assigned_role,
        is_active=True,
        is_verified=is_verified,
        is_admin=is_admin_user,
    )
    db.add(user)
    db.flush()

    # Create default profile and settings
    profile = UserProfile(user_id=user.id)
    settings = UserSettings(user_id=user.id)
    db.add(profile)
    db.add(settings)
    db.commit()
    db.refresh(user)
    return user


# ── Session management ──────────────────────────────────────────────

def create_session(
    db: DBSession,
    user: User,
    ip_address: str | None = None,
    user_agent: str | None = None,
    duration_hours: int = 168,  # 7 days
) -> str:
    """Create a new session and return the raw session token.

    Only the token hash is stored. The raw token is returned once.
    """
    raw_token, token_hash = _generate_token()
    session = Session(
        user_id=user.id,
        token_hash=token_hash,
        ip_address=ip_address,
        user_agent=user_agent,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=duration_hours),
    )
    db.add(session)
    db.commit()
    return raw_token


def _is_expired(dt: datetime) -> bool:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt < datetime.now(timezone.utc)


def validate_session(db: DBSession, raw_token: str) -> User | None:
    """Validate a session token and return the user, or None.

    Rejects expired and revoked sessions.
    """
    token_hash = _hash_token(raw_token)
    session = db.query(Session).filter_by(token_hash=token_hash, revoked=False).first()
    if not session:
        return None
    if _is_expired(session.expires_at):
        return None
    return db.get(User, session.user_id)


def revoke_session(db: DBSession, raw_token: str) -> bool:
    """Revoke a single session by its raw token."""
    token_hash = _hash_token(raw_token)
    session = db.query(Session).filter_by(token_hash=token_hash).first()
    if session:
        session.revoked = True
        db.commit()
        return True
    return False


def revoke_all_sessions(db: DBSession, user_id: int) -> int:
    """Revoke all sessions for a user. Returns count of revoked sessions."""
    count = db.query(Session).filter_by(user_id=user_id, revoked=False).update({"revoked": True})
    db.commit()
    return count


# ── Verification tokens ────────────────────────────────────────────

def create_verification_token(db: DBSession, user_id: int, hours: int = 48) -> str:
    """Create an email verification token. Returns raw token."""
    raw_token, token_hash = _generate_token()
    token = VerificationToken(
        user_id=user_id,
        token_hash=token_hash,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=hours),
    )
    db.add(token)
    db.commit()
    return raw_token


def verify_email(db: DBSession, raw_token: str) -> bool:
    """Verify email using the raw verification token."""
    token_hash = _hash_token(raw_token)
    token = db.query(VerificationToken).filter_by(token_hash=token_hash, used=False).first()
    if not token or _is_expired(token.expires_at):
        return False
    user = db.get(User, token.user_id)
    if user:
        user.is_verified = True
        token.used = True
        db.commit()
        return True
    return False


# ── Password reset ──────────────────────────────────────────────────

def create_password_reset_token(db: DBSession, user_id: int, hours: float = 0.5) -> str:
    """Create a password reset token (default 30-minute validity). Returns raw token."""
    raw_token, token_hash = _generate_token()
    token = PasswordResetToken(
        user_id=user_id,
        token_hash=token_hash,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=hours),
    )
    db.add(token)
    db.commit()
    return raw_token


def reset_password(db: DBSession, raw_token: str, new_password: str) -> bool:
    """Reset password using a valid reset token and invalidate all active sessions."""
    token_hash = _hash_token(raw_token)
    token = db.query(PasswordResetToken).filter_by(token_hash=token_hash, used=False).first()
    if not token or _is_expired(token.expires_at):
        return False
    user = db.get(User, token.user_id)
    if user:
        user.password_hash = hash_password(new_password)
        token.used = True
        # Security requirement: Invalidate all existing user sessions upon password reset
        db.query(Session).filter_by(user_id=user.id, revoked=False).update({"revoked": True})
        db.commit()
        return True
    return False
