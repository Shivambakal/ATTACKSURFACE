"""Tests for Shodan Passive Intelligence Provider."""
import pytest
from app.providers.shodan import ShodanProvider
from app.providers.base import ProviderStatus


def test_shodan_configuration(monkeypatch):
    monkeypatch.setattr("app.providers.shodan.settings.shodan_api_key", "shodan_key_abc")
    prov = ShodanProvider()
    assert prov.is_configured() is True


def test_shodan_domain_normalization():
    prov = ShodanProvider()
    sample_dns = {
        "domain": "example.com",
        "subdomains": ["api", "auth", "dev"],
    }
    records = prov.normalize_domain_data(sample_dns, domain="example.com")
    assert len(records) == 3
    assert records[0].event_type == "ASSET_CANDIDATE"
    assert records[0].metadata["fqdn"] == "api.example.com"
    assert records[0].metadata["authority_level"] == "PASSIVE_DNS_DATASET"


def test_shodan_host_normalization():
    prov = ShodanProvider()
    sample_host = {
        "ip_str": "93.184.216.34",
        "ports": [80, 443],
        "hostnames": ["example.com"],
        "last_update": "2025-05-15T10:00:00Z",
    }
    records = prov.normalize_host_data(sample_host, target="example.com")
    assert len(records) == 1
    rec = records[0]
    assert rec.event_type == "INFRASTRUCTURE_OBSERVATION"
    assert rec.metadata["ports"] == [80, 443]
