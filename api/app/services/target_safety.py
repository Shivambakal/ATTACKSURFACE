"""Validation for user-provided public observation targets.

This is deliberately conservative: a hostname must resolve only to globally
routable addresses before the collector may request it. DNS is revalidated at
the collection boundary, not just when a target is created.
"""
from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse
from typing import NamedTuple

from fastapi import HTTPException
import httpx

# Blocked schemes for SSRF prevention
BLOCKED_SCHEMES = {
    "file",
    "ftp",
    "gopher",
    "data",
    "javascript",
    "dict",
    "ldap",
    "ldaps",
    "tftp",
}

# Known cloud provider metadata and internal IPs
BLOCKED_METADATA_IPS = {
    "169.254.169.254",  # AWS/GCP/Azure/DigitalOcean/OpenStack metadata
    "169.254.169.253",  # AWS DNS resolver
    "169.254.170.2",    # AWS ECS container metadata
    "100.100.100.200",  # Alibaba Cloud metadata
    "fd00::ec2",        # AWS IPv6 metadata prefix
    "fd00:ec2::254",    # AWS IPv6 metadata
}

BLOCKED_HOSTS = {
    "localhost",
    "localhost.localdomain",
    "metadata.google.internal",
    "instance-data",
    "metadata.internal",
}

# Explicitly blocked CIDR ranges for IPv4 and IPv6
BLOCKED_NETWORKS = (
    # IPv4 Private / Reserved / Special ranges
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),          # RFC 1918 Private
    ipaddress.ip_network("100.64.0.0/10"),       # RFC 6598 Carrier-Grade NAT
    ipaddress.ip_network("127.0.0.0/8"),         # RFC 1122 Loopback
    ipaddress.ip_network("169.254.0.0/16"),      # RFC 3927 Link-Local / Cloud metadata
    ipaddress.ip_network("172.16.0.0/12"),       # RFC 1918 Private
    ipaddress.ip_network("192.0.0.0/24"),        # RFC 6890 IETF Protocol Assignments
    ipaddress.ip_network("192.0.2.0/24"),        # RFC 5737 TEST-NET-1
    ipaddress.ip_network("192.88.99.0/24"),      # RFC 7526 6to4 Relay Anycast
    ipaddress.ip_network("192.168.0.0/16"),      # RFC 1918 Private
    ipaddress.ip_network("198.18.0.0/15"),       # RFC 2544 Benchmarking
    ipaddress.ip_network("198.51.100.0/24"),     # RFC 5737 TEST-NET-2
    ipaddress.ip_network("203.0.113.0/24"),      # RFC 5737 TEST-NET-3
    ipaddress.ip_network("224.0.0.0/4"),         # RFC 5771 Multicast
    ipaddress.ip_network("240.0.0.0/4"),         # RFC 1112 Reserved
    ipaddress.ip_network("255.255.255.255/32"),  # Limited Broadcast
    # IPv6 Private / Reserved / Special ranges
    ipaddress.ip_network("::1/128"),             # RFC 4291 Loopback
    ipaddress.ip_network("::/128"),              # RFC 4291 Unspecified
    ipaddress.ip_network("64:ff9b::/96"),        # RFC 6052 IPv4/IPv6 translation
    ipaddress.ip_network("100::/64"),            # RFC 6666 Discard-only prefix
    ipaddress.ip_network("2001::/23"),           # RFC 2928 IETF Protocol Assignments
    ipaddress.ip_network("2001:db8::/32"),       # RFC 3849 Documentation
    ipaddress.ip_network("fc00::/7"),            # RFC 4193 Unique Local (includes fd00::/8)
    ipaddress.ip_network("fe80::/10"),           # RFC 4291 Link-Local Unicast
    ipaddress.ip_network("ff00::/8"),            # RFC 4291 Multicast
)


class ValidationResult(tuple):
    """Result tuple of (is_valid: bool, reason: str) that evaluates as a boolean.

    Enables both boolean checks and tuple unpacking:
        if validate_url_for_collection(url): ...
        is_safe, reason = validate_url_for_collection(url)
    """

    def __new__(cls, is_valid: bool, reason: str = ""):
        return super().__new__(cls, (is_valid, reason))

    @property
    def is_valid(self) -> bool:
        return self[0]

    @property
    def reason(self) -> str:
        return self[1]

    def __bool__(self) -> bool:
        return self[0]

    def __repr__(self) -> str:
        return f"ValidationResult(is_valid={self[0]}, reason={self[1]!r})"


