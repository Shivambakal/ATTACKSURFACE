"""Tests for Domainee and Subdomains Finder Providers."""
import pytest
from app.providers.domainee import DomaineeProvider
from app.providers.subdomains_finder import SubdomainsFinderProvider, SUBDOMAINS_FINDER_FIXTURE
from app.providers.base import ProviderStatus


def test_domainee_dns_normalization():
    prov = DomaineeProvider()
    sample = {
        "records": [
            {"name": "app.customer.com", "type": "CNAME", "value": "cname.domainee.dev"},
        ]
    }
    records = prov.normalize_dns_data(sample, domain="customer.com")
    assert len(records) == 1
    assert records[0].event_type == "DNS_CHANGE"
    assert records[0].metadata["record_type"] == "CNAME"


@pytest.mark.asyncio
async def test_subdomains_finder_unverified_guard(monkeypatch):
    monkeypatch.setattr("app.providers.subdomains_finder.settings.subdomains_finder_api_key", "sample_key")
    prov = SubdomainsFinderProvider()
    health = await prov.check_health()
    # Enforces UNVERIFIED / UNAVAILABLE status at runtime
    assert health.status == ProviderStatus.UNAVAILABLE
    assert "UNVERIFIED" in health.error_summary


def test_subdomains_finder_fixture_normalization():
    prov = SubdomainsFinderProvider()
    records = prov.normalize_payload(SUBDOMAINS_FINDER_FIXTURE, domain="example.com")
    assert len(records) == 3
    assert records[0].event_type == "ASSET_CANDIDATE"
    assert records[0].metadata["authority_level"] == "UNVERIFIED_THIRD_PARTY"
