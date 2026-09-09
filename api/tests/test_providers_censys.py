"""Tests for Censys Platform REST API Provider."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.providers.censys import CensysProvider
from app.providers.base import ProviderStatus


def test_censys_configuration(monkeypatch):
    monkeypatch.setattr("app.providers.censys.settings.censys_api_key", "test_pat")
    monkeypatch.setattr("app.providers.censys.settings.censys_organization_id", "org_123")
    prov = CensysProvider()
    assert prov.is_configured() is True
    headers = prov._headers()
    assert headers["Authorization"] == "Bearer test_pat"
    assert headers["X-Organization-ID"] == "org_123"


def test_censys_host_normalization():
    prov = CensysProvider()
    sample_host = {
        "ip": "1.1.1.1",
        "last_observed_at": "2025-06-01T12:00:00Z",
        "services": [
            {"port": 443, "service_name": "HTTPS"},
            {"port": 80, "service_name": "HTTP"},
        ],
        "autonomous_system": {"asn": 13335, "name": "CLOUDFLARENET"},
    }
    records = prov.normalize_host_result(sample_host, target="cloudflare.com")
    assert len(records) == 1
    rec = records[0]
    assert rec.event_type == "INFRASTRUCTURE_OBSERVATION"
    assert "1.1.1.1" in rec.title
    assert rec.metadata["ports"] == [443, 80]
    assert rec.metadata["authority_level"] == "INTERNET_SCAN_OBSERVATION"


def test_censys_search_hit_normalization():
    prov = CensysProvider()
    hit = {
        "ip": "8.8.8.8",
        "services": [{"port": 53}, {"port": 443}],
    }
    records = prov.normalize_search_hit(hit, target="google.com")
    assert len(records) == 1
    assert records[0].event_type == "ASSET_CANDIDATE"
    assert records[0].metadata["ip"] == "8.8.8.8"
