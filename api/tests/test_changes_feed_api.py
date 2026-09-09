"""Unit and integration tests for the Changes Feed API and statistics."""
from __future__ import annotations

import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import get_db
from app.main import app
from app.models import Base, Change, Snapshot, Target, User
from app.routers.deps import get_current_user

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
def mock_user(db_session):
    user = User(
        email="researcher@ast.test",
        password_hash="mockhash",
        role="RESEARCHER",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture(scope="function")
def client(db_session, mock_user):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    def override_get_current_user():
        return mock_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


def test_changes_stats_endpoint_empty(client):
    """Test /api/v1/changes/stats when no changes exist."""
    response = client.get("/api/v1/changes/stats")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["critical"] == 0
    assert data["high"] == 0
    assert data["critical_high"] == 0
    assert data["unique_targets"] == 0
    assert data["categories"] == {}


def test_changes_stats_and_list_with_data(client, db_session):
    """Test /api/v1/changes and /stats with populated database."""
    target = Target(
        domain="security-target.io",
        company_name="Target Security Corp",
        authorization_confirmed=True,
        monitoring_status="active",
    )
    db_session.add(target)
    db_session.commit()
    db_session.refresh(target)

    snapshot = Snapshot(target_id=target.id, status="completed")
    db_session.add(snapshot)
    db_session.commit()
    db_session.refresh(snapshot)

    c1 = Change(
        target_id=target.id,
        snapshot_id=snapshot.id,
        fingerprint="fp-test-001",
        category="repository_activity",
        priority="CRITICAL",
        status="investigating",
        summary="New critical secrets committed to public repository.",
        researcher_note="Verified commit hash on main branch",
        source_url="https://github.com/target-corp/public-repo",
        confidence=0.95,
        security_relevance=92,
        detected_at=datetime.now(timezone.utc),
    )
    c2 = Change(
        target_id=target.id,
        snapshot_id=snapshot.id,
        fingerprint="fp-test-002",
        category="external_repository_reference",
        priority="LOW",
        status="interesting",
        summary="External third-party reference found in issue tracker.",
        researcher_note="Low impact reference",
        source_url="https://github.com/target-corp/sdk",
        confidence=0.3,
        security_relevance=20,
        detected_at=datetime.now(timezone.utc),
    )
    db_session.add_all([c1, c2])
    db_session.commit()

    # 1. Test stats
    stats_res = client.get("/api/v1/changes/stats")
    assert stats_res.status_code == 200
    stats = stats_res.json()
    assert stats["total"] == 2
    assert stats["critical"] == 1
    assert stats["critical_high"] == 1
    assert stats["investigating"] == 1
    assert stats["interesting"] == 1
    assert stats["unique_targets"] == 1
    assert stats["categories"]["repository_activity"] == 1
    assert stats["categories"]["external_repository_reference"] == 1

    # 2. Test list all changes
    list_res = client.get("/api/v1/changes")
    assert list_res.status_code == 200
    items = list_res.json()
    assert len(items) == 2
    assert items[0]["target_domain"] == "security-target.io"
    assert items[0]["company_name"] == "Target Security Corp"

    # 3. Test filtering by priority
    crit_res = client.get("/api/v1/changes?priority=CRITICAL")
    assert crit_res.status_code == 200
    assert len(crit_res.json()) == 1
    assert crit_res.json()[0]["priority"] == "CRITICAL"

    # 4. Test filtering by category
    cat_res = client.get("/api/v1/changes?category=repository_activity")
    assert cat_res.status_code == 200
    assert len(cat_res.json()) == 1
    assert cat_res.json()[0]["category"] == "repository_activity"

    # 5. Test search filter
    search_res = client.get("/api/v1/changes?search=secrets")
    assert search_res.status_code == 200
    assert len(search_res.json()) == 1
    assert "secrets" in search_res.json()[0]["summary"]

    # 6. Test status update
    update_res = client.post(
        f"/api/v1/changes/{c1.id}/status",
        json={"status": "resolved"},
    )
    assert update_res.status_code == 200
    assert update_res.json()["status"] == "resolved"
