from datetime import datetime, timedelta, timezone

from app.services.verification_engine import VerificationEngine


def test_direct_observation_requires_integrity_and_entity_link():
    engine = VerificationEngine()
    now = datetime.now(timezone.utc)
    result = engine.evaluate(
        title="New authenticated API route",
        summary="Observed a new route in the production snapshot.",
        item_url="https://example.com/api/v2/users",
        source_url="https://example.com/api/v2/users",
        source_type="DIRECT_PRODUCTION_OBSERVATION",
        authority_level="DIRECT_PRODUCTION_OBSERVATION",
        source_content_hash="a" * 64,
        published_at=now,
        direct_production_observed=True,
        corroborating_source_count=1,
        entity_relationship_verified=True,
    )
    assert result.state == "CONFIRMED"
    assert result.score >= 0.9
    assert not result.blockers


def test_ai_only_claim_never_becomes_verified():
    engine = VerificationEngine()
    now = datetime.now(timezone.utc)
    result = engine.evaluate(
        title="Potential API change",
        summary="AI identified a possible new API.",
        item_url="https://example.com/api",
        source_url="https://example.com/blog",
        source_type="COMMUNITY",
        authority_level="COMMUNITY_REPORT",
        source_content_hash="b" * 64,
        published_at=now,
        ai_generated=True,
        corroborating_source_count=0,
        entity_relationship_verified=False,
    )
    assert result.state == "UNVERIFIED"
    assert "ai_only" in result.blockers
    assert "weak_source" in result.blockers


def test_future_publisher_time_is_blocked():
    engine = VerificationEngine()
    result = engine.evaluate(
        title="Release",
        summary="A specific release notice.",
        item_url="https://example.com/release",
        source_url="https://example.com/release",
        source_type="OFFICIAL_RELEASE",
        authority_level="OFFICIAL_RELEASE",
        source_content_hash="c" * 64,
        published_at=datetime.now(timezone.utc) + timedelta(days=2),
        corroborating_source_count=1,
        entity_relationship_verified=True,
    )
    assert result.state != "CONFIRMED"
    assert "publisher_time_unverified" in result.blockers
