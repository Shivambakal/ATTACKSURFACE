from pathlib import Path


SOURCE = Path(__file__).parents[1] / "app" / "services" / "cve_validation_gate.py"


def test_validation_source_never_uses_caller_confidence_as_authority():
    source = SOURCE.read_text(encoding="utf-8")
    assert "raw_metadata.get(\"confidence\"" not in source
    assert "confidence\", 0) >= 0.9" not in source


def test_validation_source_has_no_synthetic_cvss_or_cwe_defaults():
    source = SOURCE.read_text(encoding="utf-8")
    assert 'cvss_score": 9.2' not in source
    assert 'cvss_score": 7.8' not in source
    assert 'CWE-94: Code Injection / Flaw' not in source


def test_validation_source_does_not_turn_missing_dates_into_current_time():
    source = SOURCE.read_text(encoding="utf-8")
    assert 'published_at": (kev_entry.get("dateAdded")' not in source
    assert 'or now_iso' not in source


def test_research_signals_are_explicitly_not_vulnerabilities():
    source = SOURCE.read_text(encoding="utf-8")
    assert '"is_vulnerability": False' in source
    assert '"status": "REQUIRES_VERIFICATION"' in source
