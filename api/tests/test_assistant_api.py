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


def test_cyber_assistant_privacy_and_grounded_fallback():
    from app.services.attack_history_engine import HISTORIC_COMPANY_CAMPAIGNS
    from app.services.cyber_assistant_service import (
        ASSISTANT_MODEL_ID,
        generate_grounded_fallback_response,
    )

    assert ASSISTANT_MODEL_ID == "AttackSurface-CyberAnalyst-v2"

    grounded = {
        "company_name": "Google LLC",
        "canonical_domain": "google.com",
        "biggest_attack": HISTORIC_COMPANY_CAMPAIGNS["google.com"][0],
        "curated_historical_milestones": HISTORIC_COMPANY_CAMPAIGNS["google.com"],
        "yearly_distribution": {2009: 2, 2017: 1, 2023: 3},
        "attack_type_distribution": {"APT_STATE_SPONSORED": 2, "ZERO_DAY_ACTIVE_EXPLOIT": 4},
        "recent_cve_sample": ["CVE-2023-4863", "CVE-2010-0249"],
    }

    report = generate_grounded_fallback_response("What was the biggest attack on Google?", grounded)
    assert "Operation Aurora" in report
    assert "CVE-2010-0249" in report
    assert "BeyondCorp" in report

    # Strict privacy: absolutely zero vendor/Gemini/503 references in output
    assert "gemini" not in report.lower()
    assert "503" not in report
    assert "generativelanguage" not in report.lower()

