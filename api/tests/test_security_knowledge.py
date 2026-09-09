"""Comprehensive pytest test suite for the Security Knowledge Base.

Uses an in-memory SQLite database — no external services required.
Integration tests that use the real CISA KEV catalog are marked
@pytest.mark.integration and will be skipped by default.

Run non-integration tests::

    python -m pytest tests/test_security_knowledge.py -x -q -m 'not integration'
"""
from __future__ import annotations

import json
import os
import tempfile
from typing import Generator

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

# ---------------------------------------------------------------------------
# We need all models registered before Base.metadata.create_all
# ---------------------------------------------------------------------------
from app.models import (  # noqa: F401 — registers all models
    Base,
    SecurityAdvisory,
    CWEEntry,
    OWASPCategory,
    KnowledgeSource,
    KnowledgeSyncRun,
    VulnerabilityReference,
    advisory_cwe_association,
    advisory_owasp_association,
    cwe_owasp_association,
    BountyEvidence,
)
from app.models.company import Company  # noqa: F401
from app.models.user import User  # noqa: F401
from app.routers.security_knowledge import (
    resolve_vulnerability_class,
    _compute_research_relevance,
    get_advisory_bounty_intelligence,
)

from app.knowledge.taxonomy import (
    CWE_NAMES,
    CWE_TO_VULN_CLASS,
    OWASP_2021,
    CWE_TO_OWASP_2021,
    get_cwe_name,
    normalize_cwe_id,
    normalize_cve_id,
    get_owasp_2021_category_for_cwe,
    get_vuln_class_for_cwe,
)
from app.knowledge.provider_interface import (
    ProviderStatus,
    ProviderHealthReport,
    NVDProvider,
    OSVProvider,
    GitHubAdvisoryProvider,
    OWASPProvider,
    CWEProvider,
)
from app.knowledge.cisa_kev_ingestor import CISAKEVIngestor
from app.knowledge.correlation import SecurityKnowledgeCorrelationService

# ---------------------------------------------------------------------------
# Synthetic test catalog (no real file required)
# ---------------------------------------------------------------------------

TEST_CATALOG = {
    "title": "Test CISA KEV",
    "catalogVersion": "2026.09.02",
    "dateReleased": "2026-09-02T00:00:00Z",
    "count": 3,
    "vulnerabilities": [
        {
            "cveID": "CVE-2021-44228",
            "vendorProject": "Apache",
            "product": "Log4j",
            "vulnerabilityName": "Apache Log4j2 Remote Code Execution Vulnerability",
            "dateAdded": "2021-12-10",
            "shortDescription": "Apache Log4j2 contains a vulnerability.",
            "requiredAction": "Apply mitigations",
            "dueDate": "2021-12-24",
            "knownRansomwareCampaignUse": "Known",
            "forensicTriage": "",
            "notes": "https://logging.apache.org/log4j/2.x/security.html",
            "cwes": ["CWE-917", "CWE-400"],
        },
        {
            "cveID": "CVE-2022-22963",
            "vendorProject": "VMware",
            "product": "Spring Cloud",
            "vulnerabilityName": "VMware Spring Cloud Function RCE",
            "dateAdded": "2022-04-04",
            "shortDescription": "VMware Spring Cloud Function contains an RCE.",
            "requiredAction": "Update to latest version",
            "dueDate": "2022-04-25",
            "knownRansomwareCampaignUse": "Unknown",
            "forensicTriage": "",
            "notes": "",
            "cwes": ["CWE-94"],
        },
        {
            "cveID": "CVE-2021-40539",
            "vendorProject": "Zoho",
            "product": "ManageEngine",
            "vulnerabilityName": "Zoho ManageEngine ADSelfService Plus Authentication Bypass",
            "dateAdded": "2021-11-03",
            "shortDescription": "Zoho ManageEngine ADSelfService Plus contains an authentication bypass.",
            "requiredAction": "Update software",
            "dueDate": "2021-11-17",
            "knownRansomwareCampaignUse": "Known",
            "forensicTriage": "",
            "notes": "",
            "cwes": ["CWE-287"],
        },
    ],
}

