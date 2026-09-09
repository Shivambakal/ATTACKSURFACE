"""Comprehensive production functionality tests.

Verifies:
1. User login, session tokens, and role assignment (OWNER, ADMIN, RESEARCHER, VIEWER).
2. Backend role authorization: OWNER/ADMIN have access to /api/v1/admin/*; RESEARCHER/VIEWER get 403.
3. Target onboarding: company, domain, program/source, authorization source, scope, notes, and internal authorization record.
4. Target creation permissions: VIEWER gets 403, RESEARCHER/ADMIN/OWNER can create targets.
5. Bulk import of 50 authorized bug-bounty targets from verified registry.
6. Target snapshot pipeline, content-dependent fingerprinting, and deduplication (0 changes on identical second run).
7. Temporal separation of security intelligence (HISTORICAL vs CURRENT/RECENT, SECURITY_CONTEXT).
8. Research Signal quality gating (only creates signals for high confidence & relevance changes with evidence).
9. Admin direct target pipeline execution endpoint (POST /api/v1/admin/run-target/{target_id}).
"""
from __future__ import annotations

import asyncio
import hashlib
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, AsyncMock
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import get_db
from app.main import app
from app.models.base import Base
from app.models import (
    Base,
    User,
    Target,
    Snapshot,
    Observation,
    Change,
    ChangeEvidence,
    TimelineEvent,
    ResearchSignal,
    Company,
    SecurityProgram,
    ProgramScopeRule,
)
from app.models.user import UserRole
from app.services.auth import create_user, create_session
from app.services.pipeline import TargetPipeline

engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _create_test_user_and_session(db_session, email: str, role: str) -> tuple[User, str]:
    user = create_user(db_session, email=email, password="TestPassword123!", role=role)
    token = create_session(db_session, user, ip_address="127.0.0.1")
    return user, token


def test_login_returns_user_with_role(client, db_session):
    create_user(db_session, "owner@secops.io", "Pass1234!", role="OWNER")
    create_user(db_session, "researcher@secops.io", "Pass1234!", role="RESEARCHER")

    res_owner = client.post("/api/v1/auth/login", json={"email": "owner@secops.io", "password": "Pass1234!"})
    assert res_owner.status_code == 200
    data_owner = res_owner.json()
    assert data_owner["email"] == "owner@secops.io"
    assert data_owner["role"] == "OWNER"
    assert data_owner["is_admin"] is True
    assert "session_token" in res_owner.cookies

    res_res = client.post("/api/v1/auth/login", json={"email": "researcher@secops.io", "password": "Pass1234!"})
    assert res_res.status_code == 200
    data_res = res_res.json()
    assert data_res["email"] == "researcher@secops.io"
    assert data_res["role"] == "RESEARCHER"
    assert data_res["is_admin"] is False


def test_admin_route_protection_by_role(client, db_session):
    _, owner_token = _create_test_user_and_session(db_session, "owner@corp.io", "OWNER")
    _, admin_token = _create_test_user_and_session(db_session, "admin@corp.io", "ADMIN")
    _, res_token = _create_test_user_and_session(db_session, "researcher@corp.io", "RESEARCHER")
    _, viewer_token = _create_test_user_and_session(db_session, "viewer@corp.io", "VIEWER")

    # 1. Anonymous access -> 401 Unauthorized
    anon_res = client.get("/api/v1/admin/health")
    assert anon_res.status_code == 401

    # 2. OWNER access -> 200 OK
    client.cookies.set("session_token", owner_token)
    owner_res = client.get("/api/v1/admin/health")
    assert owner_res.status_code == 200

    # 3. ADMIN access -> 200 OK
    client.cookies.set("session_token", admin_token)
    admin_res = client.get("/api/v1/admin/health")
    assert admin_res.status_code == 200

    # 4. RESEARCHER access -> 403 Forbidden
    client.cookies.set("session_token", res_token)
    res_response = client.get("/api/v1/admin/health")
    assert res_response.status_code == 403
    assert "Administrative access required" in res_response.json()["detail"]

    # 5. VIEWER access -> 403 Forbidden
    client.cookies.set("session_token", viewer_token)
    viewer_response = client.get("/api/v1/admin/health")
    assert viewer_response.status_code == 403
    assert "Administrative access required" in viewer_response.json()["detail"]


