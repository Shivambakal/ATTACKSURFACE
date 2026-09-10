"""Unit tests for the Cyber Assistant and Attack History Engine."""
from __future__ import annotations

import pytest
from app.services.attack_history_engine import (
    classify_vulnerability_type,
    get_grounded_attack_history,
)

def test_classify_vulnerability_type():
    assert classify_vulnerability_type("APT17 targeted corporate network") == "APT_STATE_SPONSORED"
    assert classify_vulnerability_type("Heap buffer overflow in libwebp") == "RCE_MEMORY_CORRUPTION"
    assert classify_vulnerability_type("OAuth authorization code bypass") == "IDENTITY_OAUTH_ACCESS_BYPASS"
    assert classify_vulnerability_type("SSRF in cloud metadata API") == "CLOUD_METADATA_SSRF"
    assert classify_vulnerability_type("Exploited in the wild as a zero-day") == "ZERO_DAY_ACTIVE_EXPLOIT"

def test_grounded_attack_history_structure(db_session):
    history = get_grounded_attack_history(db_session, company_name="Google", domain="google.com")
    assert "company" in history
    assert "known_historical_milestones" in history
    assert len(history["known_historical_milestones"]) >= 1
    aurora = next((m for m in history["known_historical_milestones"] if "Aurora" in m["title"]), None)
    assert aurora is not None
    assert aurora["year"] == 2009
    assert aurora["cve_id"] == "CVE-2010-0249"