REAL_CATALOG_PATH = os.path.join(
    os.path.dirname(__file__),
    "..",
    "..",
    "cisa_kev_catalog.json",
)
REAL_CATALOG_EXISTS = os.path.isfile(REAL_CATALOG_PATH)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def engine():
    """Create an in-memory SQLite engine for the entire test session."""
    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )

    # Enable WAL mode + foreign keys for SQLite
    @event.listens_for(eng, "connect")
    def set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    # Create all tables — including any that reference users/companies
    # We create them in the right order. Since we have FKs disabled in SQLite
    # by default and we're using check_same_thread=False, create_all handles ordering.
    Base.metadata.create_all(bind=eng)
    yield eng
    eng.dispose()


@pytest.fixture()
def db(engine) -> Generator[Session, None, None]:
    """Provide a transactional session that rolls back after each test."""
    connection = engine.connect()
    transaction = connection.begin()
    TestSession = sessionmaker(bind=connection)
    session = TestSession()
    yield session
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture()
def ingestor() -> CISAKEVIngestor:
    return CISAKEVIngestor()


# ---------------------------------------------------------------------------
# 1. Taxonomy — normalize_cwe_id
# ---------------------------------------------------------------------------

class TestNormalizeCweId:
    def test_canonical_form_unchanged(self):
        assert normalize_cwe_id("CWE-79") == "CWE-79"

    def test_lowercase_normalized(self):
        assert normalize_cwe_id("cwe-79") == "CWE-79"

    def test_bare_number(self):
        assert normalize_cwe_id("79") == "CWE-79"

    def test_prefixed_without_dash(self):
        assert normalize_cwe_id("CWE79") == "CWE-79"

    def test_colon_separator(self):
        assert normalize_cwe_id("CWE:79") == "CWE-79"

    def test_underscore_separator(self):
        assert normalize_cwe_id("CWE_79") == "CWE-79"

    def test_multi_digit(self):
        assert normalize_cwe_id("CWE-918") == "CWE-918"

    def test_empty_string(self):
        assert normalize_cwe_id("") == ""


# ---------------------------------------------------------------------------
# 2. Taxonomy — normalize_cve_id
# ---------------------------------------------------------------------------

class TestNormalizeCveId:
    def test_canonical_form(self):
        assert normalize_cve_id("CVE-2021-44228") == "CVE-2021-44228"

    def test_lowercase(self):
        assert normalize_cve_id("cve-2021-44228") == "CVE-2021-44228"

    def test_with_trailing_space(self):
        assert normalize_cve_id("  CVE-2021-44228  ") == "CVE-2021-44228"

    def test_invalid_returns_none(self):
        assert normalize_cve_id("NOTACVE") is None

    def test_empty_returns_none(self):
        assert normalize_cve_id("") is None

    def test_none_returns_none(self):
        assert normalize_cve_id(None) is None


# ---------------------------------------------------------------------------
# 3. Taxonomy — get_cwe_name
# ---------------------------------------------------------------------------

class TestGetCweName:
    def test_known_cwe(self):
        assert "Cross-Site Scripting" in get_cwe_name("CWE-79")

    def test_injection(self):
        assert "Injection" in get_cwe_name("CWE-94")

    def test_authentication(self):
        assert "Authentication" in get_cwe_name("CWE-287")

    def test_unknown_cwe_returns_fallback(self):
        name = get_cwe_name("CWE-99999")
        assert "99999" in name

    def test_lowercase_input(self):
        # normalize_cwe_id called internally
        result = get_cwe_name("cwe-79")
        assert result  # non-empty

    def test_cwe_names_has_50_plus_entries(self):
        assert len(CWE_NAMES) >= 50


# ---------------------------------------------------------------------------
# 4. Taxonomy — OWASP and vuln-class lookup
# ---------------------------------------------------------------------------

