"""Tests for the Source Registry models, status transitions, and health telemetry."""
import pytest
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.models.base import Base
from app.models.company import Company
from app.models.source_registry import (
    CompanySource,
    RawSourceSnapshot,
    SourceCollectionRun,
    NormalizedSourceDocument,
    SourceHealth,
    SourceType,
    SourceAuthorityLevel,
    SourceStatus,
    SourceHealthState,
)


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionClass = sessionmaker(bind=engine)
    session = SessionClass()
    yield session
    session.close()


def test_source_registration_and_relationship(db_session: Session):
    company = Company(name="Acme Corp", canonical_domain="acme.com")
    db_session.add(company)
    db_session.flush()

    source = CompanySource(
        company_id=company.id,
        name="Acme Changelog",
        source_url="https://acme.com/changelog.rss",
        source_type=SourceType.OFFICIAL_PRODUCT_CHANGE.value,
        authority_level=SourceAuthorityLevel.OFFICIAL_RELEASE.value,
        product_scope="Acme Cloud",
        poll_interval_seconds=600,
        priority="P1",
    )
    db_session.add(source)
    db_session.flush()

    health = SourceHealth(source_id=source.id, health_state=SourceHealthState.HEALTHY.value)
    db_session.add(health)
    db_session.commit()

    assert source.id is not None
    assert source.company.name == "Acme Corp"
    assert source.health.health_state == "HEALTHY"
    assert len(company.sources) == 1


def test_raw_source_snapshot_immutability(db_session: Session):
    company = Company(name="Beta Corp", canonical_domain="beta.com")
    db_session.add(company)
    db_session.flush()

    source = CompanySource(
        company_id=company.id,
        name="Beta Releases",
        source_url="https://beta.com/releases",
    )
    db_session.add(source)
    db_session.flush()

    snapshot = RawSourceSnapshot(
        source_id=source.id,
        company_id=company.id,
        url="https://beta.com/releases",
        http_status=200,
        etag='"abc-123"',
        content_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        body_raw="<rss><channel><title>Updates</title></channel></rss>",
        body_size=55,
        parser_version="1.0.0",
    )
    db_session.add(snapshot)
    db_session.commit()

    saved = db_session.get(RawSourceSnapshot, snapshot.id)
    assert saved is not None
    assert saved.content_hash == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    assert len(saved.source.snapshots) == 1


def test_source_collection_run_metrics(db_session: Session):
    company = Company(name="Gamma", canonical_domain="gamma.com")
    db_session.add(company)
    db_session.flush()

    source = CompanySource(company_id=company.id, name="Gamma Feed", source_url="https://gamma.com/feed")
    db_session.add(source)
    db_session.flush()

    run = SourceCollectionRun(
        source_id=source.id,
        status="SUCCESS_CHANGED",
        http_status=200,
        items_found=5,
        items_changed=5,
        duration_ms=250,
        credits_used=1.0,
        response_bytes=4096,
        estimated_cost=0.002,
    )
    db_session.add(run)
    db_session.commit()

    assert run.id is not None
    assert run.items_found == 5
    assert run.duration_ms == 250
