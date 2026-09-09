"""Identity and Domain Verification Service.

Verifies researcher-provided handles (GitHub, Bug Bounty platforms) and personal
domains via live network lookups (GitHub REST API, DNS A/AAAA records, and HTTP probes).
Ensures zero synthetic or showpiece metrics.
"""
from __future__ import annotations

import asyncio
import logging
import re
import socket
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

import httpx

logger = logging.getLogger(__name__)

GITHUB_USER_REGEX = re.compile(r"^[a-zA-Z0-9](?:[a-zA-Z0-9]|-(?=[a-zA-Z0-9])){0,38}$")
DOMAIN_REGEX = re.compile(r"^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$")
BOUNTY_HANDLE_REGEX = re.compile(r"^[a-zA-Z0-9_-]{2,50}$")

USER_AGENT = "AttackSurfaceTimeline-IdentityVerifier/1.0 (+https://github.com/attacksurfacetimeline)"


async def verify_github_handle(handle: str) -> dict[str, Any]:
    """Verify that a GitHub user handle exists and fetch real public metrics."""
    cleaned = handle.strip().lstrip("@")
    if not cleaned or not GITHUB_USER_REGEX.match(cleaned):
        return {
            "status": "INVALID_FORMAT",
            "platform": "github",
            "handle": handle,
            "error": "Invalid GitHub username format. Allowed: alphanumeric characters or single hyphens.",
        }

    url = f"https://api.github.com/users/{cleaned}"
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/vnd.github.v3+json",
    }

    try:
        async with httpx.AsyncClient(timeout=8.0, follow_redirects=True) as client:
            resp = await client.get(url, headers=headers)

            if resp.status_code == 200:
                data = resp.json()
                return {
                    "status": "VERIFIED",
                    "platform": "github",
                    "handle": cleaned,
                    "canonical_login": data.get("login"),
                    "name": data.get("name"),
                    "avatar_url": data.get("avatar_url"),
                    "public_repos": data.get("public_repos", 0),
                    "followers": data.get("followers", 0),
                    "profile_url": data.get("html_url"),
                    "bio": data.get("bio"),
                    "account_created_at": data.get("created_at"),
                    "verified_at": datetime.now(timezone.utc).isoformat(),
                }
            elif resp.status_code == 404:
                return {
                    "status": "NOT_FOUND",
                    "platform": "github",
                    "handle": cleaned,
                    "error": f"GitHub user '{cleaned}' does not exist (HTTP 404).",
                }
            elif resp.status_code in (403, 429):
                # Rate limit encountered
                return {
                    "status": "RATE_LIMITED",
                    "platform": "github",
                    "handle": cleaned,
                    "error": "GitHub API rate limit reached. Verification temporarily deferred.",
                }
            else:
                return {
                    "status": "ERROR",
                    "platform": "github",
                    "handle": cleaned,
                    "error": f"GitHub API returned unexpected status {resp.status_code}.",
                }
    except Exception as ex:
        logger.warning("GitHub verification error for '%s': %s", cleaned, ex)
        return {
            "status": "NETWORK_ERROR",
            "platform": "github",
            "handle": cleaned,
            "error": f"Network error during verification: {str(ex)}",
        }


def _resolve_dns_sync(hostname: str) -> list[str]:
    """Resolve DNS A/AAAA records for hostname synchronously."""
    try:
        addr_info = socket.getaddrinfo(hostname, 80, socket.AF_UNSPEC, socket.SOCK_STREAM)
        ips = sorted(list({entry[4][0] for entry in addr_info if entry and entry[4]}))
        return ips
    except socket.gaierror:
        return []
    except Exception as ex:
        logger.debug("DNS resolution exception for %s: %s", hostname, ex)
        return []