class TestOwaspAndVulnClass:
    def test_owasp_2021_has_10_entries(self):
        assert len(OWASP_2021) == 10

    def test_owasp_category_for_injection_cwe(self):
        cat = get_owasp_2021_category_for_cwe("CWE-79")
        assert cat == "A03:2021"

    def test_owasp_category_for_auth_cwe(self):
        cat = get_owasp_2021_category_for_cwe("CWE-287")
        assert cat == "A07:2021"

    def test_owasp_category_for_ssrf_cwe(self):
        cat = get_owasp_2021_category_for_cwe("CWE-918")
        assert cat == "A10:2021"

    def test_owasp_category_unknown_returns_none(self):
        assert get_owasp_2021_category_for_cwe("CWE-99999") is None

    def test_vuln_class_for_sqli(self):
        assert get_vuln_class_for_cwe("CWE-89") == "SQL Injection"

    def test_vuln_class_for_xss(self):
        assert get_vuln_class_for_cwe("CWE-79") == "Cross-Site Scripting"

    def test_vuln_class_for_ssrf(self):
        assert get_vuln_class_for_cwe("CWE-918") == "SSRF"

    def test_vuln_class_unknown_returns_none(self):
        assert get_vuln_class_for_cwe("CWE-99999") is None

    def test_cwe_to_owasp_2021_non_empty(self):
        assert len(CWE_TO_OWASP_2021) > 10


# ---------------------------------------------------------------------------
# 5. CISAKEVIngestor — load_catalog with fence stripping
# ---------------------------------------------------------------------------

class TestLoadCatalog:
    def test_load_plain_json(self, tmp_path, ingestor):
        f = tmp_path / "kev.json"
        f.write_text(json.dumps(TEST_CATALOG), encoding="utf-8")
        data = ingestor.load_catalog(str(f))
        assert data["catalogVersion"] == "2026.09.02"

    def test_load_with_json_fence(self, tmp_path, ingestor):
        content = "```json\n" + json.dumps(TEST_CATALOG) + "\n```"
        f = tmp_path / "kev.json"
        f.write_text(content, encoding="utf-8")
        data = ingestor.load_catalog(str(f))
        assert data["count"] == 3

    def test_load_with_plain_fence(self, tmp_path, ingestor):
        content = "```\n" + json.dumps(TEST_CATALOG) + "\n```"
        f = tmp_path / "kev.json"
        f.write_text(content, encoding="utf-8")
        data = ingestor.load_catalog(str(f))
        assert "vulnerabilities" in data

    def test_file_not_found_raises(self, ingestor):
        with pytest.raises(FileNotFoundError):
            ingestor.load_catalog("/nonexistent/path/kev.json")


# ---------------------------------------------------------------------------
# 6. CISAKEVIngestor — validate_catalog
# ---------------------------------------------------------------------------

class TestValidateCatalog:
    def test_valid_catalog(self, ingestor):
        ok, reason = ingestor.validate_catalog(TEST_CATALOG)
        assert ok is True
        assert reason == ""

    def test_missing_title_key(self, ingestor):
        bad = {k: v for k, v in TEST_CATALOG.items() if k != "title"}
        ok, reason = ingestor.validate_catalog(bad)
        assert ok is False
        assert "title" in reason

    def test_empty_vulnerabilities(self, ingestor):
        bad = {**TEST_CATALOG, "vulnerabilities": []}
        ok, reason = ingestor.validate_catalog(bad)
        assert ok is False

    def test_non_dict_input(self, ingestor):
        ok, reason = ingestor.validate_catalog([1, 2, 3])
        assert ok is False
        assert "dict" in reason

    def test_vulnerabilities_not_list(self, ingestor):
        bad = {**TEST_CATALOG, "vulnerabilities": "not-a-list"}
        ok, reason = ingestor.validate_catalog(bad)
        assert ok is False

    def test_first_entry_missing_cveID(self, ingestor):
        bad_entries = [{k: v for k, v in TEST_CATALOG["vulnerabilities"][0].items() if k != "cveID"}]
        bad_entries += TEST_CATALOG["vulnerabilities"][1:]
        bad = {**TEST_CATALOG, "vulnerabilities": bad_entries}
        ok, reason = ingestor.validate_catalog(bad)
        assert ok is False
        assert "cveID" in reason


# ---------------------------------------------------------------------------
# 7. CISAKEVIngestor — compute_content_hash
# ---------------------------------------------------------------------------

