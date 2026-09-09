"""Unit tests for TargetPipeline, background RQ jobs, and demo seed data."""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.base import Base, utcnow
from app.models import (
    Target,
    Snapshot,
    Observation,
    Change,
    ChangeEvidence,
    TimelineEvent,
    Evidence,
    Asset,
    Technology,
    Feature,
    ResearchTask,
    Alert,
    User,
)
from app.services.pipeline import TargetPipeline
from app.services.diffing import Diff
from app.demo.seed import seed_demo_data
from app.jobs.snapshot_job import run_snapshot
from app.jobs.provider_job import refresh_provider_data
from app.jobs.alert_job import send_daily_digest, send_weekly_digest


@pytest.fixture
def test_db():
    """Provide an in-memory SQLite database session for unit tests."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()


@pytest.mark.asyncio
async def test_discover_sources():
    pipeline = TargetPipeline()
    target = Target(id=1, domain="example.com")
    sources = await pipeline.discover_sources(target)

    assert len(sources) >= 4
    types = {s["type"] for s in sources}
    assert "web" in types
    assert "provider" in types
    providers = {s.get("provider") for s in sources if s.get("provider")}
    assert "github" in providers
    assert "osv" in providers


@pytest.mark.asyncio
async def test_deduplicate_records():
    pipeline = TargetPipeline()
    records = [
        {"url": "https://example.com/a", "content_hash": "hash1", "title": "Page A"},
        {"url": "https://example.com/a", "content_hash": "hash1", "title": "Page A Dupe"},
        {"url": "https://example.com/b", "content_hash": "hash2", "title": "Page B"},
    ]
    deduped = await pipeline.deduplicate(records)
    assert len(deduped) == 2
    urls = [r["url"] for r in deduped]
    assert urls == ["https://example.com/a", "https://example.com/b"]


@pytest.mark.asyncio
async def test_classify_and_assess_security_relevance():
    pipeline = TargetPipeline()

    obs_api = SimpleNamespace(
        url="https://example.com/api/v1/auth",
        title="API Authentication",
        text_excerpt="OAuth login and token verification endpoints",
        technologies=["nginx"],
    )
    diff = Diff(kind="page_added", url="https://example.com/api/v1/auth", before=None, after=obs_api)

    classified = await pipeline.classify_changes([diff])
    assert len(classified) == 1
    assert "api" in classified[0]["category"] or "auth" in classified[0]["category"]

    scored = await pipeline.assess_security_relevance(classified)
    assert len(scored) == 1
    item = scored[0]
    assert item["security_relevance"] >= 70
    assert item["priority"] in ("HIGH", "CRITICAL")
    assert "category_base" in item["score_factors"]


@pytest.mark.asyncio
async def test_update_timeline_and_generate_alerts(test_db):
    pipeline = TargetPipeline()

    user = User(email="test@researcher.local", is_active=True, is_verified=True)
    test_db.add(user)
    test_db.flush()

    target = Target(user_id=user.id, domain="testtarget.local", authorization_confirmed=True)
    test_db.add(target)
    test_db.flush()

    events_data = [
        {
            "event_type": "change_new_api_documentation",
            "title": "New Public API Exposed",
            "summary": "Detected /api/v2 endpoint with potential BOLA risk.",
            "source": "collector",
            "source_url": "https://testtarget.local/api/v2",
            "confidence": 0.95,
            "relevance_score": 85,
            "priority": "HIGH",
            "metadata": {"api_version": "v2"},
        },
        {
            "event_type": "page_updated",
            "title": "Cosmetic text update",
            "summary": "Minor spelling fix on homepage.",
            "source": "collector",
            "source_url": "https://testtarget.local",
            "confidence": 0.90,
            "relevance_score": 20,
            "priority": "LOW",
        },
    ]

    events = await pipeline.update_timeline(target.id, events_data, test_db)
    assert len(events) == 2
    assert events[0].id is not None
    assert events[0].priority == "HIGH"

    alerts = await pipeline.generate_alerts(user.id, events, test_db)
    assert len(alerts) == 1
    assert alerts[0].title == "New Public API Exposed"
    assert alerts[0].priority == "HIGH"
    assert alerts[0].user_id == user.id


def test_seed_demo_data(test_db):
    result = seed_demo_data(test_db)
    assert result["status"] == "seeded"
    assert result["target_domain"] == "acmecloud.example.com"
    assert result["assets_count"] == 4
    assert result["technologies_count"] == 4
    assert result["features_count"] == 4
    assert result["changes_count"] == 4
    assert result["timeline_events_count"] >= 5
    assert result["research_tasks_count"] == 2
    assert result["alerts_count"] >= 2

    # Verify database contents
    user = test_db.query(User).filter(User.email == "demo@attacksurface.local").first()
    assert user is not None
    assert user.profile is not None
    assert "[DEMO DATA]" in user.profile.bio

    target = test_db.query(Target).filter(Target.domain == "acmecloud.example.com").first()
    assert target is not None
    assert target.monitoring_status == "active"

    assets = test_db.query(Asset).filter(Asset.target_id == target.id).all()
    assert len(assets) == 4
    asset_names = {a.name for a in assets}
    assert "Acme Web App" in asset_names
    assert "Acme REST API" in asset_names
    assert "Acme Admin Panel" in asset_names
    assert "Acme Mobile API" in asset_names

    changes = test_db.query(Change).filter(Change.target_id == target.id).all()
    assert len(changes) == 4
    for c in changes:
        assert "[DEMO DATA]" in c.summary
        assert "[DEMO DATA]" in c.researcher_note
        assert len(c.evidence) > 0

    tasks = test_db.query(ResearchTask).filter(ResearchTask.target_id == target.id).all()
    assert len(tasks) == 2
    task_titles = {t.title for t in tasks}
    assert "[DEMO DATA] Investigate new admin panel" in task_titles
    assert "[DEMO DATA] Review OAuth flow changes" in task_titles

    # Verify idempotency by running seed a second time
    result2 = seed_demo_data(test_db)
    assert result2["status"] == "seeded"
    assert test_db.query(Target).filter(Target.domain == "acmecloud.example.com").count() == 1


@patch("app.jobs.snapshot_job.SessionLocal")
def test_run_snapshot_job(mock_session_local, test_db):
    mock_session_local.return_value = test_db

    # Call with non-existent target to test graceful error handling
    res = run_snapshot(99999)
    assert res["status"] == "failed"
    assert "does not exist" in res["error"]


@patch("app.jobs.provider_job.SessionLocal")
def test_refresh_provider_data_job(mock_session_local, test_db):
    mock_session_local.return_value = test_db

    res = refresh_provider_data(99999, "github")
    assert res["status"] == "error"
    assert "not found" in res["message"]


@patch("app.jobs.alert_job.SessionLocal")
def test_digest_jobs(mock_session_local, test_db):
    mock_session_local.return_value = test_db

    # Test non-existent user
    res_daily = send_daily_digest(99999)
    assert res_daily["status"] == "error"

    res_weekly = send_weekly_digest(99999)
    assert res_weekly["status"] == "error"