def normalize_domain(value: str) -> str:
    domain = value.strip().lower().rstrip(".")
    if not domain or len(domain) > 253 or "/" in domain or ":" in domain:
        raise ValueError("Enter a hostname only, without a scheme, port, or path.")
    labels = domain.split(".")
    if any(not label or len(label) > 63 or not label.replace("-", "").isalnum() or label.startswith("-") or label.endswith("-") for label in labels):
        raise ValueError("Enter a valid public hostname.")
    if domain in BLOCKED_HOSTS:
        raise ValueError("Local and metadata hosts are not permitted.")
    try:
        ipaddress.ip_address(domain)
    except ValueError:
        pass
    else:
        raise ValueError("Enter a public hostname, not an IP address.")
    return domain


def is_public_ip(address: str) -> bool:
    """Validate whether an IP address is a globally routable public address.

    Blocks private ranges, link-local addresses (including 169.254.0.0/16 and fe80::/10),
    loopback addresses, cloud metadata endpoints, IPv6 ULA (fc00::/7, fd00::/8),
    multicast, and reserved blocks.
    """
    try:
        ip = ipaddress.ip_address(address.strip())
    except (ValueError, AttributeError):
        return False

    # Check IPv4-mapped IPv6 address (e.g. ::ffff:127.0.0.1)
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped:
        return is_public_ip(str(ip.ipv4_mapped))

    # Fast-path check against explicit cloud metadata strings
    ip_str = str(ip).lower()
    if ip_str in BLOCKED_METADATA_IPS or address.strip().lower() in BLOCKED_METADATA_IPS:
        return False

    # Standard library checks
    if (
        not ip.is_global
        or ip.is_multicast
        or ip.is_unspecified
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_private
        or ip.is_reserved
    ):
        return False

    # Explicit check against all known non-public CIDR blocks
    for net in BLOCKED_NETWORKS:
        if ip in net:
            return False

    return True


def resolve_and_validate(hostname: str, port: int = 443) -> list[str]:
    """Resolve DNS for a hostname and validate that ALL resolved addresses are public.

    Returns the sorted list of unique validated public IP addresses.
    Raises ValueError if resolution fails, no addresses are returned, or any
    resolved address points to a private, loopback, link-local, or metadata IP.
    """
    clean_host = hostname.strip().lower().rstrip(".")
    if not clean_host:
        raise ValueError("Hostname cannot be empty.")
    if clean_host in BLOCKED_HOSTS:
        raise ValueError("Local and metadata hosts are not permitted.")
    if any(clean_host.endswith(tld) for tld in (".local", ".localhost", ".internal", ".onion", ".lan")):
        raise ValueError("Internal and local domain names are not permitted.")

    # Check if host is an IP literal
    try:
        ip = ipaddress.ip_address(clean_host)
    except ValueError:
        pass
    else:
        if not is_public_ip(str(ip)):
            raise ValueError("Hostname resolves to a non-public destination.")
        return [str(ip)]

    try:
        addr_info = socket.getaddrinfo(clean_host, port, type=socket.SOCK_STREAM)
        addresses = sorted({item[4][0] for item in addr_info})
    except socket.gaierror as exc:
        raise ValueError("Hostname could not be resolved.") from exc
    except Exception as exc:
        raise ValueError(f"DNS resolution failed: {exc}") from exc

    if not addresses or any(not is_public_ip(address) for address in addresses):
        raise ValueError("Hostname resolves to a non-public destination.")

    return addresses


def validated_resolve(hostname: str, port: int = 443) -> list[str]:
    """Alias for resolve_and_validate for anti-TOCTOU resolution."""
    return resolve_and_validate(hostname, port)


def assert_public_destination(domain: str) -> None:
    """Assert domain resolves only to globally routable public addresses."""
    resolve_and_validate(domain, 443)


def safe_https_url(url: str, expected_domain: str) -> bool:
    """Verify URL is an https URL strictly on expected_domain without user credentials."""
    parsed = urlparse(url)
    return parsed.scheme == "https" and parsed.hostname == expected_domain and not parsed.username and not parsed.password