class TestComputeContentHash:
    def test_hash_is_64_chars(self, ingestor):
        h = ingestor.compute_content_hash(TEST_CATALOG)
        assert len(h) == 64

    def test_hash_is_deterministic(self, ingestor):
        h1 = ingestor.compute_content_hash(TEST_CATALOG)
        h2 = ingestor.compute_content_hash(TEST_CATALOG)
        assert h1 == h2

    def test_hash_differs_on_change(self, ingestor):
        modified = {**TEST_CATALOG, "catalogVersion": "MODIFIED"}
        h1 = ingestor.compute_content_hash(TEST_CATALOG)
        h2 = ingestor.compute_content_hash(modified)
        assert h1 != h2


# ---------------------------------------------------------------------------
# 8. CISAKEVIngestor — _normalize_record
# ---------------------------------------------------------------------------

class TestNormalizeRecord:
    def test_log4j_record(self):
        entry = TEST_CATALOG["vulnerabilities"][0]
        rec = CISAKEVIngestor._normalize_record(entry)
        assert rec["cve_id"] == "CVE-2021-44228"
        assert rec["canonical_id"] == "CISA_KEV:CVE-2021-44228"
        assert rec["provider"] == "CISA_KEV"
        assert rec["vendor"] == "Apache"
        assert rec["product"] == "Log4j"
        assert rec["known_ransomware_use"] == "Known"
        assert "CWE-917" in rec["cwes"]
        assert "CWE-400" in rec["cwes"]

    def test_source_url_extracted_from_notes(self):
        entry = TEST_CATALOG["vulnerabilities"][0]
        rec = CISAKEVIngestor._normalize_record(entry)
        assert rec["source_url"] and rec["source_url"].startswith("https://")

    def test_empty_notes_gives_no_source_url(self):
        entry = TEST_CATALOG["vulnerabilities"][2]
        rec = CISAKEVIngestor._normalize_record(entry)
        assert rec["source_url"] is None

    def test_cwe_normalization_in_record(self):
        entry = {**TEST_CATALOG["vulnerabilities"][0], "cwes": ["cwe-79", "CWE:89"]}
        rec = CISAKEVIngestor._normalize_record(entry)
        assert "CWE-79" in rec["cwes"]
        assert "CWE-89" in rec["cwes"]

    def test_date_parsing(self):
        entry = TEST_CATALOG["vulnerabilities"][0]
        rec = CISAKEVIngestor._normalize_record(entry)
        assert rec["date_added"] is not None
        assert rec["date_added"].year == 2021

    def test_confidence_is_high(self):
        rec = CISAKEVIngestor._normalize_record(TEST_CATALOG["vulnerabilities"][0])
        assert rec["confidence"] >= 0.9


# ---------------------------------------------------------------------------
# 9. CISAKEVIngestor — full ingest with TEST_CATALOG
# ---------------------------------------------------------------------------

class TestIngest:
    def test_ingest_creates_advisories(self, db, ingestor):
        sync_run = ingestor.ingest(db=db, catalog_data=TEST_CATALOG)
        assert sync_run.status == "COMPLETED"
        count = db.query(SecurityAdvisory).count()
        assert count == 3

    def test_ingest_creates_knowledge_source(self, db, ingestor):
        ingestor.ingest(db=db, catalog_data=TEST_CATALOG)
        ks = db.query(KnowledgeSource).filter_by(source_type="CISA_KEV").first()
        assert ks is not None
        assert ks.name == "CISA Known Exploited Vulnerabilities Catalog"

    def test_ingest_creates_sync_run(self, db, ingestor):
        sync_run = ingestor.ingest(db=db, catalog_data=TEST_CATALOG)
        assert sync_run.id is not None
        assert sync_run.records_seen == 3

    def test_ingest_counters_correct(self, db, ingestor):
        sync_run = ingestor.ingest(db=db, catalog_data=TEST_CATALOG)
        assert sync_run.records_created == 3
        assert sync_run.records_updated == 0
        assert sync_run.records_failed == 0

    def test_ingest_with_limit(self, db, ingestor):
        sync_run = ingestor.ingest(db=db, catalog_data=TEST_CATALOG, limit=2)
        assert db.query(SecurityAdvisory).count() == 2

    def test_ingest_dry_run_no_advisories(self, db, ingestor):
        sync_run = ingestor.ingest(db=db, catalog_data=TEST_CATALOG, dry_run=True)
        assert sync_run.status == "COMPLETED"
        assert db.query(SecurityAdvisory).count() == 0

    def test_advisory_cve_id_set(self, db, ingestor):
        ingestor.ingest(db=db, catalog_data=TEST_CATALOG)
        adv = db.query(SecurityAdvisory).filter_by(cve_id="CVE-2021-44228").first()
        assert adv is not None

    def test_advisory_canonical_id_format(self, db, ingestor):
        ingestor.ingest(db=db, catalog_data=TEST_CATALOG)
        adv = db.query(SecurityAdvisory).filter_by(cve_id="CVE-2021-44228").first()
        assert adv.canonical_id == "CISA_KEV:CVE-2021-44228"

    def test_advisory_vendor_product(self, db, ingestor):
        ingestor.ingest(db=db, catalog_data=TEST_CATALOG)
        adv = db.query(SecurityAdvisory).filter_by(cve_id="CVE-2021-44228").first()
        assert adv.vendor == "Apache"
        assert adv.product == "Log4j"

    def test_advisory_ransomware_flag(self, db, ingestor):
        ingestor.ingest(db=db, catalog_data=TEST_CATALOG)
        adv = db.query(SecurityAdvisory).filter_by(cve_id="CVE-2021-44228").first()
        assert adv.known_ransomware_use == "Known"


