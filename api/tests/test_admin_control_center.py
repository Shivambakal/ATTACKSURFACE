"""Unit and integration tests for the Reality-First Admin Control Center."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import get_db
from app.main import app
from app.models import (
    Base,
    Company,
    CompanySource,
    NormalizedSourceDocument,
    RawSourceSnapshot,
    ResearchSignal,
    SecurityAdvisory,
    SourceCollectionRun,
    TimelineEvent,
)
from app.services.admin_service import AdminObservabilityService

# SQLite in-memory test engine
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
    from app.services.auth import create_user, create_session
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        admin_user = create_user(db_session, "admin@control.io", "Pass1234!", role="ADMIN")
        token = create_session(db_session, admin_user)
        test_client.cookies.set("session_token", token)
        yield test_client
    app.dependency_overrides.clear()


def test_admin_rbac_protection(db_session):
    """Verifies that unauthenticated gets 401 and researcher gets 403."""
    from app.services.auth import create_user, create_session
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        # Anonymous -> 401
        res_anon = c.get("/api/v1/admin/health")
        assert res_anon.status_code == 401

        # Researcher -> 403
        res_user = create_user(db_session, "res@control.io", "Pass1234!", role="RESEARCHER")
        token = create_session(db_session, res_user)
        c.cookies.set("session_token", token)
        res_auth = c.get("/api/v1/admin/health")
        assert res_auth.status_code == 403
    app.dependency_overrides.clear()


def test_admin_system_health(client, db_session):
    """Verifies /api/v1/admin/health returns valid system health structure."""
    response = client.get("/api/v1/admin/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "database" in data
    assert "redis" in data
    assert "workers" in data
    assert data["database"]["healthy"] is True
    assert isinstance(data["database"]["latency_ms"], (int, float))


def test_admin_pipeline_stages(client, db_session):
    """Verifies all 9 pipeline stages are computed and returned."""
    # Seed 1 source
    co = Company(name="Test Corp", canonical_domain="testcorp.example")
    db_session.add(co)
    db_session.flush()

    source = CompanySource(
        company_id=co.id,
        name="Test Feed",
        source_url="https://testcorp.example/feed.xml",
        source_type="OFFICIAL_BLOG",
        authority_level="OFFICIAL_RELEASE",
        parser_strategy="feed_rss_atom",
        feed_url="https://testcorp.example/feed.xml",
    )
    db_session.add(source)
    db_session.commit()

    response = client.get("/api/v1/admin/pipeline")
    assert response.status_code == 200
    data = response.json()
    assert "stages" in data
    assert len(data["stages"]) == 9
    assert data["stages"][0]["name"] == "Source Registry"
    assert data["stages"][0]["count"] == 1
    assert data["pipeline_operational"] is True


def test_admin_provider_truth(client, db_session):
    """Verifies strict truth rules: CISA KEV, GitHub, Gemini, NVIDIA, Censys, Shodan."""
    response = client.get("/api/v1/admin/providers")
    assert response.status_code == 200
    providers = response.json()
    assert isinstance(providers, list)
    assert len(providers) >= 7

    names = {p["name"]: p for p in providers}
    assert "CISA KEV Catalog" in names
    assert "Google Gemini Intelligence" in names
    assert "GitHub Releases & Commits" in names

    # Gemini quota check (must be Quota unknown or tier-based, never fake number)
    gemini = names["Google Gemini Intelligence"]
    assert "Quota unknown" in gemini["quota_info"]


def test_admin_queue_telemetry(client, db_session):
    """Verifies queue depths are monitored across all 9 priority queues."""
    response = client.get("/api/v1/admin/queues")
    assert response.status_code == 200
    data = response.json()
    assert "queues" in data
    assert len(data["queues"]) == 9
    queue_names = {q["name"] for q in data["queues"]}
    assert "p0_critical" in queue_names
    assert "p1_official" in queue_names
    assert "p2_standard" in queue_names
    assert "snapshots" in queue_names


def test_admin_change_counters(client, db_session):
    """Verifies change counter windows today, 24h, 7d, 30d."""
    response = client.get("/api/v1/admin/change-counters")
    assert response.status_code == 200
    data = response.json()
    assert "today" in data
    assert "last_24h" in data
    assert "last_7d" in data
    assert "last_30d" in data


def test_admin_db_stats(client, db_session):
    """Verifies row counts across core models."""
    response = client.get("/api/v1/admin/db-stats")
    assert response.status_code == 200
    data = response.json()
    assert "companies" in data
    assert "company_sources" in data
    assert "raw_source_snapshots" in data
    assert "normalized_source_documents" in data
    assert "timeline_events" in data
    assert "research_signals" in data


def test_admin_activity_and_errors(client, db_session):
    """Verifies activity stream and error center endpoints."""
    res_act = client.get("/api/v1/admin/activity")
    assert res_act.status_code == 200
    assert isinstance(res_act.json(), list)

    res_err = client.get("/api/v1/admin/errors")
    assert res_err.status_code == 200
    data_err = res_err.json()
    assert "failed_runs_24h_count" in data_err
    assert "degraded_sources_count" in data_err


def test_admin_pipeline_proof(client, db_session):
    """Verifies pipeline proof inspector format before any run is executed."""
    response = client.get("/api/v1/admin/proof")
    assert response.status_code == 200
    data = response.json()
    assert "proof_available" in data
    assert data["proof_available"] is False
