"""Tests for CorporateScheduler, Redis distributed locking, and priority queues."""
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.models.base import Base
from app.models.company import Company
from app.models.source_registry import CompanySource, SourceStatus
from app.services.corporate_scheduler import CorporateScheduler


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionClass = sessionmaker(bind=engine)
    session = SessionClass()
    yield session
    session.close()


def test_scheduler_get_due_sources(db_session: Session):
    company = Company(name="TestCorp", canonical_domain="testcorp.com")
    db_session.add(company)
    db_session.flush()

    past_time = datetime.now(timezone.utc) - timedelta(minutes=5)
    future_time = datetime.now(timezone.utc) + timedelta(minutes=30)

    due_src = CompanySource(
        company_id=company.id,
        name="Due Feed",
        source_url="https://testcorp.com/feed1",
        enabled=True,
        next_check_at=past_time,
        priority="P0",
    )
    future_src = CompanySource(
        company_id=company.id,
        name="Future Feed",
        source_url="https://testcorp.com/feed2",
        enabled=True,
        next_check_at=future_time,
        priority="P2",
    )
    disabled_src = CompanySource(
        company_id=company.id,
        name="Disabled Feed",
        source_url="https://testcorp.com/feed3",
        enabled=False,
        next_check_at=past_time,
        priority="P0",
    )
    db_session.add_all([due_src, future_src, disabled_src])
    db_session.commit()

    mock_redis = MagicMock()
    scheduler = CorporateScheduler(redis_client=mock_redis)

    due = scheduler.get_due_sources(db_session)
    assert len(due) == 1
    assert due[0].name == "Due Feed"


def test_scheduler_partition_by_priority():
    mock_redis = MagicMock()
    scheduler = CorporateScheduler(redis_client=mock_redis)

    s0 = CompanySource(id=1, company_id=1, name="P0", source_url="https://a.com/0", priority="P0")
    s1 = CompanySource(id=2, company_id=1, name="P1", source_url="https://a.com/1", priority="P1")
    s2 = CompanySource(id=3, company_id=1, name="P2", source_url="https://a.com/2", priority="P2")
    s3 = CompanySource(id=4, company_id=1, name="P3", source_url="https://a.com/3", priority="P3")
    s4 = CompanySource(id=5, company_id=1, name="P4", source_url="https://a.com/4", priority="P4")

    buckets = scheduler.partition_by_priority([s0, s1, s2, s3, s4])
    assert len(buckets["p0_critical"]) == 1
    assert len(buckets["p1_official"]) == 1
    assert len(buckets["p2_standard"]) == 1
    assert len(buckets["p3_replay"]) == 1
    assert len(buckets["p4_community"]) == 1


def test_scheduler_distributed_lock():
    mock_redis = MagicMock()
    # First attempt: lock acquired
    mock_redis.set.return_value = True
    scheduler = CorporateScheduler(redis_client=mock_redis)

    acquired = scheduler.acquire_source_lock(123)
    assert acquired is True
    mock_redis.set.assert_called_with("source_lock:123", "locked", nx=True, ex=300)

    # Second attempt when held: lock returns False
    mock_redis.set.return_value = None
    acquired_again = scheduler.acquire_source_lock(123)
    assert acquired_again is False

    # Release
    scheduler.release_source_lock(123)
    mock_redis.delete.assert_called_with("source_lock:123")