# ---------------------------------------------------------------------------
# 10. Idempotency — double ingest
# ---------------------------------------------------------------------------

class TestIdempotency:
    def test_double_ingest_does_not_duplicate_advisories(self, db, ingestor):
        ingestor.ingest(db=db, catalog_data=TEST_CATALOG)
        ingestor.ingest(db=db, catalog_data=TEST_CATALOG)
        count = db.query(SecurityAdvisory).count()
        assert count == 3

    def test_double_ingest_second_run_is_update(self, db, ingestor):
        ingestor.ingest(db=db, catalog_data=TEST_CATALOG)
        sync_run2 = ingestor.ingest(db=db, catalog_data=TEST_CATALOG)
        assert sync_run2.records_created == 0
        assert sync_run2.records_updated == 3

    def test_double_ingest_knowledge_source_still_one(self, db, ingestor):
        ingestor.ingest(db=db, catalog_data=TEST_CATALOG)
        ingestor.ingest(db=db, catalog_data=TEST_CATALOG)
        ks_count = db.query(KnowledgeSource).filter_by(source_type="CISA_KEV").count()
        assert ks_count == 1


# ---------------------------------------------------------------------------
# 11. KnowledgeSource and KnowledgeSyncRun creation
# ---------------------------------------------------------------------------

class TestKnowledgeSourceAndSyncRun:
    def test_knowledge_source_version_set(self, db, ingestor):
        ingestor.ingest(db=db, catalog_data=TEST_CATALOG)
        ks = db.query(KnowledgeSource).filter_by(source_type="CISA_KEV").first()
        assert ks.version == "2026.09.02"

    def test_knowledge_source_record_count(self, db, ingestor):
        ingestor.ingest(db=db, catalog_data=TEST_CATALOG)
        ks = db.query(KnowledgeSource).filter_by(source_type="CISA_KEV").first()
        assert ks.record_count == 3

    def test_knowledge_source_content_hash_set(self, db, ingestor):
        ingestor.ingest(db=db, catalog_data=TEST_CATALOG)
        ks = db.query(KnowledgeSource).filter_by(source_type="CISA_KEV").first()
        assert ks.content_hash and len(ks.content_hash) == 64

    def test_sync_run_completed_at_set(self, db, ingestor):
        sync_run = ingestor.ingest(db=db, catalog_data=TEST_CATALOG)
        assert sync_run.completed_at is not None

    def test_sync_run_linked_to_source(self, db, ingestor):
        sync_run = ingestor.ingest(db=db, catalog_data=TEST_CATALOG)
        ks = db.query(KnowledgeSource).filter_by(source_type="CISA_KEV").first()
        assert sync_run.source_id == ks.id

    def test_sync_run_content_hash_matches_source(self, db, ingestor):
        sync_run = ingestor.ingest(db=db, catalog_data=TEST_CATALOG)
        ks = db.query(KnowledgeSource).filter_by(source_type="CISA_KEV").first()
        assert sync_run.content_hash == ks.content_hash


