import socket
import pytest
from app.services.target_safety import (
    is_public_ip,
    normalize_domain,
    assert_public_destination,
    safe_https_url,
    validate_url_for_collection,
    resolve_and_validate,
    validated_resolve,
    create_safe_transport,
    BLOCKED_SCHEMES,
    BLOCKED_METADATA_IPS,
    BLOCKED_HOSTS,
)

@pytest.mark.parametrize("value", ["example.com", "api.example.co.uk", "EXAMPLE.COM."])
def test_normalize_public_hostname(value):
    assert normalize_domain(value).endswith("com") or normalize_domain(value).endswith("uk")

@pytest.mark.parametrize("value", ["localhost", "http://example.com", "example.com:443", "example..com", "169.254.169.254"])
def test_rejects_unsafe_hostname_inputs(value):
    with pytest.raises(ValueError): normalize_domain(value)

@pytest.mark.parametrize("address", [
    "127.0.0.1",
    "10.0.0.1",
    "192.168.1.10",
    "169.254.169.254",
    "169.254.169.253",
    "169.254.1.1",
    "::1",
    "fe80::1",
    "fc00::1",
    "fd00::ec2",
    "fd00:ec2::254",
    "::ffff:127.0.0.1",
    "::ffff:169.254.169.254",
])
def test_non_public_addresses_are_rejected(address):
    assert not is_public_ip(address)

@pytest.mark.parametrize("address", ["93.184.216.34", "1.1.1.1", "8.8.8.8", "2606:2800:220:1:248:1893:25c8:1946"])
def test_public_addresses_are_accepted(address):
    assert is_public_ip(address)

def test_dns_rejects_mixed_private_resolution(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", lambda *args, **kwargs: [(None, None, None, None, ("93.184.216.34", 443)), (None, None, None, None, ("127.0.0.1", 443))])
    with pytest.raises(ValueError, match="non-public"):
        assert_public_destination("example.com")

def test_only_allows_same_host_https_without_credentials():
    assert safe_https_url("https://example.com/docs", "example.com")
    assert not safe_https_url("http://example.com", "example.com")
    assert not safe_https_url("https://sub.example.com", "example.com")
    assert not safe_https_url("https://user:pass@example.com", "example.com")

def test_resolve_and_validate_success(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", lambda *args, **kwargs: [(None, None, None, None, ("93.184.216.34", 443))])
    ips = resolve_and_validate("example.com", 443)
    assert "93.184.216.34" in ips
    assert validated_resolve("example.com", 443) == ips

def test_resolve_and_validate_rejects_private_ip(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", lambda *args, **kwargs: [(None, None, None, None, ("192.168.1.1", 443))])
    with pytest.raises(ValueError, match="non-public"):
        resolve_and_validate("internal.corp", 443)

def test_resolve_and_validate_rejects_metadata_hosts():
    with pytest.raises(ValueError, match="Local and metadata"):
        resolve_and_validate("localhost")
    with pytest.raises(ValueError, match="Internal and local"):
        resolve_and_validate("server.local")

@pytest.mark.parametrize("scheme", ["file", "ftp", "gopher", "data", "javascript"])
def test_validate_url_rejects_blocked_schemes(scheme):
    safe, reason = validate_url_for_collection(f"{scheme}://example.com/data")
    assert not safe
    assert "blocked" in reason.lower()
    # Also verify it acts as falsy in boolean context
    assert not validate_url_for_collection(f"{scheme}://example.com/data")

def test_validate_url_rejects_credentials():
    safe, reason = validate_url_for_collection("https://user:secret@example.com")
    assert not safe
    assert "credentials" in reason.lower()

def test_validate_url_rejects_metadata_ip():
    safe, reason = validate_url_for_collection("http://169.254.169.254/latest/meta-data")
    assert not safe
    assert "not a public routable address" in reason.lower()

def test_validate_url_accepts_public_destination(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", lambda *args, **kwargs: [(None, None, None, None, ("93.184.216.34", 443))])
    safe, reason = validate_url_for_collection("https://example.com/security")
    assert safe
    assert "safe" in reason.lower()
    assert bool(validate_url_for_collection("https://example.com/security")) is True

def test_create_safe_transport():
    transport = create_safe_transport(allowed_domain="example.com")
    assert transport.allowed_domain == "example.com"