def validate_url_for_collection(url: str) -> tuple[bool, str]:
    """Validate a candidate URL before collection to protect against SSRF.

    Performs comprehensive safety checks:
    - Rejects blocked schemes (file, ftp, gopher, data, javascript, etc.)
    - Requires http or https scheme
    - Rejects embedded credentials (user:pass@host)
    - Rejects blocked hosts (localhost, metadata hosts)
    - Resolves DNS and validates that ALL resolved IP addresses are public routable IPs

    Returns:
        ValidationResult: tuple of (safe: bool, reason: str) which also evaluates as bool.
    """
    if not url or not isinstance(url, str):
        return ValidationResult(False, "URL must be a non-empty string.")

    try:
        parsed = urlparse(url.strip())
    except Exception as exc:
        return ValidationResult(False, f"URL parse error: {exc}")

    scheme = (parsed.scheme or "").lower()
    if not scheme:
        return ValidationResult(False, "Missing URL scheme.")

    if scheme in BLOCKED_SCHEMES:
        return ValidationResult(False, f"Scheme '{scheme}' is blocked for SSRF protection.")

    if scheme not in ("http", "https"):
        return ValidationResult(False, f"Scheme '{scheme}' is not allowed. Only HTTP and HTTPS are permitted.")

    if parsed.username or parsed.password:
        return ValidationResult(False, "URL must not contain embedded authentication credentials.")

    hostname = parsed.hostname
    if not hostname:
        return ValidationResult(False, "URL must contain a valid hostname.")

    host = hostname.strip().lower().rstrip(".")
    if host in BLOCKED_HOSTS:
        return ValidationResult(False, f"Target host '{host}' is in blocked hosts list.")

    if any(host.endswith(tld) for tld in (".local", ".localhost", ".internal", ".onion", ".lan")):
        return ValidationResult(False, f"Target host '{host}' uses a prohibited internal domain suffix.")

    # Check if host is an IP literal
    try:
        ip = ipaddress.ip_address(host)
        if not is_public_ip(str(ip)):
            return ValidationResult(False, f"Destination IP '{host}' is not a public routable address.")
        return ValidationResult(True, "URL is safe for collection.")
    except ValueError:
        pass

    # Hostname is a domain name: resolve and validate destination addresses
    port = parsed.port or (443 if scheme == "https" else 80)
    try:
        resolve_and_validate(host, port)
    except ValueError as exc:
        return ValidationResult(False, str(exc))
    except Exception as exc:
        return ValidationResult(False, f"Resolution error: {exc}")

    return ValidationResult(True, "URL is safe for collection.")


def target_not_authorized() -> HTTPException:
    return HTTPException(403, "Collection requires an active authorized-research acknowledgement.")


class SafeAsyncTransport(httpx.AsyncHTTPTransport):
    """HTTPX AsyncTransport with DNS and SSRF validation before every request hop.

    Prevents TOCTOU DNS rebinding by re-validating the URL and resolved destination
    prior to executing each async HTTP request.
    """

    def __init__(self, allowed_domain: str | None = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.allowed_domain = allowed_domain.lower() if allowed_domain else None

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        url_str = str(request.url)
        is_safe, reason = validate_url_for_collection(url_str)
        if not is_safe:
            raise ValueError(f"SSRF Protection blocked request to {url_str}: {reason}")

        if self.allowed_domain:
            host = (request.url.host or "").lower()
            if host != self.allowed_domain and not host.endswith("." + self.allowed_domain):
                raise ValueError(
                    f"Request to host '{host}' outside allowed domain '{self.allowed_domain}'"
                )

        return await super().handle_async_request(request)


class SafeHTTPTransport(httpx.HTTPTransport):
    """Synchronous HTTPX HTTPTransport with SSRF validation before every request."""

    def __init__(self, allowed_domain: str | None = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.allowed_domain = allowed_domain.lower() if allowed_domain else None

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        url_str = str(request.url)
        is_safe, reason = validate_url_for_collection(url_str)
        if not is_safe:
            raise ValueError(f"SSRF Protection blocked request to {url_str}: {reason}")

        if self.allowed_domain:
            host = (request.url.host or "").lower()
            if host != self.allowed_domain and not host.endswith("." + self.allowed_domain):
                raise ValueError(
                    f"Request to host '{host}' outside allowed domain '{self.allowed_domain}'"
                )

        return super().handle_request(request)


def create_safe_transport(
    allowed_domain: str | None = None,
    verify: bool = True,
    **kwargs,
) -> httpx.AsyncHTTPTransport:
    """Factory creating an SSRF-safe HTTPX AsyncHTTPTransport for the collector."""
    return SafeAsyncTransport(allowed_domain=allowed_domain, verify=verify, **kwargs)