# ---------------------------------------------------------------------------
# 12. CWE and OWASP association linking
# ---------------------------------------------------------------------------

class TestCweOwaspAssociations:
    def test_cwe_entries_created(self, db, ingestor):
        ingestor.ingest(db=db, catalog_data=TEST_CATALOG)
        # CWE-917, CWE-400, CWE-94, CWE-287 expected
        cwe_count = db.query(CWEEntry).count()
        assert cwe_count >= 3

    def test_owasp_categories_seeded(self, db, ingestor):
        ingestor.ingest(db=db, catalog_data=TEST_CATALOG)
        count = db.query(OWASPCategory).filter_by(taxonomy_version="2021").count()
        assert count == 10

    def test_advisory_linked_to_cwe(self, db, ingestor):
        ingestor.ingest(db=db, catalog_data=TEST_CATALOG)
        adv = db.query(SecurityAdvisory).filter_by(cve_id="CVE-2021-44228").first()
        cwe_ids = [c.cwe_id for c in adv.cwes]
        assert "CWE-917" in cwe_ids
        assert "CWE-400" in cwe_ids

    def test_advisory_linked_to_owasp(self, db, ingestor):
        ingestor.ingest(db=db, catalog_data=TEST_CATALOG)
        adv = db.query(SecurityAdvisory).filter_by(cve_id="CVE-2021-44228").first()
        # CWE-917 -> A03:2021 (Injection)
        owasp_ids = [o.category_id for o in adv.owasp_categories]
        assert len(owasp_ids) > 0

    def test_vulnerability_reference_created(self, db, ingestor):
        ingestor.ingest(db=db, catalog_data=TEST_CATALOG)
        adv = db.query(SecurityAdvisory).filter_by(cve_id="CVE-2021-44228").first()
        refs = db.query(VulnerabilityReference).filter_by(advisory_id=adv.id).all()
        assert len(refs) >= 1
        assert refs[0].reference_type == "CVE"
        assert refs[0].reference_value == "CVE-2021-44228"

    def test_cwe_name_populated(self, db, ingestor):
        ingestor.ingest(db=db, catalog_data=TEST_CATALOG)
        cwe = db.query(CWEEntry).filter_by(cwe_id="CWE-287").first()
        assert cwe is not None
        assert "Authentication" in cwe.name


# ---------------------------------------------------------------------------
# 13. ProviderHealthReport stubs return NOT_IMPLEMENTED
# ---------------------------------------------------------------------------

class TestProviderStubs:
    def test_nvd_provider_health(self):
        report = NVDProvider().health()
        assert report.status == ProviderStatus.NOT_IMPLEMENTED
        assert report.provider == "NVD"

    def test_osv_provider_health(self):
        report = OSVProvider().health()
        assert report.status == ProviderStatus.NOT_IMPLEMENTED
        assert report.provider == "OSV"

    def test_github_advisory_provider_health(self):
        report = GitHubAdvisoryProvider().health()
        assert report.status == ProviderStatus.NOT_IMPLEMENTED
        assert report.provider == "GHSA"

    def test_owasp_provider_health(self):
        report = OWASPProvider().health()
        assert report.status == ProviderStatus.NOT_IMPLEMENTED
        assert report.provider == "OWASP"

    def test_cwe_provider_health(self):
        report = CWEProvider().health()
        assert report.status == ProviderStatus.NOT_IMPLEMENTED
        assert report.provider == "CWE"

    def test_provider_health_report_is_dataclass(self):
        report = NVDProvider().health()
        assert isinstance(report, ProviderHealthReport)
        assert report.checked_at is not None

    def test_nvd_fetch_raises_not_implemented(self):
        with pytest.raises(NotImplementedError):
            NVDProvider().fetch()

    def test_osv_validate_raises_not_implemented(self):
        with pytest.raises(NotImplementedError):
            OSVProvider().validate(None)


# ---------------------------------------------------------------------------
# 14. Correlation service queries
# ---------------------------------------------------------------------------

