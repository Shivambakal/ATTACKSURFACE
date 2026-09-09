"""Tests for AI-Powered Security Intelligence Collector and API endpoints."""
import json
from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.db import Base, get_db
from app.models import Company, Product, SecurityAdvisory, SecurityIntelligenceEvent, Technology
from app.services.security_intelligence_collector import (
    RawIntelligenceBatch,
    RawIntelligenceItem,
    SecurityIntelligenceCollector,
    compute_fingerprint,
    compute_priority_scores,
    parse_iso_datetime,
)


@pytest.fixture
def in_memory_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(in_memory_db):
    def override_get_db():
        try:
            yield in_memory_db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


class TestSecurityIntelligenceScoringAndDedup:
    def test_compute_fingerprint_deterministic_and_normalized(self):
        fp1 = compute_fingerprint("CISA", "https://cisa.gov/news/1", ["CVE-2026-1111"], "Critical Vulnerability")
        fp2 = compute_fingerprint(" cisa ", "HTTPS://CISA.GOV/NEWS/1 ", ["cve-2026-1111"], " critical vulnerability ")
        assert fp1 == fp2
        assert len(fp1) == 64

    def test_compute_priority_scores_critical_active_exploit(self):
        now = datetime.now(timezone.utc)
        scores = compute_priority_scores(
            severity="CRITICAL",
            actively_exploited=True,
            has_exploitation_evidence=True,
            published_at=now,
            has_cves=True,
            has_entities=True,
            confidence=0.95,
        )
        assert scores["priority"] == "CRITICAL"
        assert scores["priority_score"] >= 85
        assert scores["exploitation_score"] == 100
        assert scores["severity_score"] == 95

    def test_compute_priority_scores_low_severity(self):
        now = datetime.now(timezone.utc)
        scores = compute_priority_scores(
            severity="LOW",
            actively_exploited=False,
            has_exploitation_evidence=False,
            published_at=now,
            has_cves=False,
            has_entities=False,
            confidence=0.5,
        )
        assert scores["priority"] == "LOW"
        assert scores["priority_score"] < 45
        assert scores["exploitation_score"] == 0

    def test_parse_iso_datetime_robustness(self):
        dt1 = parse_iso_datetime("2026-09-04T12:00:00Z")
        assert dt1.tzinfo is not None
        assert dt1.year == 2026

        dt_fallback = parse_iso_datetime("invalid-date-string")
        assert dt_fallback.tzinfo is not None


class TestSecurityIntelligenceExtraction:
    def test_raw_intelligence_batch_validation(self):
        data = {
            "items": [
                {
                    "title": "Zero-Day in Enterprise Gateway",
                    "summary": "Actively exploited remote code execution flaw discovered in web gateway.",
                    "event_type": "EXPLOIT",
                    "published_at": "2026-09-04T10:00:00Z",
                    "source_url": "https://example.com/advisory",
                    "source_name": "ExampleSec",
                    "cve_ids": ["CVE-2026-99999"],
                    "severity": "CRITICAL",
                    "actively_exploited": True,
                    "known_exploitation_evidence": "Observed in targeted campaigns",
                    "confidence": 0.9,
                }
            ]
        }
        batch = RawIntelligenceBatch.model_validate(data)
        assert len(batch.items) == 1
        assert batch.items[0].cve_ids == ["CVE-2026-99999"]
        assert batch.items[0].actively_exploited is True

    def test_extract_json_batch_with_fences(self):
        collector = SecurityIntelligenceCollector()
        fenced_text = '''```json
        {
            "items": [
                {
                    "title": "Patch Released for Ivanti Connect Secure",
                    "summary": "Vendor releases out-of-band security patch addressing critical flaw.",
                    "event_type": "PATCH",
                    "published_at": "2026-09-04T08:00:00Z",
                    "source_url": "https://vendor.example/patch",
                    "source_name": "Vendor Bulletin",
                    "cve_ids": ["CVE-2026-8888"],
                    "severity": "HIGH",
                    "actively_exploited": false,
                    "confidence": 0.85
                }
            ]
        }
        ```'''
        batch = collector._extract_json_batch(fenced_text)
        assert batch is not None
        assert len(batch.items) == 1
        assert batch.items[0].title == "Patch Released for Ivanti Connect Secure"

    def test_extract_json_batch_with_preamble(self):
        collector = SecurityIntelligenceCollector()
        text_with_preamble = '''Here are the latest security findings discovered via Google Search:
        {
            "items": [
                {
                    "title": "CISA Adds Cisco Flaw to KEV",
                    "summary": "CISA has added a remote command execution flaw in Cisco ASA to KEV catalog.",
                    "event_type": "CVE",
                    "published_at": "2026-09-04T09:30:00Z",
                    "source_url": "https://cisa.gov/kev/1",
                    "source_name": "CISA",
                    "cve_ids": ["CVE-2026-7777"],
                    "severity": "CRITICAL",
                    "actively_exploited": true,
                    "confidence": 0.99
                }
            ]
        }
        I hope this analysis assists your threat monitoring.'''
        batch = collector._extract_json_batch(text_with_preamble)
        assert batch is not None
        assert len(batch.items) == 1
        assert batch.items[0].cve_ids == ["CVE-2026-7777"]


