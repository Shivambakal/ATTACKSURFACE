"""Comprehensive Test Suite for Scaled Public Security Program Registry.

Covers:
- Domain extraction and canonicalization (multi-part TLDs, platform rejections, IP filtering)
- Company name cleaning and legal suffix stripping
- Platform parsers (HackerOne, Bugcrowd, Intigriti, YesWeHack, Federacy, ProjectDiscovery)
- Entity resolution and multi-platform company merging
- Data preservation for existing companies and authorized targets
- Zero fabrication verification
- Snapshot hashing and scope diff events (PROGRAM_SCOPE_ADDED, PROGRAM_SCOPE_REMOVED)
- API endpoints (/api/v1/companies/stats, /api/v1/programs, /api/v1/programs/stats, /api/v1/programs/{id})
"""
from __future__ import annotations

import json
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import get_db
from app.main import create_app
from app.models.base import Base
from app.models.company import Company
from app.models.security_program import (
    SecurityProgram,
    ProgramScopeRule,
    ProgramSnapshot,
    ProgramChangeEvent,
)
from app.models.target import Target
from app.models.asset import Asset
from app.models.signal import ResearchSignal
from app.services.program_entity_resolution import (
    extract_root_domain,
    clean_company_name,
    normalize_name_for_matching,
    compute_scope_hash,
    ProgramEntityResolutionService,
)
from app.services.program_ingestion import (
    parse_projectdiscovery_programs,
    parse_hackerone_programs,
    parse_bugcrowd_programs,
    parse_intigriti_programs,
    parse_yeswehack_programs,
    parse_federacy_programs,
)


