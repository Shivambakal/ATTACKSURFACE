"""Unit and regression tests for Change Quality Gate.

Verifies:
1. Zero "Untitled Update" or generic placeholder records.
2. Zero manufactured "UNKNOWN" endpoints or methods.
3. Zero fake current timestamps for historical records.
4. Rejection of generic homepage fallback URLs.
5. URL canonicalization (stripping tracking parameters).
6. HTML cleanup with entity decoding.
7. Freshness classification (NEW, RECENT, HISTORICAL, STALE, UNKNOWN_DATE).
8. Security relevance scoring (ACTIONABLE, CONTEXT, NOISE).
9. Strict signal gating: only ACCEPTED + ACTIONABLE + NEW/RECENT + score >= 70 generates ResearchSignal.
10. GoogleCloudReleaseNotesConnector unpacks subsections into real product headlines.
11. Idempotency across successive collection runs.
"""
from __future__ import annotations

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock
import httpx
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.models.base import Base
from app.models.company import Company
from app.models.cluster import ChangeCluster
from app.models.signal import ResearchSignal
from app.models.timeline import TimelineEvent
from app.models.source_registry import (
    CompanySource,
    RawSourceSnapshot,
    NormalizedSourceDocument,
    SourceStatus,
)
from app.services.change_quality_gate import (
    ChangeQualityGate,
    QualityDecision,
    RejectionReason,
    FreshnessCategory,
    RelevanceCategory,
    clean_text_content,
    canonicalize_url,
    classify_freshness,
    classify_security_relevance,
)
from app.services.connector_engine import (
    ConnectorEngine,
    GenericFeedConnector,
    GoogleCloudReleaseNotesConnector,
    parse_feed_datetime,
    ParsedItem,
)
from app.services.corporate_clustering import CorporateClusteringService


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionClass = sessionmaker(bind=engine)
    session = SessionClass()
    yield session
    session.close()


@pytest.fixture(autouse=True)
def mock_target_safety(monkeypatch):
    from app.services.target_safety import ValidationResult
    monkeypatch.setattr(
        "app.services.connector_engine.validate_url_for_collection",
        lambda url: ValidationResult(True, "Safe"),
    )


# 1. Rejection of Generic and Blank Titles
def test_reject_blank_or_generic_titles():
    gate = ChangeQualityGate()
    now = datetime.now(timezone.utc)

    # Blank title
    res = gate.evaluate(
        title="",
        summary="Some valid summary for the release",
        url="https://cloud.google.com/release-notes/item-1",
        source_name="Feed",
        published_at=now,
    )
    assert res.decision == QualityDecision.REJECTED
    assert res.rejection_reason == RejectionReason.REJECT_MISSING_TITLE.value

    # "Untitled Update"
    res = gate.evaluate(
        title="Untitled Update",
        summary="Some valid summary for the release",
        url="https://cloud.google.com/release-notes/item-2",
        source_name="Feed",
        published_at=now,
    )
    assert res.decision == QualityDecision.REJECTED
    assert res.rejection_reason == RejectionReason.REJECT_GENERIC_TITLE.value

    # Date-only title
    res = gate.evaluate(
        title="September 03, 2026",
        summary="A list of product changes",
        url="https://cloud.google.com/release-notes/item-3",
        source_name="Feed",
        published_at=now,
    )
    assert res.decision == QualityDecision.REJECTED
    assert res.rejection_reason == RejectionReason.REJECT_GENERIC_TITLE.value


# 2. Rejection of Generic Homepage URLs
def test_reject_generic_homepage_urls():
    gate = ChangeQualityGate()
    now = datetime.now(timezone.utc)

    for bad_url in [
        "https://cloud.google.com",
        "https://cloud.google.com/",
        "https://www.cisa.gov",
        "https://google.com/",
        "",
        "not-a-valid-url",
    ]:
        res = gate.evaluate(
            title="Google Cloud Spanner: New Mutex API",
            summary="Introduces mutual exclusion locking API for distributed workloads.",
            url=bad_url,
            source_name="Feed",
            published_at=now,
        )
        assert res.decision == QualityDecision.REJECTED
        assert res.rejection_reason in (
            RejectionReason.REJECT_FALLBACK_URL.value,
            RejectionReason.REJECT_INVALID_URL.value,
        )


# 3. URL Canonicalization & Tracking Parameter Stripping
def test_canonicalize_url_strips_tracking():
    url_with_tracking = "https://cloud.google.com/release-notes?utm_source=rss&utm_medium=feed&real_id=9942&ref=newsletter"
    canonical = canonicalize_url(url_with_tracking)
    assert canonical == "https://cloud.google.com/release-notes?real_id=9942"
    assert "utm_source" not in canonical
    assert "ref" not in canonical


