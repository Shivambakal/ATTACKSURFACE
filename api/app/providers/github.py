"""GitHub data provider for public repositories, releases, tags, commits, and advisories.

Supports authenticated requests when GITHUB_TOKEN is configured and falls back
gracefully to unauthenticated requests with lower rate limits.
Uses ETag/conditional requests, pagination, and token bucket rate limiting.
Never logs or exposes the Authorization header.
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

import httpx

from ..config import settings
from .base import BaseProvider, NormalizedRecord, ProviderHealth, ProviderStatus, RateLimiter

logger = logging.getLogger(__name__)


def _parse_github_timestamp(val: str | None) -> datetime | None:
    if not val:
        return None
    try:
        dt = datetime.fromisoformat(val.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except (ValueError, TypeError):
        return None


def _extract_owner_repo(repo_str: str) -> tuple[str, str] | None:
    """Extract (owner, repo) from a string like 'owner/repo' or a GitHub URL."""
    s = repo_str.strip()
    if s.startswith("http://") or s.startswith("https://"):
        parsed = urlparse(s)
        if "github.com" in parsed.netloc:
            parts = [p for p in parsed.path.strip("/").split("/") if p]
            if len(parts) >= 2:
                repo_name = parts[1].removesuffix(".git")
                return parts[0], repo_name
        return None

    pattern = r"^([a-zA-Z0-9_\-\.]+)/([a-zA-Z0-9_\-\.]+)$"
    match = re.match(pattern, s)
    if match:
        repo_name = match.group(2).removesuffix(".git")
        return match.group(1), repo_name
    return None


class GitHubProvider(BaseProvider):
    """Provider for fetching GitHub metadata, releases, tags, commits, and advisories."""

    GITHUB_API_BASE = "https://api.github.com"

    def __init__(self, rate_limiter: RateLimiter | None = None):
        # Authenticated: up to 60 req/min; Unauthenticated: conservative 10 req/min
        max_requests = 60 if settings.github_token else 10
        limiter = rate_limiter or RateLimiter(max_requests=max_requests, window_seconds=60.0)
        super().__init__(name="github", rate_limiter=limiter)
        self._etags: dict[str, str] = {}
        self._cached_responses: dict[str, Any] = {}

    def is_configured(self) -> bool:
        """Whether a GitHub API token is configured."""
        return bool(settings.github_token)

    def _get_headers(self, etag: str | None = None) -> dict[str, str]:
        """Construct headers without exposing credentials in logs."""
        headers: dict[str, str] = {
            "Accept": "application/vnd.github+json",
            "User-Agent": settings.collector_user_agent,
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if settings.github_token:
            headers["Authorization"] = f"Bearer {settings.github_token}"
        if etag:
            headers["If-None-Match"] = etag
        return headers

    async def check_health(self) -> ProviderHealth:
        """Safe health check querying GitHub rate_limit endpoint."""
        url = f"{self.GITHUB_API_BASE}/rate_limit"
        headers = self._get_headers()

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, headers=headers)

            if response.status_code == 200:
                data = response.json()
                rate_info = data.get("rate", {})
                remaining = rate_info.get("remaining", 0)
                status = ProviderStatus.AUTHENTICATED if self.is_configured() else ProviderStatus.AVAILABLE
                error_summary = None if remaining > 0 else "GitHub rate limit exceeded."
                recommended_fix = None if remaining > 0 else "Wait for rate limit window reset or configure GITHUB_TOKEN."
                return ProviderHealth(
                    name=self.name,
                    status=status,
                    error_summary=error_summary,
                    recommended_fix=recommended_fix,
                )
            elif response.status_code in (401, 403):
                if self.is_configured():
                    return ProviderHealth(
                        name=self.name,
                        status=ProviderStatus.FAILED,
                        error_summary="Authentication failed: invalid or expired GitHub token.",
                        recommended_fix="Verify the GITHUB_TOKEN in your environment or configuration.",
                    )
                return ProviderHealth(
                    name=self.name,
                    status=ProviderStatus.UNAVAILABLE,
                    error_summary="Unauthenticated GitHub rate limit exhausted.",
                    recommended_fix="Set GITHUB_TOKEN for higher rate limits (5,000 requests/hour).",
                )
            else:
                return ProviderHealth(
                    name=self.name,
                    status=ProviderStatus.FAILED,
                    error_summary=f"GitHub API returned HTTP {response.status_code}.",
                    recommended_fix="Check GitHub service status or network connectivity.",
                )
        except Exception as exc:
            self.logger.warning("GitHub health check failed: %s", type(exc).__name__)
            return ProviderHealth(
                name=self.name,
                status=ProviderStatus.FAILED,
                error_summary=f"{type(exc).__name__}: connectivity failure",
                recommended_fix="Verify outbound internet connectivity to api.github.com.",
            )

    async def _fetch_url_json(
        self, client: httpx.AsyncClient, url: str, params: dict[str, Any] | None = None
    ) -> Any | None:
        """Fetch JSON with ETag conditional caching and retry."""
        cached_etag = self._etags.get(url)
        headers = self._get_headers(etag=cached_etag)

        try:
            resp = await self._request_with_retry(
                client, "GET", url, headers=headers, params=params, max_retries=3
            )
            if resp.status_code == 304 and url in self._cached_responses:
                return self._cached_responses[url]
            if resp.status_code == 200:
                data = resp.json()
                etag = resp.headers.get("etag")
                if etag:
                    self._etags[url] = etag
                    self._cached_responses[url] = data
                return data
            elif resp.status_code in (404, 422):
                self.logger.debug("Resource not found or unprocessable at %s: %s", url, resp.status_code)
                return None
            else:
                self.logger.warning("Unexpected status code %s for %s", resp.status_code, url)
                return None
        except Exception as exc:
            self.logger.warning("Failed to fetch %s: %s", url, type(exc).__name__)
            return None

    async def fetch(self, **kwargs: Any) -> list[NormalizedRecord]:
        """Fetch and normalize GitHub data for a repository, search query, or target domain.

        Supported kwargs:
            repository (str): "owner/repo" or "https://github.com/owner/repo"
            target (str): Target domain or repo identifier
            per_page (int): Items per page (default: 10)
        """
        repo_target: str | None = kwargs.get("repository") or kwargs.get("repo") or kwargs.get("target")
        if not repo_target:
            return []

        parsed = _extract_owner_repo(repo_target)
        per_page = int(kwargs.get("per_page", 10))

        records: list[NormalizedRecord] = []
        observed_at = datetime.now(timezone.utc)

        async with httpx.AsyncClient(timeout=15.0) as client:
            if parsed:
                owner, repo = parsed
                base_repo_url = f"{self.GITHUB_API_BASE}/repos/{owner}/{repo}"

                # 1. Fetch Repository Info
                repo_data = await self._fetch_url_json(client, base_repo_url)
                if repo_data and isinstance(repo_data, dict):
                    repo_url = repo_data.get("html_url", f"https://github.com/{owner}/{repo}")
                    desc = repo_data.get("description") or ""
                    pushed_at = _parse_github_timestamp(repo_data.get("pushed_at"))
                    content_raw = json.dumps(
                        {"name": repo_data.get("full_name"), "description": desc, "default_branch": repo_data.get("default_branch")},
                        sort_keys=True,
                    )
                    records.append(
                        NormalizedRecord(
                            source="github",
                            source_url=repo_url,
                            title=f"Repository: {owner}/{repo}",
                            summary=desc or f"GitHub repository {owner}/{repo}",
                            event_type="repository",
                            published_at=_parse_github_timestamp(repo_data.get("created_at")),
                            observed_at=observed_at,
                            content_hash=hashlib.sha256(content_raw.encode()).hexdigest(),
                            evidence_reference=f"repo:{owner}/{repo}",
                            metadata={
                                "repository": f"{owner}/{repo}",
                                "description": desc,
                                "stars": repo_data.get("stargazers_count", 0),
                                "forks": repo_data.get("forks_count", 0),
                                "open_issues": repo_data.get("open_issues_count", 0),
                                "pushed_at": pushed_at.isoformat() if pushed_at else None,
                                "default_branch": repo_data.get("default_branch", "main"),
                                "visibility": repo_data.get("visibility", "public"),
                            },
                        )
                    )

                # 2. Fetch Releases
                releases_data = await self._fetch_url_json(client, f"{base_repo_url}/releases", {"per_page": per_page})
                if releases_data and isinstance(releases_data, list):
                    for rel in releases_data:
                        tag_name = rel.get("tag_name", "")
                        rel_name = rel.get("name") or tag_name
                        rel_body = rel.get("body") or ""
                        rel_url = rel.get("html_url", "")
                        pub_dt = _parse_github_timestamp(rel.get("published_at"))
                        raw_hash = hashlib.sha256(f"{tag_name}:{rel_name}:{rel_body}".encode()).hexdigest()
                        records.append(
                            NormalizedRecord(
                                source="github",
                                source_url=rel_url,
                                title=f"Release {tag_name}: {rel_name}",
                                summary=rel_body[:500] if rel_body else f"Release {tag_name}",
                                event_type="release",
                                published_at=pub_dt,
                                observed_at=observed_at,
                                content_hash=raw_hash,
                                evidence_reference=f"release:{tag_name}",
                                metadata={
                                    "repository": f"{owner}/{repo}",
                                    "release_tag": tag_name,
                                    "description": rel_body,
                                    "prerelease": rel.get("prerelease", False),
                                    "draft": rel.get("draft", False),
                                },
                            )
                        )

                # 3. Fetch Tags
                tags_data = await self._fetch_url_json(client, f"{base_repo_url}/tags", {"per_page": per_page})
                if tags_data and isinstance(tags_data, list):
                    for tag in tags_data:
                        t_name = tag.get("name", "")
                        commit_sha = tag.get("commit", {}).get("sha", "")
                        records.append(
                            NormalizedRecord(
                                source="github",
                                source_url=f"https://github.com/{owner}/{repo}/releases/tag/{t_name}",
                                title=f"Tag: {t_name}",
                                summary=f"Git tag {t_name} on commit {commit_sha[:8]}",
                                event_type="tag",
                                published_at=None,
                                observed_at=observed_at,
                                content_hash=hashlib.sha256(f"{t_name}:{commit_sha}".encode()).hexdigest(),
                                evidence_reference=commit_sha,
                                metadata={
                                    "repository": f"{owner}/{repo}",
                                    "release_tag": t_name,
                                    "commit_sha": commit_sha,
                                    "description": f"Git tag {t_name}",
                                },
                            )
                        )

                # 4. Fetch Commits
                commits_data = await self._fetch_url_json(client, f"{base_repo_url}/commits", {"per_page": per_page})
                if commits_data and isinstance(commits_data, list):
                    for c in commits_data:
                        sha = c.get("sha", "")
                        commit_obj = c.get("commit", {})
                        msg = commit_obj.get("message", "")
                        first_line = msg.splitlines()[0] if msg else "Commit"
                        c_date = _parse_github_timestamp(commit_obj.get("committer", {}).get("date"))
                        c_url = c.get("html_url", f"https://github.com/{owner}/{repo}/commit/{sha}")
                        records.append(
                            NormalizedRecord(
                                source="github",
                                source_url=c_url,
                                title=f"Commit: {first_line[:80]}",
                                summary=msg[:500],
                                event_type="commit",
                                published_at=c_date,
                                observed_at=observed_at,
                                content_hash=hashlib.sha256(f"{sha}:{msg}".encode()).hexdigest(),
                                evidence_reference=sha,
                                metadata={
                                    "repository": f"{owner}/{repo}",
                                    "commit_sha": sha,
                                    "description": msg,
                                    "author": commit_obj.get("author", {}).get("name"),
                                },
                            )
                        )

                # 5. Fetch Security Advisories (if available)
                advisories_data = await self._fetch_url_json(
                    client, f"{base_repo_url}/security-advisories", {"per_page": per_page}
                )
                if advisories_data and isinstance(advisories_data, list):
                    for adv in advisories_data:
                        ghsa_id = adv.get("ghsa_id", "")
                        adv_summary = adv.get("summary") or ""
                        adv_desc = adv.get("description") or ""
                        adv_url = adv.get("html_url", f"https://github.com/{owner}/{repo}/security/advisories/{ghsa_id}")
                        adv_pub = _parse_github_timestamp(adv.get("published_at"))
                        records.append(
                            NormalizedRecord(
                                source="github",
                                source_url=adv_url,
                                title=f"Advisory {ghsa_id}: {adv_summary[:80]}",
                                summary=adv_summary or adv_desc[:300],
                                event_type="advisory",
                                published_at=adv_pub,
                                observed_at=observed_at,
                                content_hash=hashlib.sha256(f"{ghsa_id}:{adv_summary}".encode()).hexdigest(),
                                evidence_reference=ghsa_id,
                                metadata={
                                    "repository": f"{owner}/{repo}",
                                    "ghsa_id": ghsa_id,
                                    "cve_id": adv.get("cve_id"),
                                    "severity": adv.get("severity"),
                                    "description": adv_desc,
                                },
                            )
                        )

            else:
                # Search public repositories matching keyword/target
                search_url = f"{self.GITHUB_API_BASE}/search/repositories"
                search_data = await self._fetch_url_json(
                    client, search_url, {"q": repo_target, "per_page": min(per_page, 5), "sort": "updated"}
                )
                if search_data and isinstance(search_data, dict):
                    items = search_data.get("items", [])
                    for item in items:
                        full_name = item.get("full_name", "")
                        item_url = item.get("html_url", "")
                        desc = item.get("description") or ""
                        records.append(
                            NormalizedRecord(
                                source="github",
                                source_url=item_url,
                                title=f"Repository Search: {full_name}",
                                summary=desc or f"Public GitHub repository {full_name}",
                                event_type="repository",
                                published_at=_parse_github_timestamp(item.get("created_at")),
                                observed_at=observed_at,
                                content_hash=hashlib.sha256(f"{full_name}:{desc}".encode()).hexdigest(),
                                evidence_reference=f"repo:{full_name}",
                                metadata={
                                    "repository": full_name,
                                    "description": desc,
                                    "stars": item.get("stargazers_count", 0),
                                    "pushed_at": item.get("pushed_at"),
                                },
                            )
                        )

        return records

    @staticmethod
    def classify_commit_message(msg: str) -> list[str]:
        """Classifies commit messages into semantic attack surface evolution categories."""
        if not msg:
            return []
        lower = msg.lower()
        categories: list[str] = []

        if re.search(r"\b(add|new|create|introduce|expose)\b.*\b(route|endpoint|api|path|handler)\b", lower):
            categories.append("NEW_API")
        elif re.search(r"\b(modify|update|deprecate|refactor|change)\b.*\b(route|endpoint|api)\b", lower):
            categories.append("API_MODIFIED")

        if re.search(r"\b(auth|oauth|sso|saml|jwt|session|mfa|2fa|login|passwordless|credential)\b", lower):
            categories.append("NEW_AUTH")

        if re.search(r"\b(rbac|role|permission|impersonat|access\s*control|privilege|grant)\b", lower):
            categories.append("NEW_AUTHORIZATION")

        if re.search(r"\b(admin|dashboard|management\s*console|internal\s*tool)\b", lower):
            categories.append("NEW_ADMIN")

        if re.search(r"\b(export|download|csv|dump|bulk)\b", lower):
            categories.append("NEW_EXPORT")

        if re.search(r"\b(upload|attachment|file\s*storage|s3|blob)\b", lower):
            categories.append("NEW_UPLOAD")

        if re.search(r"\b(webhook|callback|event\s*stream)\b", lower):
            categories.append("NEW_WEBHOOK")

        if re.search(r"\b(api\s*key|token|secret|pat)\b", lower):
            categories.append("NEW_TOKEN")

        if re.search(r"\b(integration|plugin|connector|partner|slack|stripe|github)\b", lower):
            categories.append("NEW_INTEGRATION")

        if re.search(r"\b(upgrade|downgrade|migrate|bump|update)\b.*\b(version|dependency|framework|package|library)\b", lower):
            categories.append("TECHNOLOGY_CHANGE")

        if re.search(r"\b(config|env|setting|flag|toggle)\b", lower):
            categories.append("CONFIGURATION_CHANGE")

        return categories

    @staticmethod
    def analyze_diff_text(diff_text: str) -> list[dict[str, Any]]:
        """Parses git source diffs to extract canonical semantic artifacts.
        
        Maps source changes directly into the standard AST engine artifact format
        (e.g., ADDED_API_ENDPOINT, AUTHENTICATION_CHANGE).
        """
        if not diff_text:
            return []

        artifacts: list[dict[str, Any]] = []

        for line in diff_text.splitlines():
            line_str = line.strip()
            if not line_str.startswith("+") or line_str.startswith("+++"):
                continue
            line_content = line_str[1:].strip()

            # 1. Check for framework route decorator: @router.post("/path") or @app.get("/path")
            dec_match = re.search(
                r"@(?:app|router|blueprint)\.(get|post|put|delete|patch)\s*\(\s*[\"'](/[^\"']+)[\"']",
                line_content,
                re.IGNORECASE,
            )
            if dec_match:
                method = dec_match.group(1).upper()
                path = dec_match.group(2)
                is_admin = "/admin" in path or "impersonate" in path
                is_auth = any(k in path for k in ("/auth", "/oauth", "/login", "/session", "/token"))
                is_export = any(k in path for k in ("/export", "/download", "/dump"))
                artifacts.append({
                    "artifact_type": "ADDED_API_ENDPOINT",
                    "method": method,
                    "path": path,
                    "category": "ADMINISTRATION" if is_admin else "AUTHENTICATION" if is_auth else "EXPORT" if is_export else "GENERAL",
                    "security_sensitive": is_admin or is_auth or is_export,
                })
                continue

            # 2. Check for HTTP method + path declaration: POST /api/admin/impersonate
            method_match = re.search(
                r"\b(GET|POST|PUT|DELETE|PATCH)\s+([\"']?/[a-zA-Z0-9_\-\/{}:]+[\"']?)",
                line_content,
                re.IGNORECASE,
            )
            if method_match:
                method = method_match.group(1).upper()
                path = method_match.group(2).strip("\"'")
                is_admin = "/admin" in path or "impersonate" in path
                is_auth = any(k in path for k in ("/auth", "/oauth", "/login", "/session", "/token"))
                is_export = any(k in path for k in ("/export", "/download", "/dump"))
                artifacts.append({
                    "artifact_type": "ADDED_API_ENDPOINT",
                    "method": method,
                    "path": path,
                    "category": "ADMINISTRATION" if is_admin else "AUTHENTICATION" if is_auth else "EXPORT" if is_export else "GENERAL",
                    "security_sensitive": is_admin or is_auth or is_export,
                })

        return artifacts

    async def fetch_historical_releases(
        self, owner: str, repo: str, limit: int = 30
    ) -> list[dict[str, Any]]:
        """Fetches public releases and tags with semantic change extraction."""
        releases: list[dict[str, Any]] = []
        base_url = f"{self.GITHUB_API_BASE}/repos/{owner}/{repo}/releases"

        async with httpx.AsyncClient(timeout=15.0) as client:
            data = await self._fetch_url_json(client, base_url, {"per_page": min(limit, 100)})
            if data and isinstance(data, list):
                for rel in data:
                    body = rel.get("body") or ""
                    tag = rel.get("tag_name") or ""
                    title = rel.get("name") or tag
                    pub_dt = _parse_github_timestamp(rel.get("published_at"))

                    # Semantic extraction from release notes
                    semantic_changes = self.classify_commit_message(f"{title}\n{body}")

                    releases.append({
                        "tag": tag,
                        "title": title,
                        "body": body,
                        "published_at": pub_dt,
                        "source_url": rel.get("html_url"),
                        "repository": f"{owner}/{repo}",
                        "semantic_changes": semantic_changes,
                        "confidence": 0.98 if pub_dt else 0.85,
                    })

        return releases

    def normalize_webhook_payload(self, event_name: str, payload: dict[str, Any]) -> list[NormalizedRecord]:
        """Normalizes GitHub webhook payloads (release, push, security_advisory)."""
        records: list[NormalizedRecord] = []
        repo = payload.get("repository", {}).get("full_name", "unknown")
        repo_url = payload.get("repository", {}).get("html_url", "")

        if event_name == "release":
            rel = payload.get("release", {})
            tag = rel.get("tag_name", "")
            title = rel.get("name") or tag
            body = rel.get("body", "")
            pub_dt = _parse_github_timestamp(rel.get("published_at")) or datetime.now(timezone.utc)
            chash = hashlib.sha256(f"gh_webhook:release:{repo}:{tag}".encode()).hexdigest()

            records.append(
                NormalizedRecord(
                    source="GITHUB_WEBHOOK",
                    source_url=rel.get("html_url") or repo_url,
                    title=f"GitHub release {tag} published for {repo}",
                    summary=body[:500] if body else f"Release {tag} created.",
                    event_type="PRODUCT_RELEASE",
                    published_at=pub_dt,
                    observed_at=datetime.now(timezone.utc),
                    content_hash=chash,
                    evidence_reference=f"github:release:{repo}:{tag}",
                    metadata={"repository": repo, "tag": tag, "event": "release", "authority_level": "OFFICIAL_RELEASE"},
                )
            )

        elif event_name == "repository_advisory":
            adv = payload.get("security_advisory", {})
            cve_id = adv.get("cve_id") or adv.get("ghsa_id", "Unknown")
            summary = adv.get("summary", "")
            chash = hashlib.sha256(f"gh_webhook:advisory:{repo}:{cve_id}".encode()).hexdigest()

            records.append(
                NormalizedRecord(
                    source="GITHUB_WEBHOOK",
                    source_url=adv.get("html_url") or repo_url,
                    title=f"Security advisory {cve_id} published for {repo}",
                    summary=summary[:500],
                    event_type="SECURITY_ADVISORY",
                    published_at=datetime.now(timezone.utc),
                    observed_at=datetime.now(timezone.utc),
                    content_hash=chash,
                    evidence_reference=f"github:advisory:{repo}:{cve_id}",
                    metadata={"repository": repo, "cve_id": cve_id, "severity": adv.get("severity"), "authority_level": "OFFICIAL_SECURITY_ADVISORY"},
                )
            )

        return records


