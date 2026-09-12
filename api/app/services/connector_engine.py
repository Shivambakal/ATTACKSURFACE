"""Connector engine for multi-source corporate intelligence collection.

Handles:
- Conditional HTTP requests (ETag / If-None-Match, Last-Modified / If-Modified-Since)
- SHA-256 content hashing and unchanged payload detection
- Immutable RawSourceSnapshot preservation
- Versioned parser execution (RSS/Atom, JSON, Structured HTML)
- Safe failure isolation (network errors/429s/timeouts never emit false "product removed" events)
- SSRF safe URL outbound validation
"""
from __future__ import annotations

import abc
import hashlib
import logging
import re
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any
import urllib.parse
import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models.source_registry import (
    CompanySource,
    RawSourceSnapshot,
    SourceCollectionRun,
    NormalizedSourceDocument,
    SourceHealth,
    SourceStatus,
    SourceHealthState,
)
from ..services.target_safety import validate_url_for_collection
from .change_quality_gate import ChangeQualityGate, QualityDecision, clean_text_content, canonicalize_url

logger = logging.getLogger(__name__)


def parse_feed_datetime(date_str: str | None) -> datetime | None:
    """Safely parses standard RSS (RFC-2822) and Atom (ISO-8601) dates into UTC datetime."""
    if not date_str or not date_str.strip():
        return None
    s = date_str.strip()
    # 1. Try ISO-8601 (common in Atom)
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        pass
    # 2. Try RFC-2822 / email format (common in RSS 2.0)
    try:
        dt = parsedate_to_datetime(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        pass
    return None


def find_node(parent: ET.Element | None, *tags: str) -> ET.Element | None:
    """Find the first matching child element among tags without triggering boolean falsiness on empty elements."""
    if parent is None:
        return None
    for tag in tags:
        n = parent.find(tag)
        if n is not None:
            return n
    return None


@dataclass
class ParsedItem:
    """A single normalized item extracted from a source document."""
    item_id: str
    title: str
    summary: str
    change_type: str
    published_at: datetime | None = None
    updated_at: datetime | None = None
    effective_at: datetime | None = None
    url: str = ""
    product: str | None = None
    platform: str | None = None
    api_endpoint: str | None = None
    api_method: str | None = None  # Never hallucinate "UNKNOWN"; leave None if unobserved
    version: str | None = None
    permission: str | None = None
    quality_decision: str = "ACCEPTED"
    rejection_reason: str | None = None
    freshness_category: str = "RECENT"
    raw_attributes: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert ParsedItem to a JSON-serializable dictionary."""
        d = dict(self.__dict__)
        if isinstance(d.get("published_at"), datetime):
            d["published_at"] = d["published_at"].isoformat()
        if isinstance(d.get("updated_at"), datetime):
            d["updated_at"] = d["updated_at"].isoformat()
        if isinstance(d.get("effective_at"), datetime):
            d["effective_at"] = d["effective_at"].isoformat()
        return d


@dataclass
class FetchResult:
    """Result of a connector fetch and parse cycle."""
    status: str  # SUCCESS_CHANGED, SUCCESS_UNCHANGED, FAILED, RATE_LIMITED
    http_status: int | None = None
    etag: str | None = None
    last_modified: str | None = None
    content_hash: str | None = None
    raw_body: str | None = None
    items: list[ParsedItem] = field(default_factory=list)
    duration_ms: int = 0
    error_message: str | None = None
    credits_used: float = 0.0
    response_bytes: int = 0


class BaseConnector(abc.ABC):
    """Abstract interface for all source connectors."""

    def __init__(self, parser_version: str = "1.0.0"):
        self.parser_version = parser_version

    @abc.abstractmethod
    async def fetch_and_parse(self, source: CompanySource, client: httpx.AsyncClient) -> FetchResult:
        """Fetch content conditionally and parse changed items."""
        ...


class GenericFeedConnector(BaseConnector):
    """Standard RSS / Atom feed connector supporting ETag and Last-Modified."""

    async def fetch_and_parse(self, source: CompanySource, client: httpx.AsyncClient) -> FetchResult:
        target_url = source.feed_url or source.source_url
        safe, reason = validate_url_for_collection(target_url)
        if not safe:
            return FetchResult(
                status="FAILED",
                error_message=f"SSRF safety check rejected URL: {reason}",
            )

        headers: dict[str, str] = {
            "User-Agent": "AttackSurfaceTimeline-Intelligence/1.0 (Authorized Research)",
            "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, */*",
        }
        if source.etag:
            headers["If-None-Match"] = source.etag
        if source.last_modified:
            headers["If-Modified-Since"] = source.last_modified

        start_time = time.monotonic()
        try:
            resp = await client.get(target_url, headers=headers, timeout=20.0, follow_redirects=True)
            duration_ms = int((time.monotonic() - start_time) * 1000)

            if resp.status_code == 304:
                return FetchResult(
                    status="SUCCESS_UNCHANGED",
                    http_status=304,
                    etag=resp.headers.get("etag") or source.etag,
                    last_modified=resp.headers.get("last-modified") or source.last_modified,
                    duration_ms=duration_ms,
                    response_bytes=0,
                )

            if resp.status_code == 429:
                retry_after = resp.headers.get("retry-after", "60")
                return FetchResult(
                    status="RATE_LIMITED",
                    http_status=429,
                    duration_ms=duration_ms,
                    error_message=f"Rate limited by provider. Retry-After: {retry_after}s",
                )

            if resp.status_code >= 400:
                return FetchResult(
                    status="FAILED",
                    http_status=resp.status_code,
                    duration_ms=duration_ms,
                    error_message=f"HTTP Error {resp.status_code}: {resp.text[:200]}",
                )

            body_text = resp.text
            content_hash = hashlib.sha256(body_text.encode("utf-8")).hexdigest()

            # Hash check: if content is unchanged, treat as unchanged
            if source.content_hash and source.content_hash == content_hash:
                return FetchResult(
                    status="SUCCESS_UNCHANGED",
                    http_status=resp.status_code,
                    etag=resp.headers.get("etag") or source.etag,
                    last_modified=resp.headers.get("last-modified") or source.last_modified,
                    content_hash=content_hash,
                    duration_ms=duration_ms,
                    response_bytes=len(resp.content),
                )

            # Parse XML/RSS/Atom items
            items = self._parse_feed_items(body_text, source)

            # Resilient fallback: If XML feed parsing yields 0 items and response is HTML,
            # discover linked RSS/Atom feeds or parse structured HTML advisories/bulletins.
            if not items and ("<html" in body_text.lower() or "<!doctype" in body_text.lower()):
                discovered_feed = self._discover_feed_url(body_text, target_url)
                if discovered_feed and discovered_feed != target_url:
                    try:
                        feed_resp = await client.get(discovered_feed, headers=headers, timeout=15.0, follow_redirects=True)
                        if feed_resp.status_code == 200:
                            items = self._parse_feed_items(feed_resp.text, source)
                            if items:
                                source.feed_url = discovered_feed
                    except Exception as feed_err:
                        logger.debug("Discovered feed fetch failed for %s: %s", discovered_feed, feed_err)

                if not items:
                    items = self._parse_html_advisories(body_text, source, target_url)

            return FetchResult(
                status="SUCCESS_CHANGED" if items else "SUCCESS_UNCHANGED",
                http_status=resp.status_code,
                etag=resp.headers.get("etag"),
                last_modified=resp.headers.get("last-modified"),
                content_hash=content_hash,
                raw_body=body_text,
                items=items,
                duration_ms=duration_ms,
                response_bytes=len(resp.content),
            )

        except Exception as exc:
            duration_ms = int((time.monotonic() - start_time) * 1000)
            return FetchResult(
                status="FAILED",
                duration_ms=duration_ms,
                error_message=f"Network/transport exception: {type(exc).__name__}: {str(exc)}",
            )

    def _parse_feed_items(self, xml_text: str, source: CompanySource) -> list[ParsedItem]:
        items: list[ParsedItem] = []
        try:
            root = ET.fromstring(xml_text)
        except Exception:
            return items

        # RSS 2.0 channel -> item
        channel = root.find("channel")
        entries = channel.findall("item") if channel is not None else []
        # Atom feed -> entry
        if not entries:
            entries = root.findall("{http://www.w3.org/2005/Atom}entry") or root.findall("entry")

        for entry in entries[:50]:
            title_node = find_node(entry, "title", "{http://www.w3.org/2005/Atom}title")
            raw_title = title_node.text.strip() if (title_node is not None and title_node.text) else ""

            # Publisher timestamp (pubDate for RSS, updated/published for Atom)
            date_node = find_node(
                entry,
                "pubDate",
                "published",
                "{http://www.w3.org/2005/Atom}published",
                "updated",
                "{http://www.w3.org/2005/Atom}updated",
                "dc:date",
            )
            pub_date = parse_feed_datetime(date_node.text) if (date_node is not None and date_node.text) else None

            desc_node = find_node(
                entry,
                "description",
                "content:encoded",
                "{http://purl.org/rss/1.0/modules/content/}encoded",
                "summary",
                "{http://www.w3.org/2005/Atom}summary",
                "{http://www.w3.org/2005/Atom}content",
                "content",
            )
            raw_summary = desc_node.text if (desc_node is not None and desc_node.text) else ""
            clean_summary = clean_text_content(raw_summary)

            link_node = find_node(entry, "link", "{http://www.w3.org/2005/Atom}link")
            link = ""
            if link_node is not None:
                link = link_node.attrib.get("href") or link_node.text or ""
            link = canonicalize_url(link)

            guid_node = find_node(entry, "guid", "id", "{http://www.w3.org/2005/Atom}id")
            item_id = guid_node.text.strip() if (guid_node is not None and guid_node.text) else (link or raw_title)

            # Classify change type based on title/summary semantics
            change_type = "PRODUCT_UPDATE"
            lower_text = f"{raw_title} {clean_summary}".lower()
            if any(k in lower_text for k in ["advisory", "vulnerability", "cve", "security update", "patch", "bulletin"]):
                change_type = "SECURITY_UPDATE"
            elif any(k in lower_text for k in ["api", "endpoint", "webhook", "oauth", "rest api"]):
                change_type = "API_CHANGE"
            elif any(k in lower_text for k in ["deprecat", "retire", "sunset", "end of life"]):
                change_type = "DEPRECATION"
            elif any(k in lower_text for k in ["launch", "announcing", "new feature", "introduce", "available now"]):
                change_type = "FEATURE_ADDED"

            items.append(
                ParsedItem(
                    item_id=item_id,
                    title=raw_title,
                    summary=clean_summary[:1000],
                    change_type=change_type,
                    published_at=pub_date,
                    url=link,
                    product=source.product_scope,
                    platform=source.platform_scope,
                    api_method=None,
                    api_endpoint=None,
                )
            )
        return items

    def _discover_feed_url(self, html_text: str, base_url: str) -> str | None:
        """Autodiscover RSS/Atom feed URL from HTML <link> or <a> tags."""
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html_text, "html.parser")
            # 1. Check standard <link rel="alternate" type="...">
            for link in soup.find_all("link", rel=lambda r: r and "alternate" in r):
                t = (link.get("type") or "").lower()
                if "rss" in t or "atom" in t or "xml" in t:
                    href = link.get("href")
                    if href:
                        return urllib.parse.urljoin(base_url, href)

            # 2. Check <a> links with /feed or /rss in href
            for a in soup.find_all("a", href=True):
                href = a["href"].strip().lower()
                text = a.get_text(strip=True).lower()
                if any(x in href or x in text for x in ["rss/feed", "/feed/", "feed.xml", "rss.xml", "atom.xml"]):
                    return urllib.parse.urljoin(base_url, a["href"])
        except Exception as exc:
            logger.debug("Error autodiscovering feed URL: %s", exc)
        return None

    def _parse_html_advisories(self, html_text: str, source: CompanySource, base_url: str) -> list[ParsedItem]:
        """Extracts structured advisory and release bulletin items directly from HTML."""
        from bs4 import BeautifulSoup
        items: list[ParsedItem] = []
        try:
            soup = BeautifulSoup(html_text, "html.parser")
            seen_urls: set[str] = set()
            now = datetime.now(timezone.utc)

            # Search prominent links and cards
            for a in soup.find_all("a", href=True):
                text = clean_text_content(a.get_text(strip=True))
                href = a["href"].strip()
                if not text or len(text) < 12 or len(text) > 250:
                    continue
                lower = f"{text} {href}".lower()
                is_bulletin = any(k in lower for k in [
                    "cve-", "advisory", "security update", "bulletin", "vulnerability",
                    "security alert", "patch", "zero-day", "security release", "security notice",
                    "release notes", "changelog"
                ])
                if is_bulletin:
                    full_url = urllib.parse.urljoin(base_url, href)
                    canon_url = canonicalize_url(full_url)
                    if canon_url in seen_urls:
                        continue
                    seen_urls.add(canon_url)

                    change_type = "SECURITY_UPDATE" if any(k in lower for k in ["cve-", "security", "vulnerability", "advisory", "patch"]) else "PRODUCT_UPDATE"
                    item_id = hashlib.sha256(f"{source.id}:{canon_url}:{text}".encode()).hexdigest()[:32]
                    items.append(
                        ParsedItem(
                            item_id=item_id,
                            title=text,
                            summary=f"Security advisory / bulletin notice: {text}",
                            change_type=change_type,
                            published_at=now,
                            url=canon_url,
                            product=source.product_scope,
                            platform=source.platform_scope,
                        )
                    )
                    if len(items) >= 30:
                        break
        except Exception as exc:
            logger.debug("HTML advisory extraction error: %s", exc)
        return items


class GoogleCloudReleaseNotesConnector(BaseConnector):
    """Specialized parser for Google Cloud Release Notes Atom feed.
    
    Extracts individual product subsections (<h2 class="release-note-product-title">)
    so each change has its real product name, headline, clean summary, and timestamp,
    rather than smashing multiple products into a date title.
    """

    def __init__(self, parser_version: str = "2.0.0"):
        super().__init__(parser_version=parser_version)
        self.feed_connector = GenericFeedConnector(parser_version=parser_version)

    async def fetch_and_parse(self, source: CompanySource, client: httpx.AsyncClient) -> FetchResult:
        res = await self.feed_connector.fetch_and_parse(source, client)
        if res.status != "SUCCESS_CHANGED" or not res.raw_body:
            return res

        unpacked = self._unpack_google_cloud_items(res.raw_body, source)
        if unpacked:
            res.items = unpacked
        return res

    def _unpack_google_cloud_items(self, xml_text: str, source: CompanySource) -> list[ParsedItem]:
        items: list[ParsedItem] = []
        try:
            root = ET.fromstring(xml_text)
        except Exception:
            return items

        entries = root.findall("{http://www.w3.org/2005/Atom}entry") or root.findall("entry")
        for entry in entries[:30]:
            entry_id_node = find_node(entry, "{http://www.w3.org/2005/Atom}id", "id")
            entry_id = entry_id_node.text.strip() if (entry_id_node is not None and entry_id_node.text) else ""

            updated_node = find_node(
                entry,
                "{http://www.w3.org/2005/Atom}updated",
                "updated",
                "{http://www.w3.org/2005/Atom}published",
                "published",
            )
            pub_date = parse_feed_datetime(updated_node.text) if (updated_node is not None and updated_node.text) else None

            link_node = find_node(entry, "{http://www.w3.org/2005/Atom}link", "link")
            entry_url = ""
            if link_node is not None:
                entry_url = link_node.attrib.get("href") or link_node.text or ""
            entry_url = canonicalize_url(entry_url)

            content_node = find_node(
                entry,
                "{http://www.w3.org/2005/Atom}content",
                "content",
                "{http://www.w3.org/2005/Atom}summary",
                "summary",
            )
            raw_html = content_node.text if (content_node is not None and content_node.text) else ""

            if 'class="release-note-product-title"' in raw_html or "class='release-note-product-title'" in raw_html:
                parts = re.split(r'<h2\s+class=[\'"]release-note-product-title[\'"]\s*>([^<]+)</h2>', raw_html, flags=re.IGNORECASE)
                for i in range(1, len(parts), 2):
                    product_name = parts[i].strip()
                    section_html = parts[i+1] if i+1 < len(parts) else ""

                    kind_match = re.search(r'<h3[^>]*>([^<]+)</h3>', section_html, flags=re.IGNORECASE)
                    change_kind = kind_match.group(1).strip() if kind_match else "Change"

                    strong_match = re.search(r'<strong>([^<]+)</strong>', section_html, flags=re.IGNORECASE)
                    headline = strong_match.group(1).strip() if strong_match else ""

                    clean_summary = clean_text_content(section_html)

                    change_type = "PRODUCT_UPDATE"
                    lower_kind = f"{change_kind} {headline}".lower()
                    if any(k in lower_kind for k in ["security", "vulnerability", "cve"]):
                        change_type = "SECURITY_UPDATE"
                    elif any(k in lower_kind for k in ["api", "endpoint", "gateway", "webhook", "rest"]):
                        change_type = "API_CHANGE"
                    elif any(k in lower_kind for k in ["deprecat", "sunset", "end of life"]):
                        change_type = "DEPRECATION"
                    elif any(k in lower_kind for k in ["feature", "new", "announc", "ga", "generally available"]):
                        change_type = "FEATURE_ADDED"

                    if headline:
                        title = f"Google Cloud {product_name}: {headline}"
                    else:
                        title = f"Google Cloud {product_name}: {change_kind}"

                    prod_slug = re.sub(r'[^a-zA-Z0-9]+', '-', product_name).strip('-').lower()
                    item_id = f"{entry_id}#{prod_slug}" if entry_id else f"{entry_url}#{prod_slug}"

                    items.append(
                        ParsedItem(
                            item_id=item_id,
                            title=title,
                            summary=clean_summary[:1000],
                            change_type=change_type,
                            published_at=pub_date,
                            url=entry_url or (source.feed_url or source.source_url),
                            product=product_name,
                            platform="Google Cloud",
                            api_method=None,
                            api_endpoint=None,
                            raw_attributes={"change_kind": change_kind, "headline": headline},
                        )
                    )
            else:
                title_node = find_node(entry, "{http://www.w3.org/2005/Atom}title", "title")
                raw_title = title_node.text.strip() if (title_node is not None and title_node.text) else ""
                clean_summary = clean_text_content(raw_html)
                if raw_title and clean_summary:
                    items.append(
                        ParsedItem(
                            item_id=entry_id or entry_url,
                            title=raw_title,
                            summary=clean_summary[:1000],
                            change_type="PRODUCT_UPDATE",
                            published_at=pub_date,
                            url=entry_url or (source.feed_url or source.source_url),
                            product=source.product_scope,
                            platform=source.platform_scope,
                            api_method=None,
                            api_endpoint=None,
                        )
                    )
        return items


class JsonApiConnector(BaseConnector):
    """JSON API connector for structured discovery and roadmap endpoints."""

    async def fetch_and_parse(self, source: CompanySource, client: httpx.AsyncClient) -> FetchResult:
        target_url = source.api_url or source.source_url
        safe, reason = validate_url_for_collection(target_url)
        if not safe:
            return FetchResult(status="FAILED", error_message=f"SSRF safety check rejected URL: {reason}")

        headers = {
            "User-Agent": "AttackSurfaceTimeline-Intelligence/1.0",
            "Accept": "application/json",
        }
        if source.etag:
            headers["If-None-Match"] = source.etag
        if source.last_modified:
            headers["If-Modified-Since"] = source.last_modified

        start_time = time.monotonic()
        try:
            resp = await client.get(target_url, headers=headers, timeout=20.0, follow_redirects=True)
            duration_ms = int((time.monotonic() - start_time) * 1000)

            if resp.status_code == 304:
                return FetchResult(
                    status="SUCCESS_UNCHANGED",
                    http_status=304,
                    etag=resp.headers.get("etag") or source.etag,
                    duration_ms=duration_ms,
                )

            if resp.status_code != 200:
                return FetchResult(
                    status="FAILED",
                    http_status=resp.status_code,
                    duration_ms=duration_ms,
                    error_message=f"JSON API response {resp.status_code}",
                )

            body_text = resp.text
            content_hash = hashlib.sha256(body_text.encode("utf-8")).hexdigest()

            if source.content_hash == content_hash:
                return FetchResult(
                    status="SUCCESS_UNCHANGED",
                    http_status=200,
                    content_hash=content_hash,
                    duration_ms=duration_ms,
                )

            data = resp.json()
            items: list[ParsedItem] = []
            if isinstance(data, list):
                raw_list = data[:50]
            elif isinstance(data, dict):
                raw_list = data.get("items") or data.get("features") or data.get("value") or [data]
            else:
                raw_list = []

            for idx, obj in enumerate(raw_list):
                if not isinstance(obj, dict):
                    continue
                item_title = obj.get("title") or obj.get("name") or f"API Item {idx+1}"
                item_summary = obj.get("description") or obj.get("summary") or ""
                items.append(
                    ParsedItem(
                        item_id=str(obj.get("id", idx)),
                        title=str(item_title),
                        summary=str(item_summary)[:1000],
                        change_type="API_UPDATED",
                        url=str(obj.get("url", target_url)),
                        product=source.product_scope,
                        platform=source.platform_scope,
                    )
                )

            return FetchResult(
                status="SUCCESS_CHANGED" if items else "SUCCESS_UNCHANGED",
                http_status=200,
                etag=resp.headers.get("etag"),
                last_modified=resp.headers.get("last-modified"),
                content_hash=content_hash,
                raw_body=body_text,
                items=items,
                duration_ms=duration_ms,
                response_bytes=len(resp.content),
            )

        except Exception as exc:
            duration_ms = int((time.monotonic() - start_time) * 1000)
            return FetchResult(
                status="FAILED",
                duration_ms=duration_ms,
                error_message=f"JSON API error: {type(exc).__name__}: {str(exc)}",
            )


class ConnectorEngine:
    """Orchestrates source collection, conditional validation, persistence, and failure isolation."""

    def __init__(self):
        self.feed_connector = GenericFeedConnector()
        self.json_connector = JsonApiConnector()
        self.google_cloud_connector = GoogleCloudReleaseNotesConnector()
        self.quality_gate = ChangeQualityGate()

    def get_connector(self, strategy: str) -> BaseConnector:
        strat = (strategy or "").lower()
        if "google_cloud" in strat:
            return self.google_cloud_connector
        if "json" in strat or "api" in strat:
            return self.json_connector
        return self.feed_connector

    async def execute_source(self, source_id: int, db: Session, client: httpx.AsyncClient | None = None) -> FetchResult:
        """Executes a single source check with transaction management and failure isolation."""
        source = db.get(CompanySource, source_id)
        if not source:
            raise ValueError(f"CompanySource {source_id} not found.")

        connector = self.get_connector(source.parser_strategy)
        owns_client = client is None
        http_client = client or httpx.AsyncClient()

        run = SourceCollectionRun(
            source_id=source.id,
            started_at=datetime.now(timezone.utc),
            status="RUNNING",
        )
        db.add(run)
        db.flush()

        source.status = SourceStatus.RUNNING.value

        try:
            result = await connector.fetch_and_parse(source, http_client)
            now = datetime.now(timezone.utc)
            source.last_checked_at = now

            # Ensure health record exists
            health = db.scalar(select(SourceHealth).where(SourceHealth.source_id == source.id))
            if not health:
                health = SourceHealth(source_id=source.id, health_state=SourceHealthState.HEALTHY.value, consecutive_failures=0)
                db.add(health)

            if health.consecutive_failures is None:
                health.consecutive_failures = 0
            if source.consecutive_failures is None:
                source.consecutive_failures = 0

            health.last_checked_at = now
            health.latency_ms = result.duration_ms

            if result.status == "SUCCESS_UNCHANGED" or (result.status == "SUCCESS_CHANGED" and len(result.items) == 0):
                source.status = SourceStatus.SUCCESS_UNCHANGED.value
                source.consecutive_failures = 0
                source.last_http_status = result.http_status
                if result.etag:
                    source.etag = result.etag
                if result.last_modified:
                    source.last_modified = result.last_modified

                run.status = "SUCCESS_UNCHANGED"
                run.http_status = result.http_status
                run.duration_ms = result.duration_ms
                run.items_found = len(result.items)
                run.items_changed = 0

                health.health_state = SourceHealthState.HEALTHY.value
                health.consecutive_failures = 0

            elif result.status == "SUCCESS_CHANGED":
                source.status = SourceStatus.SUCCESS_CHANGED.value
                prev_success_at = source.last_success_at
                source.last_success_at = now
                source.last_changed_at = now
                source.consecutive_failures = 0
                source.last_http_status = result.http_status
                if result.etag:
                    source.etag = result.etag
                if result.last_modified:
                    source.last_modified = result.last_modified
                if result.content_hash:
                    source.content_hash = result.content_hash

                # 1. Evaluate extracted items through ChangeQualityGate
                accepted_items: list[ParsedItem] = []
                context_items: list[ParsedItem] = []
                rejected_items: list[ParsedItem] = []

                for item in result.items:
                    eval_result = self.quality_gate.evaluate(
                        title=item.title,
                        summary=item.summary,
                        url=item.url,
                        source_name=source.name,
                        published_at=item.published_at,
                        updated_at=item.updated_at,
                        last_collection_at=prev_success_at,
                        change_type=item.change_type,
                        api_endpoint=item.api_endpoint,
                        api_method=item.api_method,
                    )
                    item.quality_decision = eval_result.decision.value
                    item.rejection_reason = eval_result.rejection_reason
                    item.freshness_category = eval_result.freshness.value
                    item.security_relevance = eval_result.relevance.value
                    item.relevance_score = eval_result.relevance_score
                    item.title = eval_result.cleaned_title
                    item.summary = eval_result.cleaned_summary
                    item.url = eval_result.canonical_url

                    if eval_result.decision == QualityDecision.ACCEPTED:
                        accepted_items.append(item)
                    elif eval_result.decision == QualityDecision.CONTEXT_ONLY:
                        context_items.append(item)
                    else:
                        rejected_items.append(item)

                # 2. Create immutable RawSourceSnapshot
                raw_snapshot = RawSourceSnapshot(
                    source_id=source.id,
                    company_id=source.company_id,
                    retrieved_at=now,
                    url=source.feed_url or source.source_url,
                    http_status=result.http_status or 200,
                    etag=result.etag,
                    last_modified=result.last_modified,
                    content_type="application/xml" if "feed" in source.parser_strategy or "rss" in source.parser_strategy else "application/json",
                    content_hash=result.content_hash or hashlib.sha256((result.raw_body or "").encode()).hexdigest(),
                    body_raw=result.raw_body or "",
                    body_size=len((result.raw_body or "").encode("utf-8")),
                    parser_version=connector.parser_version,
                )
                db.add(raw_snapshot)
                db.flush()

                # 3. Create NormalizedSourceDocument (preserving all items with audit quality evaluation)
                norm_doc = NormalizedSourceDocument(
                    raw_snapshot_id=raw_snapshot.id,
                    source_id=source.id,
                    company_id=source.company_id,
                    title=f"Update for {source.name}",
                    summary=f"Extracted {len(result.items)} items (Accepted: {len(accepted_items)}, Context: {len(context_items)}, Rejected: {len(rejected_items)})",
                    extracted_items=[item.to_dict() for item in result.items],
                    parser_name=source.parser_strategy,
                    parser_version=connector.parser_version,
                )
                db.add(norm_doc)
                db.flush()

                # 4. Cluster and fuse only valid items (ACCEPTED + CONTEXT_ONLY, never REJECTED)
                valid_items = accepted_items + context_items
                if source.company_id and valid_items:
                    try:
                        from .corporate_clustering import CorporateClusteringService
                        clustering_service = CorporateClusteringService(db)
                        clustering_service.cluster_extracted_items(
                            company_id=source.company_id,
                            source_id=source.id,
                            items=[item.to_dict() for item in valid_items],
                            authority_level=source.authority_level or "OFFICIAL_RELEASE",
                        )
                    except Exception as cluster_err:
                        logger.warning("Clustering error for source %s: %s", source.id, cluster_err)

                run.status = "SUCCESS_CHANGED"
                run.http_status = result.http_status
                run.duration_ms = result.duration_ms
                run.items_found = len(result.items)
                run.items_changed = len(valid_items)
                run.raw_snapshot_id = raw_snapshot.id
                run.response_bytes = result.response_bytes

                health.health_state = SourceHealthState.HEALTHY.value
                health.consecutive_failures = 0
                health.last_success_at = now

            elif result.status == "RATE_LIMITED":
                source.status = SourceStatus.RATE_LIMITED.value
                source.last_http_status = 429
                source.last_error = result.error_message

                run.status = "RATE_LIMITED"
                run.http_status = 429
                run.error_message = result.error_message
                run.duration_ms = result.duration_ms

                health.health_state = SourceHealthState.DEGRADED.value

            else:  # FAILED
                source.status = SourceStatus.FAILED.value
                source.consecutive_failures += 1
                source.last_http_status = result.http_status
                source.last_error = result.error_message

                run.status = "FAILED"
                run.http_status = result.http_status
                run.error_message = result.error_message
                run.duration_ms = result.duration_ms

                health.consecutive_failures += 1
                if health.consecutive_failures >= 3:
                    health.health_state = SourceHealthState.FAILED.value
                else:
                    health.health_state = SourceHealthState.DEGRADED.value

            run.finished_at = datetime.now(timezone.utc)
            db.commit()
            return result

        except Exception as exc:
            db.rollback()
            logger.exception("Unexpected error executing source %s", source_id)
            source = db.get(CompanySource, source_id)
            if source:
                source.status = SourceStatus.FAILED.value
                source.consecutive_failures = (source.consecutive_failures or 0) + 1
                source.last_error = str(exc)
                health = db.scalar(select(SourceHealth).where(SourceHealth.source_id == source.id))
                if health:
                    health.consecutive_failures = (health.consecutive_failures or 0) + 1
                    health.health_state = SourceHealthState.FAILED.value if health.consecutive_failures >= 3 else SourceHealthState.DEGRADED.value
                    health.last_checked_at = datetime.now(timezone.utc)
            db.commit()
            return FetchResult(status="FAILED", error_message=str(exc))
        finally:
            if owns_client:
                await http_client.aclose()