# 4. HTML Cleanup and Entity Decoding
def test_clean_text_content():
    raw_html = """
    <p>Google Cloud <strong>IAM</strong> announces &quot;Privilege Boundaries&quot; &amp; fine-grained access.</p>
    <div><a href="https://example.com">Learn more</a></div>
    """
    clean = clean_text_content(raw_html)
    assert clean == 'Google Cloud IAM announces "Privilege Boundaries" & fine-grained access. Learn more'
    assert "<p>" not in clean
    assert "&quot;" not in clean


# 5. Freshness Classification & No Fake Timestamps
def test_freshness_classification_and_real_dates():
    now = datetime.now(timezone.utc)

    # New: 2 days old
    f_new = classify_freshness(now - timedelta(days=2))
    assert f_new == FreshnessCategory.NEW

    # Recent: 15 days old
    f_rec = classify_freshness(now - timedelta(days=15))
    assert f_rec == FreshnessCategory.RECENT

    # Historical: 45 days old (> 30 days)
    f_hist = classify_freshness(now - timedelta(days=45))
    assert f_hist == FreshnessCategory.HISTORICAL

    # Stale: 200 days old (> 180 days)
    f_stale = classify_freshness(now - timedelta(days=200))
    assert f_stale == FreshnessCategory.STALE

    # Unknown date
    f_unk = classify_freshness(None)
    assert f_unk == FreshnessCategory.UNKNOWN_DATE


# 6. Quality Gate: Historical Items are Kept as Context Only
def test_historical_items_context_only():
    gate = ChangeQualityGate()
    hist_date = datetime.now(timezone.utc) - timedelta(days=50)

    res = gate.evaluate(
        title="Google Cloud KMS: Added Post-Quantum Cryptography Algorithms",
        summary="Added ML-KEM and Dilithium algorithms to Cloud Key Management Service endpoints.",
        url="https://cloud.google.com/kms/docs/release-notes#pqc",
        source_name="Google Cloud Release Notes",
        published_at=hist_date,
        change_type="SECURITY_UPDATE",
    )
    # Must be CONTEXT_ONLY (never REJECTED, but never primary ACTIONABLE signal)
    assert res.decision == QualityDecision.CONTEXT_ONLY
    assert res.freshness == FreshnessCategory.HISTORICAL
    assert res.is_actionable is False


# 7. Security Relevance: Noise vs Context vs Actionable
def test_security_relevance_classification():
    # Actionable: Security / Auth / API
    cat_sec, score_sec = classify_security_relevance(
        "OpenID Connect Workload Identity Federation update",
        "Enforces strict audience validation on token exchange endpoints.",
        "SECURITY_UPDATE",
    )
    assert cat_sec == RelevanceCategory.ACTIONABLE
    assert score_sec >= 80

    # Context: Routine product capability
    cat_ctx, score_ctx = classify_security_relevance(
        "Cloud Storage: Added support for 50TB objects in regional buckets",
        "Customers can now store larger objects in single PUT operations.",
        "PRODUCT_UPDATE",
    )
    assert cat_ctx == RelevanceCategory.CONTEXT
    assert score_ctx < 70

    # Noise: Marketing / webinar / pricing
    cat_noise, score_noise = classify_security_relevance(
        "Join our Webinar: Enterprise Architecture Best Practices",
        "Sign up for our marketing seminar and live Q&A session.",
        "PRODUCT_UPDATE",
    )
    assert cat_noise == RelevanceCategory.NOISE


# 8. Feed DateTime Parsing (RSS & Atom)
def test_parse_feed_datetime():
    # Atom ISO-8601
    atom_dt = parse_feed_datetime("2026-09-02T14:30:00Z")
    assert atom_dt is not None
    assert atom_dt.year == 2026
    assert atom_dt.month == 9
    assert atom_dt.day == 2

    # RSS RFC-2822
    rss_dt = parse_feed_datetime("Wed, 02 Sep 2026 14:30:00 GMT")
    assert rss_dt is not None
    assert rss_dt.year == 2026
    assert rss_dt.month == 9
    assert rss_dt.day == 2