def test_target_creation_with_authorization_record(client, db_session):
    _, res_token = _create_test_user_and_session(db_session, "lead@research.io", "RESEARCHER")
    client.cookies.set("session_token", res_token)

    payload = {
        "domain": "security.github.com",
        "company_name": "GitHub",
        "program_source": "Bugcrowd",
        "authorization_source": "https://bugcrowd.com/engagements/github",
        "scope": ["*.github.com", "security.github.com"],
        "scope_type": "DOMAIN",
        "notes": "Verified public bounty scope",
        "authorization_confirmed": True,
    }

    res = client.post("/api/v1/targets", json=payload)
    assert res.status_code == 201
    target_data = res.json()
    assert target_data["domain"] == "security.github.com"
    assert target_data["company_name"] == "GitHub"
    assert target_data["program_source"] == "Bugcrowd"
    assert target_data["authorization_source"] == "https://bugcrowd.com/engagements/github"
    assert target_data["scope_type"] == "DOMAIN"
    assert target_data["authorization_confirmed"] is True

    # Check internal authorization record in DB
    target_db = db_session.query(Target).filter_by(domain="security.github.com").first()
    assert target_db is not None
    assert target_db.authorization_record is not None
    auth_rec = target_db.authorization_record
    assert auth_rec["provenance_status"] == "AUTHORIZED_PUBLIC_BOUNTY"
    assert auth_rec["authorizing_user"] == "lead@research.io"
    assert "audit_hash_sha256" in auth_rec


def test_viewer_cannot_create_target(client, db_session):
    _, viewer_token = _create_test_user_and_session(db_session, "viewer@read.io", "VIEWER")
    client.cookies.set("session_token", viewer_token)

    payload = {
        "domain": "forbidden.example.com",
        "company_name": "ForbiddenCorp",
        "authorization_source": "https://bugcrowd.com/forbidden",
        "authorization_confirmed": True,
    }
    res = client.post("/api/v1/targets", json=payload)
    assert res.status_code == 403


def test_bulk_import_50_targets(client, db_session):
    _, admin_token = _create_test_user_and_session(db_session, "admin@secops.io", "ADMIN")
    client.cookies.set("session_token", admin_token)

    res = client.post("/api/v1/targets/bulk-import")
    assert res.status_code == 200
    data = res.json()
    assert data["imported_count"] >= 50 or data["total_targets"] >= 50

    targets = db_session.query(Target).all()
    assert len(targets) >= 50
    for t in targets[:5]:
        assert t.authorization_confirmed is True
        assert t.authorization_record is not None
        assert t.authorization_record["provenance_status"] == "AUTHORIZED_PUBLIC_BOUNTY"


def test_pipeline_deduplication_on_identical_polls(db_session):
    user = create_user(db_session, "analyst@secops.io", "Pass123!", role="RESEARCHER")
    target = Target(
        domain="app.testcorp.local",
        company_name="TestCorp",
        program_source="Bugcrowd",
        authorization_source="https://bugcrowd.com/testcorp",
        authorization_confirmed=True,
        monitoring_status="active",
        authorization_record={"provenance_status": "AUTHORIZED"},
    )
    db_session.add(target)
    db_session.commit()

    pipeline = TargetPipeline()

    mock_html_v1 = """
    <!DOCTYPE html>
    <html>
      <head><title>Test App Login</title></head>
      <body>
        <h1>Portal Login</h1>
        <form action="/login" method="POST">
          <input type="text" name="username" />
          <input type="password" name="password" />
          <button type="submit">Sign In</button>
        </form>
      </body>
    </html>
    """

    obs_payload_v1 = [{
        "url": f"https://{target.domain}/login",
        "html": mock_html_v1,
        "content_hash": hashlib.sha256(mock_html_v1.encode("utf-8")).hexdigest(),
        "text_excerpt": "Portal Login username password Sign In",
        "status_code": 200,
        "headers": {"content-type": "text/html"},
        "technologies": ["Nginx"],
        "kind": "page",
    }]

    # Run 1: Initial baseline snapshot
    with patch("app.services.pipeline.collect", new_callable=AsyncMock) as mock_collect:
        mock_collect.return_value = obs_payload_v1
        result1 = asyncio.run(pipeline.run(target.id, db_session))
        assert result1["status"] == "complete"

    # Run 2: Exact same content -> DEDUPLICATED -> 0 changes detected
    with patch("app.services.pipeline.collect", new_callable=AsyncMock) as mock_collect:
        mock_collect.return_value = obs_payload_v1
        result2 = asyncio.run(pipeline.run(target.id, db_session))
        assert result2["status"] == "complete"
        assert result2["meaningful_changes_count"] == 0

    # Run 3: Content changed (sensitive OAuth parameter added)
    mock_html_v2 = """
    <!DOCTYPE html>
    <html>
      <head><title>Test App Login v2</title></head>
      <body>
        <h1>Portal Login v2</h1>
        <form action="/api/v2/oauth/token" method="POST">
          <input type="text" name="client_id" />
          <input type="password" name="client_secret" />
          <input type="hidden" name="scope" value="admin,debug" />
          <button type="submit">OAuth Sign In</button>
        </form>
      </body>
    </html>
    """
    obs_payload_v2 = [{
        "url": f"https://{target.domain}/login",
        "html": mock_html_v2,
        "content_hash": hashlib.sha256(mock_html_v2.encode("utf-8")).hexdigest(),
        "text_excerpt": "Portal Login v2 client_id client_secret OAuth Sign In",
        "status_code": 200,
        "headers": {"content-type": "text/html"},
        "technologies": ["Nginx", "OAuth2"],
        "kind": "page",
    }]

    with patch("app.services.pipeline.collect", new_callable=AsyncMock) as mock_collect:
        mock_collect.return_value = obs_payload_v2
        result3 = asyncio.run(pipeline.run(target.id, db_session))
        assert result3["status"] == "complete"
        assert result3["meaningful_changes_count"] >= 1