class TestCollectorPersistenceAndCorrelation:
    def test_persist_single_item_and_deduplicate(self, in_memory_db):
        collector = SecurityIntelligenceCollector()
        item = RawIntelligenceItem(
            title="Fortinet Authentication Bypass",
            summary="Critical vulnerability allowing unauthenticated admin access.",
            event_type="CVE",
            published_at="2026-09-04T07:00:00Z",
            source_url="https://fortinet.example/advisory",
            source_name="Fortinet",
            cve_ids=["CVE-2026-5555"],
            affected_products=["FortiOS"],
            affected_companies=["Fortinet"],
            severity="CRITICAL",
            actively_exploited=True,
            confidence=0.92,
        )

        event1 = collector._persist_single_item(item, {}, "raw", in_memory_db)
        in_memory_db.commit()
        assert event1 is not None
        assert event1.id is not None
        assert event1.priority == "CRITICAL"

        # Persist identical item again (should update existing rather than duplicate)
        item_updated = RawIntelligenceItem(
            title="Fortinet Authentication Bypass",
            summary="Updated summary with confirmed exploitation in the wild.",
            event_type="CVE",
            published_at="2026-09-04T07:00:00Z",
            source_url="https://fortinet.example/advisory",
            source_name="Fortinet",
            cve_ids=["CVE-2026-5555"],
            affected_products=["FortiOS"],
            affected_companies=["Fortinet"],
            severity="CRITICAL",
            actively_exploited=True,
            confidence=0.95,
        )
        event2 = collector._persist_single_item(item_updated, {}, "raw2", in_memory_db)
        in_memory_db.commit()

        assert event2.id == event1.id
        assert event2.summary == "Updated summary with confirmed exploitation in the wild."

    def test_entity_correlation_graph(self, in_memory_db):
        collector = SecurityIntelligenceCollector()

        # Seed company and product
        company = Company(name="Acme Corp", canonical_domain="acme.com")
        in_memory_db.add(company)
        in_memory_db.commit()

        product = Product(company_id=company.id, name="Acme Cloud Gateway")
        technology = Technology(name="AcmeOS")
        advisory = SecurityAdvisory(
            canonical_id="CISA_KEV:CVE-2026-1234",
            provider="cisa_kev",
            provider_record_id="CVE-2026-1234",
            cve_id="CVE-2026-1234",
            title="Acme Flaw",
            summary="Test",
        )
        in_memory_db.add_all([product, technology, advisory])
        in_memory_db.commit()

        # Correlate
        matched_companies = collector._correlate_companies(["Acme Corp"], in_memory_db)
        matched_products = collector._correlate_products(["Acme Cloud Gateway"], in_memory_db)
        matched_techs = collector._correlate_technologies(["AcmeOS"], in_memory_db)
        matched_advisories = collector._correlate_advisories(["CVE-2026-1234"], in_memory_db)

        assert company.id in matched_companies
        assert product.id in matched_products
        assert technology.id in matched_techs
        assert advisory.id in matched_advisories


class TestSecurityIntelligenceRouter:
    def test_endpoints_crud_and_stats(self, client, in_memory_db):
        # Insert test event
        event = SecurityIntelligenceEvent(
            title="Major OpenSSL RCE Disclosed",
            summary="Remote code execution vulnerability in OpenSSL versions prior to 3.2.1.",
            event_type="CVE",
            published_at=datetime.now(timezone.utc),
            source_url="https://openssl.org/advisory",
            source_name="OpenSSL Foundation",
            cve_ids=["CVE-2026-0001"],
            severity="CRITICAL",
            actively_exploited=True,
            confidence=0.95,
            fingerprint="test_fp_openssl_0001",
            priority="CRITICAL",
            priority_score=92,
            severity_score=95,
            freshness_score=100,
            exploitation_score=100,
            relevance_score=85,
        )
        in_memory_db.add(event)
        in_memory_db.commit()

        # 1. GET /stats
        res_stats = client.get("/api/v1/security-intelligence/stats")
        assert res_stats.status_code == 200
        data_stats = res_stats.json()
        assert data_stats["total_events"] == 1
        assert data_stats["actively_exploited_count"] == 1
        assert data_stats["by_severity"]["CRITICAL"] == 1

        # 2. GET /latest
        res_latest = client.get("/api/v1/security-intelligence/latest")
        assert res_latest.status_code == 200
        latest_items = res_latest.json()
        assert len(latest_items) == 1
        assert latest_items[0]["cve_ids"] == ["CVE-2026-0001"]

        # 3. GET /high-priority
        res_high = client.get("/api/v1/security-intelligence/high-priority")
        assert res_high.status_code == 200
        assert len(res_high.json()) == 1

        # 4. GET / with filter
        res_filter = client.get("/api/v1/security-intelligence/?severity=CRITICAL&actively_exploited=true")
        assert res_filter.status_code == 200
        assert res_filter.json()["total"] == 1

        # 5. GET /{id}
        res_single = client.get(f"/api/v1/security-intelligence/{event.id}")
        assert res_single.status_code == 200
        assert res_single.json()["title"] == "Major OpenSSL RCE Disclosed"
