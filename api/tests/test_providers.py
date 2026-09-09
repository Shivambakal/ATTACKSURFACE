"""Unit tests for providers and ProviderManager."""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.config import settings
from app.providers.base import (
    BaseProvider,
    NormalizedRecord,
    ProviderHealth,
    ProviderStatus,
    RateLimiter,
)
from app.providers.cisa_kev import CISAKEVProvider
from app.providers.gemini import GeminiProvider
from app.providers.github import GitHubProvider, _extract_owner_repo
from app.providers.nvd import NVDProvider
from app.providers.nvidia import NvidiaProvider
from app.providers.osv import OSVProvider
from app.services.provider_manager import ProviderManager, get_provider_manager


@pytest.mark.asyncio
async def test_rate_limiter():
    limiter = RateLimiter(max_requests=2, window_seconds=0.1)
    await limiter.acquire()
    await limiter.acquire()
    start = asyncio.get_event_loop().time()
    await limiter.acquire()
    elapsed = asyncio.get_event_loop().time() - start
    assert elapsed >= 0.05


def test_base_provider_caching():
    class DummyProvider(BaseProvider):
        def is_configured(self) -> bool:
            return True

        async def check_health(self) -> ProviderHealth:
            return ProviderHealth(name=self.name, status=ProviderStatus.AVAILABLE)

        async def fetch(self, **kwargs):
            return []

    dummy = DummyProvider("dummy")
    k = dummy._cache_key(a="1", b=2)
    assert dummy._get_cached(k) is None
    dummy._set_cached(k, "cached_val")
    assert dummy._get_cached(k) == "cached_val"


@pytest.mark.asyncio
async def test_base_provider_safe_health_handles_exception():
    class FailingProvider(BaseProvider):
        def is_configured(self) -> bool:
            return True

        async def check_health(self) -> ProviderHealth:
            raise ConnectionError("Network down")

        async def fetch(self, **kwargs):
            return []

    prov = FailingProvider("failing")
    health = await prov.safe_health()
    assert health.status == ProviderStatus.FAILED
    assert "ConnectionError" in (health.error_summary or "")


def test_github_extract_owner_repo():
    assert _extract_owner_repo("owner/repo") == ("owner", "repo")
    assert _extract_owner_repo("owner/repo.git") == ("owner", "repo")
    assert _extract_owner_repo("https://github.com/fastapi/fastapi") == ("fastapi", "fastapi")
    assert _extract_owner_repo("https://github.com/fastapi/fastapi.git") == ("fastapi", "fastapi")
    assert _extract_owner_repo("invalid_string_without_slash") is None


def test_github_provider_headers_never_expose_token():
    with patch.object(settings, "github_token", "super_secret_token_123"):
        prov = GitHubProvider()
        assert prov.is_configured() is True
        headers = prov._get_headers()
        assert headers.get("Authorization") == "Bearer super_secret_token_123"

    with patch.object(settings, "github_token", None):
        prov = GitHubProvider()
        assert prov.is_configured() is False
        headers = prov._get_headers()
        assert "Authorization" not in headers


@pytest.mark.asyncio
async def test_gemini_provider_unconfigured():
    with patch.object(settings, "gemini_api_key", None):
        prov = GeminiProvider()
        assert prov.is_configured() is False
        health = await prov.check_health()
        assert health.status == ProviderStatus.NOT_CONFIGURED
        records = await prov.fetch(content="test content")
        assert records == []


@pytest.mark.asyncio
async def test_gemini_insufficient_evidence():
    with patch.object(settings, "gemini_api_key", "fake_key"):
        prov = GeminiProvider()
        prov._configured_sdk = True
        records = await prov.fetch(content="", evidence_ids=[])
        assert len(records) == 1
        assert records[0].summary == "Insufficient evidence."


@pytest.mark.asyncio
async def test_nvidia_provider_unconfigured():
    with patch.object(settings, "nvidia_api_key", None):
        prov = NvidiaProvider()
        assert prov.is_configured() is False
        health = await prov.check_health()
        assert health.status == ProviderStatus.NOT_CONFIGURED
        records = await prov.fetch(content="test")
        assert records == []


@pytest.mark.asyncio
async def test_nvidia_insufficient_evidence():
    with patch.object(settings, "nvidia_api_key", "fake_key"):
        prov = NvidiaProvider()
        records = await prov.fetch(content="", evidence_ids=[])
        assert len(records) == 1
        assert records[0].summary == "Insufficient evidence."


def test_osv_provider_configured():
    prov = OSVProvider()
    assert prov.is_configured() is True