class TestCorrelationService:
    def _ingest(self, db, ingestor):
        ingestor.ingest(db=db, catalog_data=TEST_CATALOG)

    def test_get_advisories_for_technology_apache(self, db, ingestor):
        self._ingest(db, ingestor)
        results = SecurityKnowledgeCorrelationService.get_advisories_for_technology(
            db, "Apache", limit=10
        )
        assert len(results) >= 1
        assert any(a.vendor == "Apache" for a in results)

    def test_get_advisories_for_technology_log4j(self, db, ingestor):
        self._ingest(db, ingestor)
        results = SecurityKnowledgeCorrelationService.get_advisories_for_technology(
            db, "Log4j", limit=10
        )
        assert len(results) >= 1

    def test_get_advisories_for_technology_empty_name(self, db, ingestor):
        self._ingest(db, ingestor)
        results = SecurityKnowledgeCorrelationService.get_advisories_for_technology(
            db, "", limit=10
        )
        assert results == []

    def test_get_advisories_for_vendor_product(self, db, ingestor):
        self._ingest(db, ingestor)
        results = SecurityKnowledgeCorrelationService.get_advisories_for_vendor_product(
            db, vendor="VMware", product="Spring", limit=20
        )
        assert len(results) >= 1
        assert results[0].vendor == "VMware"

    def test_get_advisories_for_vendor_only(self, db, ingestor):
        self._ingest(db, ingestor)
        results = SecurityKnowledgeCorrelationService.get_advisories_for_vendor_product(
            db, vendor="Zoho", product="", limit=10
        )
        assert len(results) >= 1

    def test_get_historical_context_apache(self, db, ingestor):
        self._ingest(db, ingestor)
        ctx = SecurityKnowledgeCorrelationService.get_historical_context_for_signal(
            db, "Apache", "API_ADDED"
        )
        assert ctx["technology"] == "Apache"
        assert ctx["advisory_count"] >= 1
        assert ctx["ransomware_count"] >= 1

    def test_get_historical_context_empty_tech(self, db, ingestor):
        self._ingest(db, ingestor)
        ctx = SecurityKnowledgeCorrelationService.get_historical_context_for_signal(
            db, "", "NONE"
        )
        assert ctx["advisory_count"] == 0

    def test_get_historical_context_unknown_tech(self, db, ingestor):
        self._ingest(db, ingestor)
        ctx = SecurityKnowledgeCorrelationService.get_historical_context_for_signal(
            db, "ThisTechDoesNotExist_XYZ", "ADDED"
        )
        assert ctx["advisory_count"] == 0

    def test_compute_weakness_fingerprint_no_assets(self, db, ingestor):
        self._ingest(db, ingestor)
        result = SecurityKnowledgeCorrelationService.compute_weakness_fingerprint_with_advisories(
            db, company_id=999
        )
        assert result["company_id"] == 999
        assert result["total_advisories"] == 0


# ---------------------------------------------------------------------------
# 14b. Vulnerability Class, Research Relevance, and Bounty Intelligence
# ---------------------------------------------------------------------------

