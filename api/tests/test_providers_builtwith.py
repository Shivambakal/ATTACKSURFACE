"""Tests for BuiltWith Technographic Provider."""
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
import httpx

from app.providers.builtwith import BuiltWithProvider
from app.providers.base import ProviderStatus


def test_builtwith_configuration(monkeypatch):
    monkeypatch.setattr("app.providers.builtwith.settings.builtwith_api_key", "test_key_123")
    prov = BuiltWithProvider()
    assert prov.is_configured() is True
    assert prov.api_key == "test_key_123"

    monkeypatch.setattr("app.providers.builtwith.settings.builtwith_api_key", None)
    prov2 = BuiltWithProvider()
    assert prov2.is_configured() is False


@pytest.mark.asyncio
async def test_builtwith_health_not_configured(monkeypatch):
    monkeypatch.setattr("app.providers.builtwith.settings.builtwith_api_key", None)
    prov = BuiltWithProvider()
    health = await prov.check_health()
    assert health.status == ProviderStatus.NOT_CONFIGURED


def test_builtwith_normalization_additions_and_removals():
    prov = BuiltWithProvider()
    sample_payload = {
        "results": [
            {
                "lookup": "example.com",
                "additions": [{"tech": "Cloudflare WAF", "category": "Security"}],
                "removals": [{"tech": "Apache", "category": "Web Server"}],
            }
        ]
    }
    records = prov.normalize_payload(sample_payload)
    assert len(records) == 2

    add_rec = [r for r in records if r.event_type == "TECHNOLOGY_ADDED"][0]
    assert "Cloudflare WAF" in add_rec.title
    assert add_rec.metadata["change_direction"] == "ADDED"
    assert add_rec.metadata["evidence_type"] == "TECHNOGRAPHIC_CHANGE"

    rem_rec = [r for r in records if r.event_type == "TECHNOLOGY_REMOVED"][0]
    assert "Apache" in rem_rec.title
    assert rem_rec.metadata["change_direction"] == "REMOVED"


@pytest.mark.asyncio
async def test_builtwith_multi_domain_fetch(monkeypatch):
    monkeypatch.setattr("app.providers.builtwith.settings.builtwith_api_key", "valid_key")
    prov = BuiltWithProvider()

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "results": [
            {"lookup": "a.com", "additions": [{"tech": "React", "category": "JavaScript"}]},
            {"lookup": "b.com", "removals": [{"tech": "jQuery", "category": "JavaScript"}]},
        ]
    }

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    prov._request_with_retry = AsyncMock(return_value=mock_resp)

    records = await prov.fetch(domains=["a.com", "b.com"], since=datetime(2025, 1, 1, tzinfo=timezone.utc))
    assert len(records) == 2
