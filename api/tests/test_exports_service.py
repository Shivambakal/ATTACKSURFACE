"""Unit and security tests for Researcher Export Service."""
from __future__ import annotations

import os
import pytest
from app.models.user import User
from app.services.export_service import ExportService


def test_export_package_generation(db_session):
    """Verify that export creates chunked artifact with SHA-256 checksum and download token."""
    # Ensure test user
    user = db_session.query(User).filter(User.email == "test_export@example.com").first()
    if not user:
        user = User(email="test_export@example.com", role="RESEARCHER")
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

    service = ExportService(db_session)
    job = service.create_export_job(
        user_id=user.id,
        export_type="COMPANY_INTELLIGENCE",
        export_format="JSON",
    )
    assert job.status == "QUEUED"
    assert job.download_token is not None

    # Execute
    job = service.execute_job(job.id)
    assert job.status == "READY"
    assert job.checksum_sha256 is not None
    assert len(job.checksum_sha256) == 64
    assert job.file_path is not None
    assert os.path.exists(job.file_path)


def test_export_ownership_and_idor_protection(db_session):
    """Verify that a user cannot download an export created by another user."""
    u1 = db_session.query(User).filter(User.email == "u1@example.com").first()
    if not u1:
        u1 = User(email="u1@example.com", role="RESEARCHER")
        db_session.add(u1)

    u2 = db_session.query(User).filter(User.email == "u2@example.com").first()
    if not u2:
        u2 = User(email="u2@example.com", role="RESEARCHER")
        db_session.add(u2)
    db_session.commit()

    service = ExportService(db_session)
    job = service.create_export_job(user_id=u1.id, export_type="RESEARCH_SIGNALS", export_format="CSV")
    job = service.execute_job(job.id)

    # u1 can access
    job_auth = service.get_export_by_token(job.download_token, user_id=u1.id, is_admin=False)
    assert job_auth.id == job.id

    # u2 denied access (IDOR protection)
    with pytest.raises(PermissionError, match="Access denied"):
        service.get_export_by_token(job.download_token, user_id=u2.id, is_admin=False)