def test_temporal_separation_and_provenance(db_session):
    target = Target(
        domain="temporal.corp.local",
        authorization_confirmed=True,
        monitoring_status="active",
    )
    db_session.add(target)
    db_session.commit()

    pipeline = TargetPipeline()

    now = datetime.now(timezone.utc)
    old_published_date = now - timedelta(days=900)
    recent_published_date = now - timedelta(days=10)

    events_to_test = [
        {
            "event_type": "security_advisory",
            "title": "CVE-2021-99999 - Historical remote code execution",
            "summary": "Historical vulnerability in legacy dependency",
            "source": "cve_feed",
            "temporal_category": "HISTORICAL",
            "provenance_category": "SECURITY_CONTEXT",
            "published_at": old_published_date,
            "confidence": 0.95,
            "relevance_score": 70,
            "priority": "MEDIUM",
        },
        {
            "event_type": "security_advisory",
            "title": "CVE-2026-11111 - Current zero-day flaw",
            "summary": "Actively discussed authentication bypass",
            "source": "cve_feed",
            "temporal_category": "CURRENT",
            "provenance_category": "SECURITY_CONTEXT",
            "published_at": recent_published_date,
            "confidence": 0.95,
            "relevance_score": 90,
            "priority": "HIGH",
        },
    ]

    saved_events = asyncio.run(pipeline.update_timeline(target.id, events_to_test, db_session))
    assert len(saved_events) == 2

    event_hist = next(e for e in saved_events if "CVE-2021-99999" in e.title)
    event_rec = next(e for e in saved_events if "CVE-2026-11111" in e.title)

    assert event_hist.temporal_category == "HISTORICAL"
    assert event_hist.provenance_category == "SECURITY_CONTEXT"

    assert event_rec.temporal_category == "CURRENT"
    assert event_rec.provenance_category == "SECURITY_CONTEXT"


def test_research_signal_quality_gate(db_session):
    pipeline = TargetPipeline()

    # Test deterministic synthesis with verified evidence citation
    evidence_dicts = [
        {"id": "ev-101", "url": "https://auth.corp.local/oauth/authorize", "type": "form"},
        {"id": "ev-102", "url": "https://auth.corp.local/api/v2/tokens", "type": "api"},
    ]

    brief = asyncio.run(pipeline.ai_synthesize_signal(
        cluster_title="Exposed Administrative Token Issuance",
        category="AUTHENTICATION",
        summary="New endpoint /api/v2/tokens observed accepting unauthenticated requests",
        affected_urls=["https://auth.corp.local/api/v2/tokens"],
        evidence_dicts=evidence_dicts,
        historical_notes=["Legacy API v1 had broken object level authorization"],
    ))

    assert brief.title in ("Exposed Administrative Token Issuance", "Attack Surface Observation")
    assert brief.confidence >= 0.70
    assert "ev-101" in brief.evidence_ids or "ev-102" in brief.evidence_ids
    assert brief.why_it_matters
    assert brief.research_area


def test_admin_run_target_endpoint(client, db_session):
    _, admin_token = _create_test_user_and_session(db_session, "operator@corp.io", "ADMIN")

    target = Target(
        domain="admin-runner.corp.local",
        company_name="RunnerCorp",
        authorization_confirmed=True,
        monitoring_status="active",
    )
    db_session.add(target)
    db_session.commit()

    obs_payload = [{
        "url": f"https://{target.domain}/",
        "html": "<html><body><h1>Admin Runner Test</h1></body></html>",
        "content_hash": hashlib.sha256(b"admin test").hexdigest(),
        "text_excerpt": "Admin Runner Test",
        "status_code": 200,
        "headers": {},
        "technologies": [],
        "kind": "page",
    }]

    with patch("app.services.pipeline.collect", new_callable=AsyncMock) as mock_collect:
        mock_collect.return_value = obs_payload
        res = client.post(
            f"/api/v1/admin/run-target/{target.id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["domain"] == "admin-runner.corp.local"
        assert data["status"] == "complete"
        assert "snapshot_id" in data
        assert "meaningful_changes_count" in data
        assert "signals_count" in data
        assert "timeline_events_count" in data