@pytest.fixture
def test_db():
    """In-memory SQLite database for isolated test execution."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def client(test_db):
    """FastAPI TestClient with overridden DB dependency."""
    app = create_app()

    def override_get_db():
        try:
            yield test_db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


# ==============================================================================
# 1. DOMAIN EXTRACTION & VALIDATION TESTS
# ==============================================================================

def test_extract_root_domain_standard():
    assert extract_root_domain("https://api.openai.com/v1") == "openai.com"
    assert extract_root_domain("http://staging.shop.stripe.com:8080/cart") == "stripe.com"
    assert extract_root_domain("*.subdomain.example.org") == "example.org"
    assert extract_root_domain("example.com") == "example.com"
    assert extract_root_domain("www.coindesk.com") == "coindesk.com"


def test_extract_root_domain_multipart_tlds():
    assert extract_root_domain("https://portal.bank.co.uk/login") == "bank.co.uk"
    assert extract_root_domain("payments.auspost.com.au") == "auspost.com.au"
    assert extract_root_domain("api.tokyo.co.jp") == "tokyo.co.jp"
    assert extract_root_domain("service.startup.co.in") == "startup.co.in"


def test_extract_root_domain_rejections():
    # Bug bounty platforms must not be treated as target company domains
    assert extract_root_domain("https://hackerone.com/shopify") is None
    assert extract_root_domain("https://bugcrowd.com/tesla") is None
    assert extract_root_domain("https://intigriti.com/programs/test") is None
    assert extract_root_domain("https://yeswehack.com/programs/slug") is None

    # Third-party host and cloud platforms
    assert extract_root_domain("https://docs.google.com/document/d/123") is None
    assert extract_root_domain("https://play.google.com/store/apps/details?id=com.app") is None
    assert extract_root_domain("https://apps.apple.com/us/app/id123") is None
    assert extract_root_domain("https://t.me/channel") is None

    # IP addresses
    assert extract_root_domain("192.168.1.1") is None
    assert extract_root_domain("10.0.0.1:8080") is None
    assert extract_root_domain("1.1.1.1") is None

    # Android package IDs / non-domains
    assert extract_root_domain("com.example.mobileapp") is None
    assert extract_root_domain("smart contract") is None
    assert extract_root_domain("") is None
    assert extract_root_domain(None) is None


# ==============================================================================
# 2. COMPANY NAME CLEANING TESTS
# ==============================================================================

def test_clean_company_name():
    assert clean_company_name("Acme Corp, Inc.") == "Acme"
    assert clean_company_name("Shopify (Bug Bounty Program)") == "Shopify"
    assert clean_company_name("GitLab - Bug Bounty") == "GitLab"
    assert clean_company_name("Uber Technologies, LLC") == "Uber"
    assert clean_company_name("BlaBlaCar [VDP]") == "BlaBlaCar"
    assert clean_company_name("", fallback_domain="datadog.com") == "Datadog"


def test_normalize_name_for_matching():
    token1 = normalize_name_for_matching("Shopify, Inc.")
    token2 = normalize_name_for_matching("Shopify")
    assert token1 == token2 == "shopify"

    token3 = normalize_name_for_matching("CoinDesk - Bug Bounty Program")
    token4 = normalize_name_for_matching("CoinDesk LLC")
    assert token3 == token4 == "coindesk"


# ==============================================================================
# 3. PUBLIC ECOSYSTEM PARSER TESTS
# ==============================================================================

def test_parse_projectdiscovery_programs():
    raw = {
        "programs": [
            {
                "name": "1inch",
                "url": "https://hackenproof.com/1inch/1inch-smart-contract",
                "bounty": True,
                "domains": ["1inch.io", "app.1inch.io"],
            }
        ]
    }
    parsed = parse_projectdiscovery_programs(raw)
    assert len(parsed) == 1
    p = parsed[0]
    assert p["platform"] == "ProjectDiscovery"
    assert p["program_name"] == "1inch"
    assert p["offers_bounties"] is True
    assert len(p["in_scope"]) == 2
    assert p["in_scope"][0]["target"] == "1inch.io"


def test_parse_hackerone_programs():
    raw = [
        {
            "name": "Shopify",
            "handle": "shopify",
            "url": "https://hackerone.com/shopify",
            "website": "https://www.shopify.com",
            "offers_bounties": True,
            "submission_state": "open",
            "targets": {
                "in_scope": [
                    {"asset_identifier": "shopify.com", "asset_type": "URL", "eligible_for_bounty": True}
                ],
                "out_of_scope": [
                    {"asset_identifier": "help.shopify.com", "asset_type": "URL"}
                ],
            },
        }
    ]
    parsed = parse_hackerone_programs(raw)
    assert len(parsed) == 1
    p = parsed[0]
    assert p["platform"] == "HackerOne"
    assert p["program_handle"] == "shopify"
    assert p["offers_bounties"] is True
    assert len(p["in_scope"]) == 1
    assert len(p["out_of_scope"]) == 1


def test_parse_bugcrowd_programs():
    raw = [
        {
            "name": "CoinDesk",
            "url": "https://bugcrowd.com/coindesk",
            "max_payout": 2500,
            "targets": {
                "in_scope": [
                    {"target": "https://www.coindesk.com", "type": "website"}
                ]
            }
        }
    ]
    parsed = parse_bugcrowd_programs(raw)
    assert len(parsed) == 1
    p = parsed[0]
    assert p["platform"] == "Bugcrowd"
    assert p["max_bounty"] == 2500.0
    assert p["offers_bounties"] is True


def test_parse_intigriti_programs():
    raw = [
        {
            "name": "Red Bull",
            "handle": "redbull",
            "url": "https://app.intigriti.com/programs/redbull/redbull",
            "status": "Open",
            "confidentiality_level": "Public",
            "min_bounty": 100,
            "max_bounty": 5000,
            "targets": {
                "in_scope": [{"endpoint": "redbull.com", "type": "url"}]
            }
        }
    ]
    parsed = parse_intigriti_programs(raw)
    assert len(parsed) == 1
    p = parsed[0]
    assert p["platform"] == "Intigriti"
    assert p["min_bounty"] == 100.0
    assert p["max_bounty"] == 5000.0
    assert p["currency"] == "EUR"


def test_parse_yeswehack_programs():
    raw = [
        {
            "name": "Dailymotion",
            "slug": "dailymotion",
            "public": True,
            "min_bounty": 250,
            "max_bounty": 3000,
            "targets": {
                "in_scope": [{"target": "dailymotion.com", "scope_type": "web-application"}]
            }
        }
    ]
    parsed = parse_yeswehack_programs(raw)
    assert len(parsed) == 1
    p = parsed[0]
    assert p["platform"] == "YesWeHack"
    assert p["is_public"] is True


def test_parse_federacy_programs():
    raw = [
        {
            "name": "SimpleLogin",
            "url": "https://www.federacy.com/simplelogin",
            "offers_awards": True,
            "targets": {
                "in_scope": [{"target": "simplelogin.io", "target_type": "website"}]
            }
        }
    ]
    parsed = parse_federacy_programs(raw)
    assert len(parsed) == 1
    p = parsed[0]
    assert p["platform"] == "Federacy"
    assert p["offers_bounties"] is True


# ==============================================================================
# 4. ENTITY RESOLUTION & PRESERVATION TESTS
# ==============================================================================

def test_entity_resolution_preserves_existing_companies(test_db):
    # Seed an existing company and an authorized target
    existing_comp = Company(
        name="Existing Corp",
        canonical_domain="existing.com",
        industry="Technology",
        tracking_status="ACTIVE",
    )
    test_db.add(existing_comp)
    test_db.flush()

    target = Target(
        domain="existing.com",
        company_id=existing_comp.id,
        monitoring_status="MONITORED",
        authorization_confirmed=True,
    )
    test_db.add(target)
    test_db.commit()

    initial_comp_id = existing_comp.id
    initial_target_count = test_db.query(Target).count()
    assert initial_target_count == 1

    # Ingest a program that belongs to existing.com
    resolver = ProgramEntityResolutionService(test_db)
    prog_data = {
        "platform": "HackerOne",
        "program_name": "Existing Corp Bug Bounty",
        "handle": "existing",
        "url": "https://hackerone.com/existing",
        "website": "https://existing.com",
        "is_public": True,
        "offers_bounties": True,
        "in_scope": [{"target": "existing.com", "type": "URL"}],
        "out_of_scope": [],
    }

    sp, comp_created, prog_created = resolver.ingest_program_record(prog_data)
    test_db.commit()

    # Verify company was matched and NOT re-created
    assert comp_created is False
    assert prog_created is True
    assert sp.company_id == initial_comp_id
    assert test_db.query(Target).count() == 1  # Authorized target preserved!


def test_entity_resolution_merges_multi_platform_programs(test_db):
    resolver = ProgramEntityResolutionService(test_db)

    # Ingest HackerOne program for Acme
    h1_prog = {
        "platform": "HackerOne",
        "program_name": "Acme Corporation",
        "handle": "acme",
        "url": "https://hackerone.com/acme",
        "website": "https://acme.org",
        "is_public": True,
        "offers_bounties": True,
        "in_scope": [{"target": "acme.org", "type": "URL"}],
    }
    sp1, comp_created1, prog_created1 = resolver.ingest_program_record(h1_prog)
    test_db.commit()

    assert comp_created1 is True
    assert prog_created1 is True
    acme_company_id = sp1.company_id

    # Ingest Bugcrowd program for the same company (acme.org)
    bc_prog = {
        "platform": "Bugcrowd",
        "program_name": "Acme Bug Bounty",
        "handle": "acme-corp",
        "url": "https://bugcrowd.com/acme",
        "website": "https://acme.org",
        "is_public": True,
        "offers_bounties": True,
        "max_bounty": 10000.0,
        "in_scope": [{"target": "acme.org", "type": "website"}],
    }
    sp2, comp_created2, prog_created2 = resolver.ingest_program_record(bc_prog)
    test_db.commit()

    # Second ingestion should MATCH existing company, not create duplicate
    assert comp_created2 is False
    assert prog_created2 is True
    assert sp2.company_id == acme_company_id

    # Verify both programs belong to the same company
    programs = test_db.query(SecurityProgram).filter(SecurityProgram.company_id == acme_company_id).all()
    assert len(programs) == 2
    platforms = {p.platform for p in programs}
    assert platforms == {"HackerOne", "Bugcrowd"}


def test_zero_fabrication_skips_domainless_programs(test_db):
    resolver = ProgramEntityResolutionService(test_db)

    # Program with no valid root domain and no website
    invalid_prog = {
        "platform": "HackerOne",
        "program_name": "Phantom Mobile App",
        "handle": "phantom-app",
        "url": "https://hackerone.com/phantom-app",
        "website": None,
        "is_public": True,
        "offers_bounties": False,
        "in_scope": [{"target": "com.phantom.android", "type": "Android"}],
    }
    sp, comp_created, prog_created = resolver.ingest_program_record(invalid_prog)

    # Must NOT create a synthetic company like "phantomapp.com"
    assert sp is None
    assert comp_created is False
    assert test_db.query(Company).filter(Company.name == "Phantom Mobile App").first() is None


# ==============================================================================
# 5. SNAPSHOT HASHING & SCOPE DIFF DETECTION TESTS
# ==============================================================================

def test_scope_diff_and_snapshot_events(test_db):
    resolver = ProgramEntityResolutionService(test_db)

    # Initial scope with 1 target
    initial_prog = {
        "platform": "HackerOne",
        "program_name": "Diff Corp",
        "handle": "diffcorp",
        "url": "https://hackerone.com/diffcorp",
        "website": "https://diffcorp.io",
        "is_public": True,
        "offers_bounties": True,
        "in_scope": [{"target": "diffcorp.io", "type": "URL"}],
        "out_of_scope": [],
    }
    sp1, _, _ = resolver.ingest_program_record(initial_prog)
    test_db.commit()

    # Should have 1 snapshot and 0 change events initially
    snapshots = test_db.query(ProgramSnapshot).filter(ProgramSnapshot.security_program_id == sp1.id).all()
    assert len(snapshots) == 1
    assert snapshots[0].scope_count == 1
    assert test_db.query(ProgramChangeEvent).count() == 0

    # Expand scope with 2 additional targets
    expanded_prog = {
        "platform": "HackerOne",
        "program_name": "Diff Corp",
        "handle": "diffcorp",
        "url": "https://hackerone.com/diffcorp",
        "website": "https://diffcorp.io",
        "is_public": True,
        "offers_bounties": True,
        "in_scope": [
            {"target": "diffcorp.io", "type": "URL"},
            {"target": "api.diffcorp.io", "type": "URL"},
            {"target": "app.diffcorp.io", "type": "URL"},
        ],
        "out_of_scope": [],
    }
    resolver.ingest_program_record(expanded_prog)
    test_db.commit()

    # Should have 2 snapshots now and 1 PROGRAM_SCOPE_ADDED change event
    snapshots_after = test_db.query(ProgramSnapshot).filter(ProgramSnapshot.security_program_id == sp1.id).all()
    assert len(snapshots_after) == 2

    change_events = test_db.query(ProgramChangeEvent).filter(ProgramChangeEvent.security_program_id == sp1.id).all()
    assert len(change_events) == 1
    assert change_events[0].change_type == "PROGRAM_SCOPE_ADDED"
    assert "+2 targets" in change_events[0].summary


# ==============================================================================
# 6. API ROUTER TESTS
# ==============================================================================

def test_api_company_stats_endpoint(client, test_db):
    # Populate test data
    c1 = Company(name="Alpha", canonical_domain="alpha.io")
    c2 = Company(name="Beta", canonical_domain="beta.io")
    test_db.add_all([c1, c2])
    test_db.flush()

    p1 = SecurityProgram(company_id=c1.id, platform="HackerOne", program_name="Alpha Prog")
    t1 = Target(domain="alpha.io", company_id=c1.id, monitoring_status="MONITORED", authorization_confirmed=True)
    a1 = Asset(name="alpha-root", hostname="alpha.io", company_id=c1.id, normalized_hostname="alpha.io", scope_status="IN_SCOPE")
    test_db.add_all([p1, t1, a1])
    test_db.commit()

    resp = client.get("/api/v1/companies/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["canonical_companies"] == 2
    assert data["public_programs"] == 1
    assert data["authorized_targets"] == 1
    assert data["observed_assets"] == 1


def test_api_list_companies_contains_program_counts(client, test_db):
    c1 = Company(name="Gamma", canonical_domain="gamma.com")
    test_db.add(c1)
    test_db.flush()

    sp1 = SecurityProgram(company_id=c1.id, platform="HackerOne", program_name="Gamma H1")
    sp2 = SecurityProgram(company_id=c1.id, platform="Bugcrowd", program_name="Gamma BC")
    test_db.add_all([sp1, sp2])
    test_db.commit()

    resp = client.get("/api/v1/companies?q=gamma")
    assert resp.status_code == 200
    items = resp.json().get("items", [])
    assert len(items) == 1
    assert items[0]["name"] == "Gamma"
    assert items[0]["programs_count"] == 2


def test_api_programs_endpoints(client, test_db):
    c = Company(name="Delta Corp", canonical_domain="delta.com")
    test_db.add(c)
    test_db.flush()

    sp = SecurityProgram(
        company_id=c.id,
        platform="HackerOne",
        program_name="Delta Bug Bounty",
        program_handle="delta",
        program_type="BUG_BOUNTY",
        offers_bounties=True,
        min_bounty=500.0,
        max_bounty=15000.0,
        currency="USD",
        submission_state="OPEN",
        scope_summary="10 targets in scope",
    )
    test_db.add(sp)
    test_db.flush()

    rule = ProgramScopeRule(
        security_program_id=sp.id,
        pattern="*.delta.com",
        asset_type="URL",
        inclusion_type="INCLUDE",
    )
    test_db.add(rule)
    test_db.commit()

    # 1. /api/v1/programs/stats
    stats_resp = client.get("/api/v1/programs/stats")
    assert stats_resp.status_code == 200
    stats_data = stats_resp.json()
    assert stats_data["total_programs"] >= 1
    assert stats_data["bounty_programs"] >= 1
    assert stats_data["platform_breakdown"].get("HackerOne") >= 1

    # 2. /api/v1/programs (list)
    list_resp = client.get("/api/v1/programs?q=delta")
    assert list_resp.status_code == 200
    items = list_resp.json().get("items", [])
    assert len(items) == 1
    assert items[0]["program_name"] == "Delta Bug Bounty"
    assert items[0]["company_name"] == "Delta Corp"
    assert items[0]["max_bounty"] == 15000.0
    assert items[0]["scope_rules_count"] == 1

    # 3. /api/v1/programs/{id} (detail)
    detail_resp = client.get(f"/api/v1/programs/{sp.id}")
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert detail["id"] == sp.id
    assert detail["company"]["canonical_domain"] == "delta.com"
    assert len(detail["scope_rules"]) == 1
    assert detail["scope_rules"][0]["pattern"] == "*.delta.com"
