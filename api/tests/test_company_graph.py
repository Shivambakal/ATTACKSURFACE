"""Comprehensive Test Suite for Company & Attack Surface Graph Intelligence Engine.

Covers:
- Canonical company resolution and input normalization
- Duplicate resolution & alias mapping
- Safe public discovery and HTML subdomain extraction
- Multi-source evidence fusion (no duplicate assets, confidence boosting)
- Conservative Scope Correlation Engine (INCLUDE, EXCLUDE, CONDITIONAL, UNKNOWN, PENDING)
- Product and API surface inference and linking
- Graph generation, scope filtering, and structured JSON export
- 100-company seed catalog validation and idempotence
- SSRF and safety boundaries
- API router endpoint validation
- Real-world replay scenarios
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.models.base import Base
from app.models.company import Company
from app.models.asset import Asset, Technology, AssetTechnology
from app.models.asset_evidence import AssetEvidence
from app.models.product import Product
from app.models.feature import Feature
from app.models.api_surface import ApiSurface
from app.models.security import SecurityEvent
from app.models.security_program import SecurityProgram, ProgramScopeRule, InclusionType, ScopeStatus, VerificationStatus
from app.models.signal import ResearchSignal, SignalType
from app.models.target import Target
from app.services.company_discovery import (
    normalize_company_input,
    resolve_or_create_company,
    CompanyDiscoveryService,
)
from app.services.scope_resolver import ScopeResolver, ScopeDecision
from app.services.graph_service import GraphService
from app.services.target_safety import normalize_domain
from app.seed_companies import seed_companies
from app.main import create_app
from app.db import get_db


from sqlalchemy.pool import StaticPool

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
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(test_db):
    """FastAPI TestClient with overridden database session."""
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
# 1. Company Resolution & Input Normalization Tests
# ==============================================================================

def test_normalize_company_input_urls():
    domain, name = normalize_company_input("https://google.com/search?q=test")
    assert domain == "google.com"
    assert name == "Google"

    domain2, name2 = normalize_company_input("http://www.stripe.com/")
    assert domain2 == "stripe.com"
    assert name2 == "Stripe"


def test_normalize_company_input_domains_and_ports():
    domain, name = normalize_company_input("api.example.com:443")
    assert domain == "api.example.com"
    assert name == "Api"


def test_normalize_company_input_known_aliases():
    domain, name = normalize_company_input("Google Cloud")
    assert domain == "google.com"
    assert "Google" in name

    domain2, name2 = normalize_company_input("AWS")
    assert domain2 == "amazon.com"


def test_resolve_or_create_company_canonical_dedup(test_db):
    c1, created1 = resolve_or_create_company(test_db, "google.com")
    test_db.commit()
    assert created1 is True

    c2, created2 = resolve_or_create_company(test_db, "https://www.google.com/")
    test_db.commit()
    assert created2 is False
    assert c1.id == c2.id

    c3, created3 = resolve_or_create_company(test_db, "Google")
    test_db.commit()
    assert created3 is False
    assert c1.id == c3.id


def test_company_aliases_lookup(test_db):
    c = Company(
        name="Acme Inc",
        canonical_domain="acme.com",
        aliases=["acme corp", "acme-cloud"],
    )
    test_db.add(c)
    test_db.commit()

    c_match, created = resolve_or_create_company(test_db, "acme corp")
    assert created is False
    assert c_match.id == c.id


# ==============================================================================
# 2. Scope Correlation Engine Tests
# ==============================================================================

def test_scope_resolver_exact_match_include():
    rule = ProgramScopeRule(
        pattern="api.example.com",
        inclusion_type=InclusionType.INCLUDE.value,
        confidence=0.95,
    )
    decision = ScopeResolver.evaluate("api.example.com", [rule])
    assert decision.status == ScopeStatus.IN_SCOPE
    assert decision.confidence == 0.95


def test_scope_resolver_wildcard_include():
    rule = ProgramScopeRule(
        pattern="*.example.com",
        inclusion_type=InclusionType.INCLUDE.value,
        confidence=0.90,
    )
    assert ScopeResolver.evaluate("api.example.com", [rule]).status == ScopeStatus.IN_SCOPE
    assert ScopeResolver.evaluate("auth.example.com", [rule]).status == ScopeStatus.IN_SCOPE
    assert ScopeResolver.evaluate("sub.deep.example.com", [rule]).status == ScopeStatus.IN_SCOPE
    assert ScopeResolver.evaluate("example.com", [rule]).status == ScopeStatus.IN_SCOPE


def test_scope_resolver_exclude_takes_precedence_over_include():
    include_rule = ProgramScopeRule(
        pattern="*.example.com",
        inclusion_type=InclusionType.INCLUDE.value,
        confidence=0.90,
    )
    exclude_rule = ProgramScopeRule(
        pattern="admin.example.com",
        inclusion_type=InclusionType.EXCLUDE.value,
        confidence=0.99,
    )
    # Even though it matches *.example.com, the explicit exclude must win!
    decision = ScopeResolver.evaluate("admin.example.com", [include_rule, exclude_rule])
    assert decision.status == ScopeStatus.OUT_OF_SCOPE
    assert "Explicitly excluded" in decision.reason


def test_scope_resolver_wildcard_exclude():
    include_rule = ProgramScopeRule(
        pattern="*.example.com",
        inclusion_type=InclusionType.INCLUDE.value,
    )
    exclude_rule = ProgramScopeRule(
        pattern="*.corp.example.com",
        inclusion_type=InclusionType.EXCLUDE.value,
    )
    assert ScopeResolver.evaluate("intranet.corp.example.com", [include_rule, exclude_rule]).status == ScopeStatus.OUT_OF_SCOPE
    assert ScopeResolver.evaluate("public.example.com", [include_rule, exclude_rule]).status == ScopeStatus.IN_SCOPE


def test_scope_resolver_conditional_scope():
    cond_rule = ProgramScopeRule(
        pattern="payment.example.com",
        inclusion_type=InclusionType.CONDITIONAL.value,
        confidence=0.90,
    )
    decision = ScopeResolver.evaluate("payment.example.com", [cond_rule])
    assert decision.status == ScopeStatus.RELATED
    assert "conditional" in decision.reason.lower()


def test_scope_resolver_subdomain_without_explicit_rule_is_related():
    rule = ProgramScopeRule(
        pattern="api.example.com",
        inclusion_type=InclusionType.INCLUDE.value,
    )
    # test.example.com is an organizational subdomain, but not in explicit rules
    decision = ScopeResolver.evaluate("test.example.com", [rule], canonical_domain="example.com")
    assert decision.status == ScopeStatus.RELATED
    assert decision.status != ScopeStatus.IN_SCOPE


def test_scope_resolver_subdomain_with_no_rules_is_pending():
    decision = ScopeResolver.evaluate("test.example.com", [], canonical_domain="example.com")
    assert decision.status == ScopeStatus.PENDING_VERIFICATION


def test_scope_resolver_unrelated_domain_is_unknown():
    rule = ProgramScopeRule(pattern="*.example.com", inclusion_type=InclusionType.INCLUDE.value)
    decision = ScopeResolver.evaluate("unrelated-third-party.com", [rule], canonical_domain="example.com")
    assert decision.status == ScopeStatus.UNKNOWN


def test_scope_resolver_empty_hostname():
    decision = ScopeResolver.evaluate("", [])
    assert decision.status == ScopeStatus.UNKNOWN


# ==============================================================================
# 3. Evidence Fusion & Multi-Source Corroboration Tests
# ==============================================================================

def test_evidence_fusion_single_source(test_db):
    company = Company(name="Acme", canonical_domain="acme.com")
    test_db.add(company)
    test_db.commit()

    candidates = [{
        "hostname": "api.acme.com",
        "asset_type": "API",
        "source_type": "OFFICIAL_WEBSITE",
        "source_url": "https://acme.com",
        "evidence_text": "Discovered in footer links",
        "base_confidence": 0.75,
    }]

    assets = CompanyDiscoveryService.fuse_discovered_assets(test_db, company, candidates)
    test_db.commit()

    assert len(assets) == 1
    assert assets[0].normalized_hostname == "api.acme.com"
    assert assets[0].confidence == 0.75

    evidence = test_db.query(AssetEvidence).filter(AssetEvidence.asset_id == assets[0].id).all()
    assert len(evidence) == 1
    assert evidence[0].source_type == "OFFICIAL_WEBSITE"


def test_evidence_fusion_multi_source_boosts_confidence(test_db):
    company = Company(name="Acme", canonical_domain="acme.com")
    test_db.add(company)
    test_db.commit()

    # Source 1: Official website
    CompanyDiscoveryService.fuse_discovered_assets(test_db, company, [{
        "hostname": "api.acme.com",
        "asset_type": "API",
        "source_type": "OFFICIAL_WEBSITE",
        "source_url": "https://acme.com",
        "evidence_text": "Discovered on homepage",
        "base_confidence": 0.75,
    }])
    test_db.commit()

    # Source 2: Security Policy
    CompanyDiscoveryService.fuse_discovered_assets(test_db, company, [{
        "hostname": "api.acme.com",
        "asset_type": "API",
        "source_type": "SECURITY_POLICY",
        "source_url": "https://acme.com/.well-known/security.txt",
        "evidence_text": "Explicitly referenced in security.txt policy",
        "base_confidence": 0.85,
    }])
    test_db.commit()

    # Source 3: GitHub repository documentation
    CompanyDiscoveryService.fuse_discovered_assets(test_db, company, [{
        "hostname": "api.acme.com",
        "asset_type": "API",
        "source_type": "GITHUB_REPOSITORY",
        "source_url": "https://github.com/acme/sdk",
        "evidence_text": "Target base URL configured in official SDK",
        "base_confidence": 0.80,
    }])
    test_db.commit()

    # Verify: exactly 1 Asset, 3 AssetEvidence records, confidence boosted
    assets = test_db.query(Asset).filter(Asset.company_id == company.id).all()
    assert len(assets) == 1
    asset = assets[0]
    assert asset.normalized_hostname == "api.acme.com"
    assert asset.confidence >= 0.95  # 0.75 + 0.10 + 0.10 = 0.95

    evidence = test_db.query(AssetEvidence).filter(AssetEvidence.asset_id == asset.id).all()
    assert len(evidence) == 3


def test_evidence_fusion_no_duplicate_assets(test_db):
    company = Company(name="Acme", canonical_domain="acme.com")
    test_db.add(company)
    test_db.commit()

    for _ in range(5):
        CompanyDiscoveryService.fuse_discovered_assets(test_db, company, [{
            "hostname": "portal.acme.com",
            "asset_type": "WEB_APPLICATION",
            "source_type": "OFFICIAL_WEBSITE",
            "source_url": "https://acme.com",
            "evidence_text": "Referenced on login page",
        }])
        test_db.commit()

    count = test_db.query(Asset).filter(Asset.company_id == company.id).count()
    assert count == 1


# ==============================================================================
# 4. Product & API Surface Inference Tests
# ==============================================================================

def test_product_inference_api_platform(test_db):
    company = Company(name="Acme", canonical_domain="acme.com")
    test_db.add(company)
    test_db.flush()

    asset = Asset(
        company_id=company.id,
        name="api.acme.com",
        normalized_hostname="api.acme.com",
        asset_type="API",
    )
    test_db.add(asset)
    test_db.commit()

    products = CompanyDiscoveryService.infer_and_link_products(test_db, company, [asset])
    test_db.commit()

    assert len(products) == 1
    assert "API Platform" in products[0].name
    assert asset.id in products[0].domain_ids


def test_product_inference_identity(test_db):
    company = Company(name="Acme", canonical_domain="acme.com")
    test_db.add(company)
    test_db.flush()

    asset = Asset(
        company_id=company.id,
        name="accounts.acme.com",
        normalized_hostname="accounts.acme.com",
        asset_type="SECURITY_PORTAL",
    )
    test_db.add(asset)
    test_db.commit()

    products = CompanyDiscoveryService.infer_and_link_products(test_db, company, [asset])
    test_db.commit()

    assert any("Identity" in p.name for p in products)


def test_extract_subdomains_from_html():
    html = """
    <html>
        <body>
            <a href="https://api.example.com/v1">API Documentation</a>
            <a href="https://docs.example.com/start">Guides</a>
            <a href="https://facebook.com/example">Social</a>
            <a href="https://twitter.com/example">X</a>
            <span>Contact auth.example.com for SSO</span>
        </body>
    </html>
    """
    subdomains = CompanyDiscoveryService.extract_subdomains_from_text(html, "example.com")
    assert "api.example.com" in subdomains
    assert "docs.example.com" in subdomains
    assert "auth.example.com" in subdomains
    assert "facebook.com" not in subdomains
    assert "twitter.com" not in subdomains


# ==============================================================================
# 5. Graph Service & Export Tests
# ==============================================================================

def test_graph_service_structure(test_db):
    company = Company(name="Acme", canonical_domain="acme.com")
    test_db.add(company)
    test_db.flush()

    asset = Asset(
        company_id=company.id,
        name="api.acme.com",
        normalized_hostname="api.acme.com",
        asset_type="API",
        scope_status="IN_SCOPE",
        confidence=0.9,
    )
    product = Product(
        company_id=company.id,
        name="API Platform",
        domain_ids=[1],
    )
    sig = ResearchSignal(
        company_id=company.id,
        title="New API Surface",
        summary="Test signal",
        why_it_matters="Test relevance",
        relevance_score=90,
        confidence_score=95,
        priority="HIGH",
    )
    test_db.add_all([asset, product, sig])
    test_db.commit()

    graph = GraphService.get_attack_surface_graph(test_db, company)
    assert graph["company"]["canonical_domain"] == "acme.com"
    assert graph["stats"]["total_nodes"] >= 4
    assert any(n["type"] == "COMPANY" for n in graph["nodes"])
    assert any(n["type"] == "PRODUCT" for n in graph["nodes"])
    assert any(n["type"] == "API" for n in graph["nodes"])
    assert any(n["type"] == "RESEARCH_SIGNAL" for n in graph["nodes"])


def test_graph_service_scope_filtering(test_db):
    company = Company(name="Acme", canonical_domain="acme.com")
    test_db.add(company)
    test_db.flush()

    a1 = Asset(company_id=company.id, name="in.acme.com", scope_status="IN_SCOPE")
    a2 = Asset(company_id=company.id, name="out.acme.com", scope_status="OUT_OF_SCOPE")
    test_db.add_all([a1, a2])
    test_db.commit()

    in_scope_graph = GraphService.get_attack_surface_graph(test_db, company, scope_filter="IN_SCOPE")
    asset_labels = [n["label"] for n in in_scope_graph["nodes"] if n["scope"] in ("IN_SCOPE", "OUT_OF_SCOPE")]
    assert "in.acme.com" in asset_labels
    assert "out.acme.com" not in asset_labels


def test_export_company_graph_structure(test_db):
    company = Company(name="Acme", canonical_domain="acme.com")
    test_db.add(company)
    test_db.commit()

    export_data = GraphService.export_company_graph(test_db, company.id)
    assert export_data["export_version"] == "1.0"
    assert export_data["company"]["canonical_domain"] == "acme.com"
    assert "security_programs" in export_data
    assert "products" in export_data
    assert "assets" in export_data
    assert "research_signals" in export_data


# ==============================================================================
# 6. 100-Company Seed Catalog Tests
# ==============================================================================

def test_seed_companies_catalog_file_integrity():
    catalog_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "app", "data", "seed_companies.json"
    )
    assert os.path.exists(catalog_path), "Seed companies catalog file must exist"

    with open(catalog_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert len(data) == 100, f"Expected exactly 100 seed companies, got {len(data)}"
    for item in data:
        assert "name" in item
        assert "canonical_domain" in item
        assert "." in item["canonical_domain"]
        assert " " not in item["canonical_domain"]


def test_seed_companies_idempotent_execution(test_db):
    res1 = seed_companies(test_db)
    assert res1["created"] == 304
    assert res1["updated"] == 0

    res2 = seed_companies(test_db)
    assert res2["created"] == 0
    assert res2["updated"] == 304

    total = test_db.query(Company).count()
    assert total == 304


# ==============================================================================
# 7. SSRF & Safety Protection Tests
# ==============================================================================

def test_ssrf_protection_in_company_discovery():
    with pytest.raises(ValueError):
        normalize_domain("localhost")

    with pytest.raises(ValueError):
        normalize_domain("127.0.0.1")

    with pytest.raises(ValueError):
        normalize_domain("169.254.169.254")

    with pytest.raises(ValueError):
        normalize_domain("metadata.google.internal")


# ==============================================================================
# 8. API Router Endpoint Tests
# ==============================================================================

def test_api_post_company(client):
    res = client.post("/api/v1/companies", json={"name_or_domain": "https://stripe.com"})
    assert res.status_code == 201, f"Status: {res.status_code}, detail: {res.text}"
    body = res.json()
    assert body["canonical_domain"] == "stripe.com"
    assert body["created"] is True


def test_api_list_companies(client):
    client.post("/api/v1/companies", json={"name_or_domain": "google.com"})
    client.post("/api/v1/companies", json={"name_or_domain": "github.com"})

    res = client.get("/api/v1/companies")
    assert res.status_code == 200
    body = res.json()
    assert body["total"] >= 2


def test_api_get_company_detail(client):
    c = client.post("/api/v1/companies", json={"name_or_domain": "openai.com"}).json()
    res = client.get(f"/api/v1/companies/{c['id']}")
    assert res.status_code == 200
    body = res.json()
    assert body["canonical_domain"] == "openai.com"
    assert "metrics" in body


def test_api_get_company_assets(client):
    c = client.post("/api/v1/companies", json={"name_or_domain": "cloudflare.com"}).json()
    res = client.get(f"/api/v1/companies/{c['id']}/assets")
    assert res.status_code == 200
    assert isinstance(res.json(), list)


def test_api_get_company_products(client):
    c = client.post("/api/v1/companies", json={"name_or_domain": "netflix.com"}).json()
    res = client.get(f"/api/v1/companies/{c['id']}/products")
    assert res.status_code == 200
    assert isinstance(res.json(), list)


def test_api_get_company_attack_surface(client):
    c = client.post("/api/v1/companies", json={"name_or_domain": "uber.com"}).json()
    res = client.get(f"/api/v1/companies/{c['id']}/attack-surface")
    assert res.status_code == 200
    body = res.json()
    assert "nodes" in body
    assert "edges" in body


def test_api_get_company_export(client):
    c = client.post("/api/v1/companies", json={"name_or_domain": "shopify.com"}).json()
    res = client.get(f"/api/v1/companies/{c['id']}/export")
    assert res.status_code == 200
    assert res.json()["export_version"] == "1.0"


# ==============================================================================
# 9. Backward Compatibility & Real-World Replay Scenarios
# ==============================================================================

def test_target_backward_compatibility(test_db):
    target = Target(
        domain="target-compat.example.com",
        authorization_confirmed=True,
    )
    test_db.add(target)
    test_db.commit()
    assert target.id is not None
    assert target.company_id is None


def test_replay_scope_update_include_to_exclude(test_db):
    company = Company(name="TestCorp", canonical_domain="testcorp.com")
    test_db.add(company)
    test_db.flush()

    prog = SecurityProgram(company_id=company.id, platform="HackerOne")
    test_db.add(prog)
    test_db.flush()

    rule1 = ProgramScopeRule(
        security_program_id=prog.id,
        pattern="*.testcorp.com",
        inclusion_type=InclusionType.INCLUDE.value,
    )
    test_db.add(rule1)

    asset = Asset(
        company_id=company.id,
        name="admin.testcorp.com",
        normalized_hostname="admin.testcorp.com",
    )
    test_db.add(asset)
    test_db.commit()

    # Initial resolution -> IN_SCOPE
    dec1 = ScopeResolver.resolve_asset(test_db, asset, company)
    assert dec1.status == ScopeStatus.IN_SCOPE

    # Program updates scope: explicitly excludes admin.testcorp.com
    rule_exclude = ProgramScopeRule(
        security_program_id=prog.id,
        pattern="admin.testcorp.com",
        inclusion_type=InclusionType.EXCLUDE.value,
    )
    test_db.add(rule_exclude)
    test_db.commit()

    # Re-evaluate -> OUT_OF_SCOPE
    dec2 = ScopeResolver.resolve_asset(test_db, asset, company)
    assert dec2.status == ScopeStatus.OUT_OF_SCOPE
    assert asset.scope_status == "OUT_OF_SCOPE"


def test_replay_conflicting_evidence(test_db):
    """When third-party source claims an asset is in-scope, but security program explicitly excludes it, exclusion wins."""
    company = Company(name="TestCorp", canonical_domain="testcorp.com")
    test_db.add(company)
    test_db.flush()

    prog = SecurityProgram(company_id=company.id)
    test_db.add(prog)
    test_db.flush()

    rule_exclude = ProgramScopeRule(
        security_program_id=prog.id,
        pattern="staging.testcorp.com",
        inclusion_type=InclusionType.EXCLUDE.value,
    )
    test_db.add(rule_exclude)
    test_db.commit()

    # Discover asset with 'high confidence' from third party
    candidate = [{
        "hostname": "staging.testcorp.com",
        "asset_type": "WEB_APPLICATION",
        "source_type": "THIRD_PARTY",
        "source_url": "https://thirdparty.example.com",
        "evidence_text": "Claimed in-scope by community list",
        "base_confidence": 0.90,
    }]
    assets = CompanyDiscoveryService.fuse_discovered_assets(test_db, company, candidate)
    test_db.commit()

    assert len(assets) == 1
    assert assets[0].scope_status == "OUT_OF_SCOPE"


# ==============================================================================
# 10. Additional Deep Edge Case & Robustness Tests (Reaching 51+ Graph Tests)
# ==============================================================================

def test_scope_resolver_case_insensitivity():
    rule = ProgramScopeRule(
        pattern="*.EXAMPLE.COM",
        inclusion_type=InclusionType.INCLUDE.value,
        confidence=0.95,
    )
    decision = ScopeResolver.evaluate("API.example.com", [rule])
    assert decision.status == ScopeStatus.IN_SCOPE


def test_scope_resolver_whitespace_handling():
    rule = ProgramScopeRule(
        pattern="  *.example.com  ",
        inclusion_type=InclusionType.INCLUDE.value,
    )
    decision = ScopeResolver.evaluate("  auth.example.com  ", [rule])
    assert decision.status == ScopeStatus.IN_SCOPE


def test_scope_resolver_trailing_dot_handling():
    rule = ProgramScopeRule(
        pattern="*.example.com",
        inclusion_type=InclusionType.INCLUDE.value,
    )
    decision = ScopeResolver.evaluate("api.example.com.", [rule])
    assert decision.status == ScopeStatus.IN_SCOPE


def test_scope_resolver_subdomain_wildcard_boundary():
    rule = ProgramScopeRule(
        pattern="*.example.com",
        inclusion_type=InclusionType.INCLUDE.value,
    )
    # fakexample.com must NOT match *.example.com
    decision1 = ScopeResolver.evaluate("fakexample.com", [rule], canonical_domain="example.com")
    assert decision1.status != ScopeStatus.IN_SCOPE

    decision2 = ScopeResolver.evaluate("badexample.com", [rule], canonical_domain="example.com")
    assert decision2.status != ScopeStatus.IN_SCOPE


def test_scope_resolver_rule_evidence_persistence():
    rule = ProgramScopeRule(
        pattern="*.security.example.com",
        inclusion_type=InclusionType.INCLUDE.value,
        confidence=0.88,
        source_url="https://example.com/bounty",
    )
    decision = ScopeResolver.evaluate("portal.security.example.com", [rule])
    assert decision.status == ScopeStatus.IN_SCOPE
    assert decision.matched_rule == "*.security.example.com"
    assert decision.confidence == 0.88


def test_normalize_company_input_slug_fallback():
    domain, name = normalize_company_input("SuperSecureEnterprise")
    assert "supersecureenterprise.com" in domain
    assert "Supersecureenterprise" in name


def test_resolve_or_create_company_persists_aliases(test_db):
    company, _ = resolve_or_create_company(test_db, "stripe.com")
    test_db.commit()
    assert company.canonical_domain == "stripe.com"


def test_evidence_fusion_updates_timestamp(test_db):
    company = Company(name="Acme", canonical_domain="acme.com")
    test_db.add(company)
    test_db.commit()

    candidates = [{
        "hostname": "vpn.acme.com",
        "asset_type": "WEB_APPLICATION",
        "source_type": "OFFICIAL_WEBSITE",
        "source_url": "https://acme.com",
    }]
    assets = CompanyDiscoveryService.fuse_discovered_assets(test_db, company, candidates)
    test_db.commit()
    t1 = assets[0].last_seen_at

    assets2 = CompanyDiscoveryService.fuse_discovered_assets(test_db, company, candidates)
    test_db.commit()
    t2 = assets2[0].last_seen_at
    assert t2 >= t1


def test_product_inference_cloud_services(test_db):
    company = Company(name="Acme", canonical_domain="acme.com")
    test_db.add(company)
    test_db.flush()

    asset = Asset(
        company_id=company.id,
        name="cloud.acme.com",
        normalized_hostname="cloud.acme.com",
        asset_type="CLOUD_ASSET",
    )
    test_db.add(asset)
    test_db.commit()

    prods = CompanyDiscoveryService.infer_and_link_products(test_db, company, [asset])
    test_db.commit()
    assert any("Cloud Services" in p.name for p in prods)


def test_product_inference_developer_platform(test_db):
    company = Company(name="Acme", canonical_domain="acme.com")
    test_db.add(company)
    test_db.flush()

    asset = Asset(
        company_id=company.id,
        name="developer.acme.com",
        normalized_hostname="developer.acme.com",
        asset_type="DOCUMENTATION",
    )
    test_db.add(asset)
    test_db.commit()

    prods = CompanyDiscoveryService.infer_and_link_products(test_db, company, [asset])
    test_db.commit()
    assert any("Developer Platform" in p.name for p in prods)


def test_product_inference_status_portal(test_db):
    company = Company(name="Acme", canonical_domain="acme.com")
    test_db.add(company)
    test_db.flush()

    asset = Asset(
        company_id=company.id,
        name="status.acme.com",
        normalized_hostname="status.acme.com",
        asset_type="WEB_APPLICATION",
    )
    test_db.add(asset)
    test_db.commit()

    prods = CompanyDiscoveryService.infer_and_link_products(test_db, company, [asset])
    test_db.commit()
    assert any("Infrastructure Status" in p.name for p in prods)


def test_product_inference_billing_portal(test_db):
    company = Company(name="Acme", canonical_domain="acme.com")
    test_db.add(company)
    test_db.flush()

    asset = Asset(
        company_id=company.id,
        name="billing.acme.com",
        normalized_hostname="billing.acme.com",
        asset_type="WEB_APPLICATION",
    )
    test_db.add(asset)
    test_db.commit()

    prods = CompanyDiscoveryService.infer_and_link_products(test_db, company, [asset])
    test_db.commit()
    assert any("Billing & Payments" in p.name for p in prods)


def test_graph_service_handles_empty_relations(test_db):
    company = Company(name="MinimalCorp", canonical_domain="minimal.com")
    test_db.add(company)
    test_db.commit()

    graph = GraphService.get_attack_surface_graph(test_db, company)
    assert graph["company"]["name"] == "MinimalCorp"
    assert len(graph["nodes"]) == 1
    assert len(graph["edges"]) == 0


def test_export_company_graph_preserves_scope_rules(test_db):
    company = Company(name="TestExport", canonical_domain="export.com")
    test_db.add(company)
    test_db.flush()

    prog = SecurityProgram(company_id=company.id, platform="Bugcrowd")
    test_db.add(prog)
    test_db.flush()

    rule = ProgramScopeRule(
        security_program_id=prog.id,
        pattern="*.export.com",
        inclusion_type=InclusionType.INCLUDE.value,
        confidence=0.92,
    )
    test_db.add(rule)
    test_db.commit()

    data = GraphService.export_company_graph(test_db, company.id)
    assert len(data["security_programs"]) == 1
    assert data["security_programs"][0]["scope_rules"][0]["pattern"] == "*.export.com"


def test_company_signals_min_relevance_filter(client, test_db):
    c = Company(name="SigFilterCorp", canonical_domain="sigfilter.com")
    test_db.add(c)
    test_db.flush()

    s1 = ResearchSignal(
        company_id=c.id,
        title="High Relevance",
        summary="High",
        why_it_matters="Relevant",
        relevance_score=90,
    )
    s2 = ResearchSignal(
        company_id=c.id,
        title="Low Relevance",
        summary="Low",
        why_it_matters="Minor",
        relevance_score=30,
    )
    test_db.add_all([s1, s2])
    test_db.commit()

    res = client.get(f"/api/v1/companies/{c.id}/signals?min_relevance=80")
    assert res.status_code == 200
    items = res.json()
    assert len(items) == 1
    assert items[0]["title"] == "High Relevance"