def test_osv_normalization():
    prov = OSVProvider()
    vuln_dict = {
        "id": "GHSA-1234-5678",
        "summary": "Sample XSS in package",
        "details": "Details of the vulnerability",
        "aliases": ["CVE-2024-9999"],
        "published": "2024-01-15T12:00:00Z",
        "modified": "2024-01-16T12:00:00Z",
        "affected": [{"package": {"name": "sample-pkg", "ecosystem": "npm"}}],
        "references": [{"type": "WEB", "url": "https://example.com/advisory"}],
    }
    rec = prov._normalize_vuln(vuln_dict)
    assert rec.source == "osv"
    assert rec.evidence_reference == "CVE-2024-9999"
    assert "CVE-2024-9999" in rec.title
    assert rec.metadata["ecosystem"] == "npm"
    assert rec.metadata["package"] == "sample-pkg"
    assert rec.published_at is not None
    assert rec.published_at.tzinfo == timezone.utc


def test_cisa_kev_provider_normalization():
    prov = CISAKEVProvider()
    assert prov.is_configured() is True
    item = {
        "cveID": "CVE-2023-1234",
        "vendorProject": "TestVendor",
        "product": "TestProduct",
        "vulnerabilityName": "Test Vulnerability",
        "dateAdded": "2023-05-10",
        "shortDescription": "Test description of exploited vulnerability",
        "requiredAction": "Apply patch",
        "dueDate": "2023-06-01",
        "knownRansomwareCampaignUse": "Known",
        "notes": "https://nvd.nist.gov/vuln/detail/CVE-2023-1234",
    }
    rec = prov._normalize_item(item)
    assert rec.source == "cisa_kev"
    assert rec.evidence_reference == "CVE-2023-1234"
    assert "CVE-2023-1234" in rec.title
    assert rec.published_at is not None
    assert rec.published_at.tzinfo == timezone.utc
    assert rec.metadata["vendor"] == "TestVendor"


def test_nvd_provider_rate_limits():
    with patch.object(settings, "nvd_api_key", None):
        prov = NVDProvider()
        assert prov.is_configured() is False
        assert prov._rate_limiter.max_requests == 5

    with patch.object(settings, "nvd_api_key", "fake_nvd_key"):
        prov = NVDProvider()
        assert prov.is_configured() is True
        assert prov._rate_limiter.max_requests == 50


def test_nvd_normalization():
    prov = NVDProvider()
    raw_item = {
        "cve": {
            "id": "CVE-2021-44228",
            "published": "2021-12-10T10:15:00.000Z",
            "lastModified": "2023-11-07T03:39:27.530Z",
            "vulnStatus": "Analyzed",
            "descriptions": [{"lang": "en", "value": "Log4j RCE vulnerability"}],
            "metrics": {
                "cvssMetricV31": [
                    {
                        "cvssData": {
                            "baseScore": 10.0,
                            "baseSeverity": "CRITICAL",
                            "vectorString": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:H/A:H",
                        }
                    }
                ]
            },
            "weaknesses": [{"description": [{"value": "CWE-502"}]}],
            "references": [{"url": "https://logging.apache.org"}],
        }
    }
    rec = prov._normalize_cve_item(raw_item)
    assert rec.source == "nvd"
    assert rec.evidence_reference == "CVE-2021-44228"
    assert "10.0" in rec.title
    assert rec.published_at is not None
    assert rec.published_at.tzinfo == timezone.utc
    assert rec.metadata["cvss_score"] == 10.0
    assert "CWE-502" in rec.metadata["cwes"]


@pytest.mark.asyncio
async def test_provider_manager_singleton_and_registry():
    mgr1 = get_provider_manager()
    mgr2 = ProviderManager()
    assert mgr1 is mgr2

    providers = mgr1.list_providers()
    for expected in ["github", "gemini", "nvidia", "osv", "cisa_kev", "nvd"]:
        assert expected in providers


@pytest.mark.asyncio
async def test_provider_manager_health_check_all():
    mgr = get_provider_manager()
    results = await mgr.health_check_all()
    assert len(results) >= 6
    names = {h.name for h in results}
    assert "github" in names
    assert "osv" in names
    assert "cisa_kev" in names


@pytest.mark.asyncio
async def test_provider_manager_fetch_graceful_degradation():
    mgr = get_provider_manager()

    mock_failing = MagicMock(spec=BaseProvider)
    mock_failing.name = "mock_failing"
    mock_failing.fetch = AsyncMock(side_effect=RuntimeError("Provider exploded"))

    mock_working = MagicMock(spec=BaseProvider)
    mock_working.name = "mock_working"
    mock_record = NormalizedRecord(
        source="mock_working",
        source_url="https://example.test",
        title="Mock Item",
        summary="Working item",
        event_type="test",
        published_at=datetime.now(timezone.utc),
        observed_at=datetime.now(timezone.utc),
    )
    mock_working.fetch = AsyncMock(return_value=[mock_record])

    mgr.register_provider(mock_failing)
    mgr.register_provider(mock_working)

    records = await mgr.fetch_from_all(
        target="example.com", providers=["mock_failing", "mock_working"]
    )
    assert len(records) == 1
    assert records[0].source == "mock_working"
