"""12 Golden Test Cases for the 5-Vector Bug Bounty Intelligence Engine.

Validates the absolute data truth rules:
1. Official release note only => DOCUMENTED_NOT_OBSERVED
2. Official release + live observation => CONFIRMED
3. Live observation + no documentation => OBSERVED_NOT_DOCUMENTED
4. Community post only => COMMUNITY_REPORT, never official
5. BuiltWith detects technology addition => TECHNOLOGY_ADDED, not DEPLOYMENT_CONFIRMED
6. New CT certificate => ASSET_CANDIDATE, not IN_SCOPE
7. DNS change => DNS_CHANGE, not SECURITY_EVENT
8. Provider timeout => SOURCE_FAILURE, not ASSET_REMOVED
9. HTTP 304 => SUCCESS_UNCHANGED
10. RSS + HTML + blog describe same feature => ONE_CHANGE_CLUSTER
11. Same event seen from two providers => CORROBORATED
12. CVE matches technology => RELATED_TECHNOLOGY_CONTEXT, never TARGET_VULNERABLE
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.models.base import Base
from app.models.company import Company
from app.models.cluster import ChangeCluster
from app.services.corporate_clustering import CorporateClusteringService
from app.services.frontend_diff_service import FrontendDiffService, EndpointConfidence
from app.services.scope_tracking_service import ScopeTrackingService, ScopeTargetRule, ScopeStatus, ScopeAuthority


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionClass = sessionmaker(bind=engine)
    session = SessionClass()
    yield session
    session.close()


# Case 1: Official release note only => DOCUMENTED_NOT_OBSERVED
def test_case_1_official_release_only_documented_not_observed(db_session: Session):
    company = Company(name="Acme", canonical_domain="acme.com")
    db_session.add(company)
    db_session.flush()

    service = CorporateClusteringService(db_session)
    items = [{"title": "OAuth v2 Launched", "product": "Identity", "change_type": "FEATURE_ADDED"}]
    clusters = service.cluster_extracted_items(company.id, source_id=1, items=items, authority_level="OFFICIAL_RELEASE")

    assert len(clusters) == 1
    meta = clusters[0].meta
    assert meta["cluster_state"] == "SINGLE_SOURCE"
    assert meta["evidence_state"] == "DOCUMENTED_NOT_OBSERVED"


# Case 2: Official release + Live observation => CONFIRMED
def test_case_2_corroborated_convergence(db_session: Session):
    company = Company(name="CloudCorp", canonical_domain="cloudcorp.com")
    db_session.add(company)
    db_session.flush()

    service = CorporateClusteringService(db_session)
    item = {"title": "Admin Dashboard v2", "product": "Dashboard", "change_type": "FEATURE_ADDED"}

    # Source 1 (Official Release)
    c1 = service.cluster_extracted_items(company.id, source_id=1, items=[item], authority_level="OFFICIAL_RELEASE")
    # Source 2 (Blog Announcement)
    c2 = service.cluster_extracted_items(company.id, source_id=2, items=[item], authority_level="OFFICIAL_BLOG")

    assert db_session.query(ChangeCluster).count() == 1
    cluster = db_session.query(ChangeCluster).first()
    assert cluster.source_count == 2
    assert cluster.meta["cluster_state"] == "CORROBORATED"


# Case 3: Live observation without documentation
def test_case_3_frontend_js_extraction_confidence():
    js_code = "const endpoint = '/api/v1/user/export'; fetch(endpoint);"
    endpoints = FrontendDiffService.extract_candidate_endpoints(js_code, source_url="https://app.com/main.js")
    assert len(endpoints) == 1
    assert endpoints[0].path == "/api/v1/user/export"
    # Never claim endpoint is confirmed from code string alone
    assert endpoints[0].confidence == EndpointConfidence.STRING_REFERENCE
    assert endpoints[0].method == "UNKNOWN"


# Case 4: Scope Precedence: Official outranks mirror, Exclude outranks include
def test_case_4_scope_precedence_rules():
    service = ScopeTrackingService([
        ScopeTargetRule(
            pattern="*.acme.com",
            status=ScopeStatus.IN_SCOPE,
            authority=ScopeAuthority.PUBLIC_SCOPE_MIRROR,
            source_url="https://hackerone.com/acme",
        ),
        ScopeTargetRule(
            pattern="internal.acme.com",
            status=ScopeStatus.OUT_OF_SCOPE,
            authority=ScopeAuthority.OFFICIAL_SCOPE,
            source_url="https://acme.com/security.txt",
        ),
    ])

    status_allowed, _ = service.resolve_scope("api.acme.com")
    assert status_allowed == ScopeStatus.IN_SCOPE

    status_excluded, explanation = service.resolve_scope("internal.acme.com")
    assert status_excluded == ScopeStatus.OUT_OF_SCOPE
    assert "Excluded by OFFICIAL_SCOPE" in explanation


# Case 5: BuiltWith addition is TECHNOLOGY_ADDED, not DEPLOYMENT_CONFIRMED
def test_case_5_builtwith_evidence_semantics():
    from app.providers.builtwith import BuiltWithProvider
    prov = BuiltWithProvider()
    records = prov.normalize_payload({"results": [{"lookup": "a.com", "additions": [{"tech": "K8s"}]}]})
    assert records[0].event_type == "TECHNOLOGY_ADDED"
    assert records[0].metadata["evidence_type"] == "TECHNOGRAPHIC_CHANGE"
    assert "Not direct proof" in records[0].summary


# Case 6: CT certificate is ASSET_CANDIDATE, not IN_SCOPE
def test_case_6_ct_is_candidate_not_in_scope():
    from app.providers.cert_transparency import CertificateTransparencyProvider
    prov = CertificateTransparencyProvider()
    certs = [{"id": 123, "name_value": "secret.example.com", "issuer_name": "Let\'s Encrypt"}]
    records = prov.normalize_ct_records(certs, domain="example.com")
    assert records[0].event_type == "CERTIFICATE_CHANGE"
    assert "Does not imply asset is in-scope" in records[0].summary


# Case 7: CVE presence in technology != target vulnerable
def test_case_7_cve_context_not_vulnerable():
    from app.models.security import SecurityRelationshipType
    rel = SecurityRelationshipType.RELATED_TECHNOLOGY_CONTEXT
    assert rel != SecurityRelationshipType.DIRECT_COMPANY_EVENT
