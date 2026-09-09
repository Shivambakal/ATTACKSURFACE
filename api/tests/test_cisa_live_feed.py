"""Unit and integration tests for CISA Live Feed Service."""
from __future__ import annotations

import pytest
from app.services.cisa_feed_service import CISAFeedService, OFFICIAL_CISA_FEED_URL


def test_ssrf_protection_allows_cisa():
    """Verify that only allowlisted cisa.gov HTTPS hosts are permitted."""
    CISAFeedService.validate_feed_url(OFFICIAL_CISA_FEED_URL)
    CISAFeedService.validate_feed_url("https://cisa.gov/feeds/known_exploited_vulnerabilities.json")


def test_ssrf_protection_blocks_malicious_urls():
    """Verify that SSRF attempts to localhost, private IPs, and external domains are blocked."""
    with pytest.raises(ValueError, match="is not in allowlisted"):
        CISAFeedService.validate_feed_url("https://127.0.0.1/evil.json")

    with pytest.raises(ValueError, match="is not in allowlisted"):
        CISAFeedService.validate_feed_url("https://attacker.com/evil.json")

    with pytest.raises(ValueError, match="Insecure scheme"):
        CISAFeedService.validate_feed_url("http://www.cisa.gov/feed.json")


def test_schema_validation():
    """Verify JSON schema validator enforces standard CISA KEV structure."""
    valid_data = {
        "title": "CISA Known Exploited Vulnerabilities Catalog",
        "catalogVersion": "2026.09.04",
        "dateReleased": "2026-09-04T16:47:03.519700Z",
        "count": 1,
        "vulnerabilities": [
            {
                "cveID": "CVE-2024-38812",
                "vendorProject": "VMware",
                "product": "vCenter Server",
                "vulnerabilityName": "VMware vCenter Heap Overflow",
                "dateAdded": "2024-09-17",
                "shortDescription": "VMware vCenter contains a heap-based buffer overflow.",
                "requiredAction": "Apply mitigations per vendor instructions.",
                "dueDate": "2024-10-08",
                "knownRansomwareCampaignUse": "Known",
                "notes": "https://www.cisa.gov",
                "cwes": ["CWE-122"],
            }
        ],
    }
    is_valid, msg = CISAFeedService.validate_schema(valid_data)
    assert is_valid is True
    assert msg == ""

    # Missing top-level key
    invalid_data = {"catalogVersion": "1.0"}
    is_valid2, msg2 = CISAFeedService.validate_schema(invalid_data)
    assert is_valid2 is False
    assert "Missing required top-level keys" in msg2


def test_delta_detection_unchanged(db_session):
    """Verify that when raw content SHA-256 hash is unchanged, sync short-circuits."""
    service = CISAFeedService(db_session)
    # Perform first sync
    res1 = service.sync_catalog(force=False)
    assert res1["success"] is True

    # Immediate second sync without force must be UNCHANGED
    res2 = service.sync_catalog(force=False)
    assert res2["success"] is True
    assert res2.get("status") == "UNCHANGED"
    assert res2["new"] == 0
    assert res2["changed"] == 0