# 9. GoogleCloudReleaseNotesConnector unpacks product subsections
def test_google_cloud_release_notes_unpacks_product_subsections():
    connector = GoogleCloudReleaseNotesConnector()
    atom_xml = """<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Google Cloud Release Notes</title>
  <entry>
    <id>tag:google.com,2026:gcp-rn-2026-09-03</id>
    <title>September 03, 2026</title>
    <updated>2026-09-03T10:00:00Z</updated>
    <link href="https://cloud.google.com/release-notes#september-03-2026" />
    <content type="html"><![CDATA[
      <h2 class="release-note-product-title">API Gateway</h2>
      <div class="release-note-section">
        <h3>Feature</h3>
        <p><strong>Mutual TLS (mTLS) Support</strong> is now Generally Available on API Gateway endpoints.</p>
      </div>
      <h2 class="release-note-product-title">Cloud Key Management Service</h2>
      <div class="release-note-section">
        <h3>Security</h3>
        <p><strong>Post-quantum ML-DSA signing keys</strong> are now supported in KMS v1 API.</p>
      </div>
    ]]></content>
  </entry>
</feed>"""

    source = CompanySource(
        id=1,
        company_id=1,
        name="Google Cloud Release Notes",
        feed_url="https://cloud.google.com/feeds/gcp-release-notes.xml",
        source_url="https://cloud.google.com/release-notes",
    )
    items = connector._unpack_google_cloud_items(atom_xml, source)

    assert len(items) == 2

    # First item: API Gateway
    assert items[0].product == "API Gateway"
    assert "Mutual TLS" in items[0].title
    assert "Generally Available" in items[0].summary
    assert items[0].change_type == "FEATURE_ADDED"
    assert items[0].api_method is None  # Zero manufactured "UNKNOWN"
    assert items[0].api_endpoint is None

    # Second item: Cloud KMS
    assert items[1].product == "Cloud Key Management Service"
    assert "Post-quantum" in items[1].title
    assert items[1].change_type == "SECURITY_UPDATE"


# 10. Strict ResearchSignal Gating & Deduplication
def test_strict_signal_gating_and_deduplication(db_session: Session):
    company = Company(name="Google", canonical_domain="google.com")
    db_session.add(company)
    db_session.flush()

    service = CorporateClusteringService(db_session)
    now = datetime.now(timezone.utc)

    # Item 1: High quality actionable security change
    actionable_item = {
        "title": "Google Cloud API Gateway: mTLS Gateway Endpoint Security",
        "product": "API Gateway",
        "change_type": "SECURITY_UPDATE",
        "summary": "Enforces strict certificate validation on API Gateway routes.",
        "url": "https://cloud.google.com/api-gateway/docs/security-mtls",
        "published_at": now.isoformat(),
        "quality_decision": "ACCEPTED",
        "security_relevance": "ACTIONABLE",
        "freshness_category": "NEW",
        "relevance_score": 85,
    }

    # Item 2: Routine product update (CONTEXT_ONLY)
    context_item = {
        "title": "Google Cloud Storage: Minor console UI color update",
        "product": "Cloud Storage",
        "change_type": "PRODUCT_UPDATE",
        "summary": "Adjusted primary action button color in web console.",
        "url": "https://cloud.google.com/storage/docs/release-notes#ui",
        "published_at": now.isoformat(),
        "quality_decision": "CONTEXT_ONLY",
        "security_relevance": "CONTEXT",
        "freshness_category": "NEW",
        "relevance_score": 45,
    }

    # Item 3: Stale historical item (CONTEXT_ONLY)
    stale_item = {
        "title": "Google Cloud BigQuery: SQL v1 deprecation announcement",
        "product": "BigQuery",
        "change_type": "DEPRECATION",
        "summary": "Historical deprecation notice published a year ago.",
        "url": "https://cloud.google.com/bigquery/docs/legacy-sql",
        "published_at": (now - timedelta(days=365)).isoformat(),
        "quality_decision": "CONTEXT_ONLY",
        "security_relevance": "CONTEXT",
        "freshness_category": "STALE",
        "relevance_score": 30,
    }

    # RUN #1: Ingest batch
    clusters = service.cluster_extracted_items(
        company_id=company.id,
        source_id=1,
        items=[actionable_item, context_item, stale_item],
    )
    assert len(clusters) == 3

    # All 3 have TimelineEvents
    timeline_events = db_session.query(TimelineEvent).all()
    assert len(timeline_events) == 3

    # Check quality badge and temporal category
    event_by_title = {e.title: e for e in timeline_events}
    act_te = event_by_title[f"{company.name}: {actionable_item['title']}"]
    assert act_te.temporal_category == "NEW"
    assert act_te.quality_badge == "ACCEPTED"

    stale_te = event_by_title[f"{company.name}: {stale_item['title']}"]
    assert stale_te.temporal_category == "STALE"
    assert stale_te.quality_badge == "CONTEXT_ONLY"

    # CRITICAL: Exactly 1 ResearchSignal created (ONLY for the actionable item!)
    signals = db_session.query(ResearchSignal).all()
    assert len(signals) == 1
    assert "mTLS Gateway" in signals[0].title
    assert signals[0].relevance_score == 85

    # RUN #2: Re-ingest the exact same items (Idempotency test)
    clusters_run2 = service.cluster_extracted_items(
        company_id=company.id,
        source_id=1,
        items=[actionable_item, context_item, stale_item],
    )
    assert len(clusters_run2) == 3

    # Clusters count must remain exactly 3 (no duplicates)
    assert db_session.query(ChangeCluster).count() == 3

    # TimelineEvents count must remain exactly 3 (no duplicate timeline events)
    assert db_session.query(TimelineEvent).count() == 3

    # Signals count must remain exactly 1 (zero duplicate signals)
    assert db_session.query(ResearchSignal).count() == 1