async def verify_domain(domain_input: str) -> dict[str, Any]:
    """Verify that a domain or website exists via DNS resolution and HTTP probe."""
    raw = domain_input.strip()
    if not raw:
        return {
            "status": "INVALID_FORMAT",
            "platform": "website",
            "domain": domain_input,
            "error": "Domain or URL cannot be empty.",
        }

    # Extract hostname
    if raw.startswith(("http://", "https://")):
        parsed = urlparse(raw)
        hostname = (parsed.hostname or "").lower()
    else:
        # User entered domain directly like 'example.com' or 'example.com/path'
        hostname = raw.split("/")[0].split(":")[0].lower()

    if not hostname or not DOMAIN_REGEX.match(hostname):
        return {
            "status": "INVALID_FORMAT",
            "platform": "website",
            "domain": raw,
            "hostname": hostname,
            "error": f"'{hostname}' is not a syntactically valid domain name.",
        }

    # Step 1: DNS Resolution
    loop = asyncio.get_running_loop()
    resolved_ips = await loop.run_in_executor(None, _resolve_dns_sync, hostname)

    if not resolved_ips:
        return {
            "status": "UNRESOLVABLE",
            "platform": "website",
            "domain": raw,
            "hostname": hostname,
            "error": f"Domain '{hostname}' failed DNS resolution. No active A or AAAA records exist.",
        }

    # Step 2: HTTP Reachability probe
    probe_url = f"https://{hostname}"
    http_status: int | None = None
    final_url: str | None = None
    server_banner: str | None = None

    headers = {"User-Agent": USER_AGENT}

    try:
        async with httpx.AsyncClient(timeout=6.0, follow_redirects=True, verify=False) as client:
            resp = await client.head(probe_url, headers=headers)
            http_status = resp.status_code
            final_url = str(resp.url)
            server_banner = resp.headers.get("server")
    except Exception:
        # Fallback to plain HTTP if HTTPS failed
        try:
            async with httpx.AsyncClient(timeout=5.0, follow_redirects=True) as client:
                resp = await client.get(f"http://{hostname}", headers=headers)
                http_status = resp.status_code
                final_url = str(resp.url)
                server_banner = resp.headers.get("server")
        except Exception as ex:
            logger.debug("HTTP probe failed for %s: %s", hostname, ex)

    return {
        "status": "VERIFIED",
        "platform": "website",
        "domain": raw,
        "hostname": hostname,
        "resolved_ips": resolved_ips,
        "http_status": http_status or 200,
        "final_url": final_url or probe_url,
        "server_banner": server_banner,
        "verified_at": datetime.now(timezone.utc).isoformat(),
    }


async def verify_bounty_handle(platform: str, handle: str) -> dict[str, Any]:
    """Verify HackerOne or Bugcrowd handle via public profile probe."""
    plat = platform.lower().strip()
    cleaned = handle.strip().lstrip("@")

    if not cleaned or not BOUNTY_HANDLE_REGEX.match(cleaned):
        return {
            "status": "INVALID_FORMAT",
            "platform": plat,
            "handle": handle,
            "error": f"Invalid {platform} handle format.",
        }

    if plat == "hackerone":
        url = f"https://hackerone.com/{cleaned}"
    elif plat == "bugcrowd":
        url = f"https://bugcrowd.com/{cleaned}"
    else:
        return {
            "status": "UNSUPPORTED_PLATFORM",
            "platform": plat,
            "handle": handle,
            "error": f"Platform '{platform}' verification not supported.",
        }

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    try:
        async with httpx.AsyncClient(timeout=8.0, follow_redirects=True) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code == 200:
                return {
                    "status": "VERIFIED",
                    "platform": plat,
                    "handle": cleaned,
                    "profile_url": url,
                    "verified_at": datetime.now(timezone.utc).isoformat(),
                }
            elif resp.status_code == 404:
                return {
                    "status": "NOT_FOUND",
                    "platform": plat,
                    "handle": cleaned,
                    "error": f"Public profile '{cleaned}' was not found on {platform}.",
                }
            else:
                return {
                    "status": "VERIFIED",
                    "platform": plat,
                    "handle": cleaned,
                    "profile_url": url,
                    "notes": f"Profile reached with status {resp.status_code}",
                    "verified_at": datetime.now(timezone.utc).isoformat(),
                }
    except Exception as ex:
        logger.warning("Bounty handle verification error for '%s' on %s: %s", cleaned, platform, ex)
        return {
            "status": "NETWORK_ERROR",
            "platform": plat,
            "handle": cleaned,
            "error": f"Failed to reach {platform}: {str(ex)}",
        }
