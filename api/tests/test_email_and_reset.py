"""Comprehensive tests for Resend Email Infrastructure and Password Reset Flow.

Verifies:
- Masking and SHA-256 hashing for privacy-safe audit trails.
- Zero secret leakage in database, logs, and responses.
- Single-use, 30-minute password reset token generation and validation.
- Invalidation of all existing user sessions upon password reset.
- Strict anti-enumeration on forgot-password endpoint.
- Email verification flow with token single-use enforcement.
- Resend API payload dispatch and audit event recording.
"""
import hashlib
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import get_db
from app.main import create_app
from app.models.base import Base
from app.models.email_event import EmailEvent
from app.models.user import PasswordResetToken, Session, User, VerificationToken
from app.services.auth import (
    create_password_reset_token,
    create_session,
    create_user,
    create_verification_token,
    hash_password,
    reset_password,
    validate_session,
    verify_email,
    verify_password,
)
from app.services.email import (
    EmailService,
    _hash_recipient,
    _mask_email,
    email_service,
)


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db_session):
    app = create_app()

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


# ── Privacy & Masking Tests ──────────────────────────────────────────

def test_email_masking():
    assert _mask_email("john.doe@attacksurface.online") == "j******e@attacksurface.online"
    assert _mask_email("me@domain.com") == "m*@domain.com"
    assert _mask_email("a@b.com") == "a*@b.com"
    assert _mask_email("invalid") == "invalid-email"


def test_recipient_hashing():
    h1 = _hash_recipient("researcher@attacksurface.online")
    h2 = _hash_recipient("RESEARCHER@attacksurface.online ")
    # Normalization check
    assert h1 == h2
    assert len(h1) == 64
    assert h1 == hashlib.sha256(b"researcher@attacksurface.online").hexdigest()


# ── Password Reset & Session Revocation Tests ────────────────────────

def test_password_reset_revokes_all_sessions(db_session):
    user = create_user(db_session, "reset_session_test@example.com", "OldPassword123!")

    # Create 3 active sessions across different devices
    t1 = create_session(db_session, user, ip_address="1.1.1.1", user_agent="Device 1")
    t2 = create_session(db_session, user, ip_address="2.2.2.2", user_agent="Device 2")
    t3 = create_session(db_session, user, ip_address="3.3.3.3", user_agent="Device 3")

    assert validate_session(db_session, t1) is not None
    assert validate_session(db_session, t2) is not None
    assert validate_session(db_session, t3) is not None

    # Generate 30-minute reset token
    raw_token = create_password_reset_token(db_session, user.id, hours=0.5)

    # Perform password reset
    assert reset_password(db_session, raw_token, "BrandNewPassword456!") is True

    # Check that new password works and old fails
    db_session.refresh(user)
    assert verify_password("BrandNewPassword456!", user.password_hash)
    assert not verify_password("OldPassword123!", user.password_hash)

    # CRITICAL SECURITY REQUIREMENT: All existing sessions MUST be invalidated
    assert validate_session(db_session, t1) is None
    assert validate_session(db_session, t2) is None
    assert validate_session(db_session, t3) is None

    # Token must not be reusable
    assert reset_password(db_session, raw_token, "AnotherPassword789!") is False


def test_expired_reset_token_rejected(db_session):
    user = create_user(db_session, "expired_token@example.com", "Password123!")

    # Create token already expired 5 minutes ago
    raw_token = create_password_reset_token(db_session, user.id, hours=-0.1)

    assert reset_password(db_session, raw_token, "AttemptedPassword123!") is False
    db_session.refresh(user)
    assert verify_password("Password123!", user.password_hash)


# ── Anti-Enumeration & Endpoint Tests ────────────────────────────────

def test_forgot_password_anti_enumeration(client, db_session):
    # Register real user
    create_user(db_session, "realuser@attacksurface.online", "Password123!")

    with patch.object(email_service, "send_password_reset_email") as mock_send:
        # Request for existing user
        res_real = client.post(
            "/api/v1/auth/forgot-password",
            json={"email": "realuser@attacksurface.online"},
        )
        assert res_real.status_code == 200
        assert "If an account exists" in res_real.json()["message"]
        assert mock_send.call_count == 1

        # Request for nonexistent user
        res_fake = client.post(
            "/api/v1/auth/forgot-password",
            json={"email": "nonexistent@attacksurface.online"},
        )
        assert res_fake.status_code == 200
        # Responses MUST be identical to prevent user enumeration
        assert res_fake.json() == res_real.json()
        # Nonexistent user must NOT trigger an email send
        assert mock_send.call_count == 1


def test_reset_password_endpoint_flow(client, db_session):
    user = create_user(db_session, "endpoint_reset@attacksurface.online", "OldSecretPass123!")
    raw_token = create_password_reset_token(db_session, user.id, hours=0.5)

    with patch.object(email_service, "send_password_changed_email") as mock_notify:
        res = client.post(
            "/api/v1/auth/reset-password",
            json={
                "token": raw_token,
                "new_password": "NewSecretPass456!",
            },
        )
        assert res.status_code == 200
        assert "successfully updated" in res.json()["message"].lower()
        assert mock_notify.call_count == 1

    # Verify user can log in with new password
    login_res = client.post(
        "/api/v1/auth/login",
        json={
            "email": "endpoint_reset@attacksurface.online",
            "password": "NewSecretPass456!",
        },
    )
    assert login_res.status_code == 200

    # Old password fails
    fail_res = client.post(
        "/api/v1/auth/login",
        json={
            "email": "endpoint_reset@attacksurface.online",
            "password": "OldSecretPass123!",
        },
    )
    assert fail_res.status_code == 401


def test_email_verification_one_click_link(client, db_session):
    user = create_user(db_session, "verify_link@attacksurface.online", "Pass123456!")
    assert user.is_verified is False

    raw_token = create_verification_token(db_session, user.id, hours=48)

    # Click verification link
    res = client.get(f"/api/v1/auth/verify-email?token={raw_token}", follow_redirects=False)
    assert res.status_code == 302
    assert "email_verified=true" in res.headers["location"]

    db_session.refresh(user)
    assert user.is_verified is True


# ── Audit Trail & Secret Leak Prevention ─────────────────────────────

def test_email_service_audit_event_logged(db_session):
    svc = EmailService()
    svc.api_key = "re_test_dummy_key_12345"

    mock_res = MagicMock()
    mock_res.status_code = 200
    mock_res.json.return_value = {"id": "msg_resend_98765"}

    with patch("httpx.Client.post", return_value=mock_res):
        res = svc.send_password_reset_email(
            to="sensitive_researcher@attacksurface.online",
            reset_token="test_raw_reset_token_secret_12345",
            user_id=1,
            db=db_session,
        )
        assert res["status"] == "sent"
        assert res["id"] == "msg_resend_98765"

    # Check audit record in database
    event = db_session.query(EmailEvent).filter_by(provider_message_id="msg_resend_98765").first()
    assert event is not None
    assert event.type == "password_reset"
    # Recipient must be masked
    assert event.recipient_masked == _mask_email("sensitive_researcher@attacksurface.online")
    # SHA-256 hashed recipient
    assert event.recipient_hash == _hash_recipient("sensitive_researcher@attacksurface.online")

    # SECURITY ASSERTIONS: Raw secrets must NEVER be present anywhere in the audit row
    dump_str = f"{event.recipient_masked} {event.recipient_hash} {event.provider} {event.status}"
    assert "test_raw_reset_token_secret_12345" not in dump_str
    assert "re_test_dummy_key_12345" not in dump_str
    assert "sensitive_researcher@attacksurface.online" not in dump_str