class TestVulnerabilityClassAndBountyIntelligence:
    def test_resolve_vulnerability_class_from_cwes(self, db):
        adv = SecurityAdvisory(
            canonical_id="CISA-KEV:CVE-2026-0001",
            provider="CISA_KEV",
            provider_record_id="CVE-2026-0001",
            cve_id="CVE-2026-0001",
            title="Generic Memory Corruption",
            summary="A flaw occurs in buffer handling",
        )
        cwe = CWEEntry(cwe_id="CWE-119", name="Buffer Overflow")
        adv.cwes.append(cwe)
        db.add_all([cwe, adv])
        db.flush()

        v_class = resolve_vulnerability_class(adv)
        assert v_class == "Buffer Overflow"

    def test_resolve_vulnerability_class_from_title_keywords(self):
        adv1 = SecurityAdvisory(
            canonical_id="CISA-KEV:CVE-2026-85046",
            provider="CISA_KEV",
            provider_record_id="CVE-2026-85046",
            title="Google Chromium V8 Type Confusion Vulnerability",
        )
        assert resolve_vulnerability_class(adv1) == "Type Confusion"

        adv2 = SecurityAdvisory(
            canonical_id="CISA-KEV:CVE-2026-0002",
            provider="CISA_KEV",
            provider_record_id="CVE-2026-0002",
            title="Linux Kernel Use-After-Free Vulnerability",
        )
        assert resolve_vulnerability_class(adv2) == "Use-After-Free"

    def test_research_relevance_structure_and_truth_grounding(self, db):
        adv = SecurityAdvisory(
            canonical_id="CISA-KEV:CVE-2026-85046",
            provider="CISA_KEV",
            provider_record_id="CVE-2026-85046",
            title="Google Chromium V8 Type Confusion Vulnerability",
            vendor="Google",
            product="Chromium V8",
        )
        db.add(adv)
        db.flush()

        v_class = resolve_vulnerability_class(adv)
        rel = _compute_research_relevance(adv, v_class, db)
        assert rel["vulnerability_class"] == "Type Confusion"
        assert rel["truth_classification"] == "CONTEXT_ONLY"
        assert "not establish that a monitored asset is vulnerable" in rel["grounding_disclaimer"]
        assert rel["is_actively_exploited"] is True

    def test_bounty_intelligence_unavailable_when_no_records(self, db):
        adv = SecurityAdvisory(
            canonical_id="CISA-KEV:CVE-2026-85046",
            provider="CISA_KEV",
            provider_record_id="CVE-2026-85046",
            cve_id="CVE-2026-85046",
            title="Google Chromium V8 Type Confusion Vulnerability",
            vendor="Google",
            product="Chromium V8",
        )
        db.add(adv)
        db.commit()

        res = get_advisory_bounty_intelligence(adv.id, db)
        assert res["status"] == "unavailable"
        assert res["records"] == []
        assert res["verified_count"] == 0
        assert res["range"] is None
        assert res["median"] is None
        assert res["average"] is None
        assert "No verified public award data available" in res["message"]

    def test_bounty_intelligence_available_with_verified_records(self, db):
        adv = SecurityAdvisory(
            canonical_id="CISA-KEV:CVE-2026-99999",
            provider="CISA_KEV",
            provider_record_id="CVE-2026-99999",
            cve_id="CVE-2026-99999",
            title="Type Confusion in Engine",
            vendor="Google",
            product="V8",
        )
        db.add(adv)
        db.flush()

        b1 = BountyEvidence(
            vulnerability_class="Type Confusion",
            source="Google VRP",
            source_type="PUBLIC_DISCLOSURE",
            program_name="Chrome Vulnerability Reward Program",
            award_amount=15000.0,
            currency="USD",
            source_url="https://bughunters.google.com/rules",
        )
        b2 = BountyEvidence(
            vulnerability_class="Type Confusion",
            source="HackerOne Public",
            source_type="PUBLIC_DISCLOSURE",
            program_name="Internet Bug Bounty",
            award_amount=5000.0,
            currency="USD",
            source_url="https://hackerone.com/ibb",
        )
        db.add_all([b1, b2])
        db.commit()

        res = get_advisory_bounty_intelligence(adv.id, db)
        assert res["status"] == "available"
        assert res["verified_count"] == 2
        assert res["range"]["min"] == 5000.0
        assert res["range"]["max"] == 15000.0
        assert res["median"] == 10000.0
        assert res["average"] == 10000.0
        assert len(res["records"]) == 2


# ---------------------------------------------------------------------------
# 15. Integration tests (require real catalog file)
# ---------------------------------------------------------------------------

@pytest.mark.integration
@pytest.mark.skipif(not REAL_CATALOG_EXISTS, reason="Real CISA KEV catalog not found")
class TestIntegrationRealCatalog:
    def test_real_catalog_loads_successfully(self, tmp_path):
        ingestor = CISAKEVIngestor()
        data = ingestor.load_catalog(REAL_CATALOG_PATH)
        assert "vulnerabilities" in data
        assert len(data["vulnerabilities"]) > 100

    def test_real_catalog_ingest_limit_5(self, db):
        ingestor = CISAKEVIngestor()
        sync_run = ingestor.ingest(db=db, catalog_path=REAL_CATALOG_PATH, limit=5)
        assert sync_run.status in ("COMPLETED", "PARTIAL")
        assert sync_run.records_seen == 5
        count = db.query(SecurityAdvisory).count()
        assert count == 5
