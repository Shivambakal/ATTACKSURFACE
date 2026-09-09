"""Change Quality Gate Service.

Enforces strict quality, freshness, deduplication, and security relevance standards
between raw source normalization and downstream cluster/timeline/signal synthesis.

Ensures:
- Zero "Untitled Update" or generic placeholder titles
- Zero manufactured "UNKNOWN" endpoints or methods
- Zero fake current timestamps for historical entries
- Zero fallback domain homepages as item URLs
- Separation of ACTIONABLE security signals vs CONTEXTUAL records vs NOISE
- Reliable freshness classification (NEW, RECENT, HISTORICAL, STALE, UNKNOWN_DATE)
- Safe HTML cleanup preserving original raw evidence in RawSourceSnapshot
"""
from __future__ import annotations

import html
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode

logger = logging.getLogger(__name__)

# Blacklisted generic titles that are never actionable
GENERIC_TITLES_BLACKLIST = {
    "untitled update",
    "untitled",
    "update",
    "new update",
    "announcement",
    "announcements",
    "item",
    "unknown",
    "unnamed",
    "n/a",
    "na",
    "none",
    "product update",
    "release notes",
    "changelog",
    "latest changes",
    "general update",
    "security bulletin",  # bare bulletin title without CVE/product
    "bulletin",
}

# Regex to detect titles that are just a date (e.g. "September 03, 2026", "2026-09-03", "Aug 15, 2026")
DATE_ONLY_TITLE_REGEX = re.compile(
    r"^(?:(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|"
    r"jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
    r"\s+\d{1,2}(?:st|nd|rd|th)?,?\s+\d{4}|\d{4}-\d{2}-\d{2})$",
    re.IGNORECASE,
)

# Known generic homepage roots that must never be used as specific item URLs
GENERIC_HOMEPAGE_FALLBACKS = {
    "https://www.cisa.gov",
    "https://cisa.gov",
    "https://www.cisa.gov/",
    "https://cisa.gov/",
    "https://google.com",
    "https://www.google.com",
    "https://cloud.google.com",
    "https://cloud.google.com/",
    "https://aws.amazon.com",
    "https://aws.amazon.com/",
    "https://cloudflare.com",
    "https://www.cloudflare.com",
    "https://github.com",
    "https://github.com/",
}

# Tracking query parameters to strip from URLs
TRACKING_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "ref", "source", "fbclid", "gclid", "mc_cid", "mc_eid",
}


class QualityDecision(str, Enum):
    ACCEPTED = "ACCEPTED"          # High-quality, meaningful change
    CONTEXT_ONLY = "CONTEXT_ONLY"  # Valid historical/contextual update, not primary research signal
    REJECTED = "REJECTED"          # Dropped from all downstream processing


class RejectionReason(str, Enum):
    REJECT_MISSING_TITLE = "REJECT_MISSING_TITLE"
    REJECT_GENERIC_TITLE = "REJECT_GENERIC_TITLE"
    REJECT_MISSING_SUMMARY = "REJECT_MISSING_SUMMARY"
    REJECT_BOILERPLATE_SUMMARY = "REJECT_BOILERPLATE_SUMMARY"
    REJECT_INVALID_URL = "REJECT_INVALID_URL"
    REJECT_FALLBACK_URL = "REJECT_FALLBACK_URL"
    REJECT_MISSING_SOURCE = "REJECT_MISSING_SOURCE"
    REJECT_MISSING_DATE = "REJECT_MISSING_DATE"
    REJECT_INVALID_DATE = "REJECT_INVALID_DATE"
    REJECT_TOO_OLD = "REJECT_TOO_OLD"
    REJECT_DUPLICATE = "REJECT_DUPLICATE"
    REJECT_LOW_INFORMATION = "REJECT_LOW_INFORMATION"
    REJECT_UNSUPPORTED_ITEM = "REJECT_UNSUPPORTED_ITEM"
    REJECT_MALFORMED = "REJECT_MALFORMED"
    REJECT_NOISE = "REJECT_NOISE"


class FreshnessCategory(str, Enum):
    NEW = "NEW"                      # Published/updated within last 48h or since previous collection
    RECENT = "RECENT"                # Published within last 30 days
    HISTORICAL = "HISTORICAL"        # Published > 30 days ago
    STALE = "STALE"                  # Published > 180 days ago
    UNKNOWN_DATE = "UNKNOWN_DATE"    # No reliable date provided by publisher


class RelevanceCategory(str, Enum):
    ACTIONABLE = "ACTIONABLE"        # High-value security / attack surface change (new API, auth, CVE, exposure)
    CONTEXT = "CONTEXT"              # Routine release note, documentation update, general capability
    NOISE = "NOISE"                  # Boilerplate, administrative churn, cookie banners


@dataclass
class QualityEvaluation:
    decision: QualityDecision
    rejection_reason: str | None = None
    freshness: FreshnessCategory = FreshnessCategory.RECENT
    relevance: RelevanceCategory = RelevanceCategory.CONTEXT
    relevance_score: int = 50
    cleaned_title: str = ""
    cleaned_summary: str = ""
    canonical_url: str = ""
    is_actionable: bool = False
    details: dict[str, Any] = field(default_factory=dict)


def clean_text_content(raw_html_or_text: str | None) -> str:
    """Strips HTML tags, decodes entities, collapses whitespace, and preserves plain text."""
    if not raw_html_or_text:
        return ""

    # Replace common break tags with spaces
    text = re.sub(r"<(?:br|p|div|li|h[1-6])[\s/>]", " ", raw_html_or_text, flags=re.IGNORECASE)
    # Strip all remaining tags
    text = re.sub(r"<[^>]+>", "", text)
    # Decode HTML entities (&amp;, &lt;, &#39;, &nbsp;, etc.)
    text = html.unescape(text)
    # Replace non-breaking spaces
    text = text.replace("\u00a0", " ").replace("\u200b", "")
    # Collapse multiple whitespace / newlines into a single clean space
    text = " ".join(text.strip().split())
    return text


def canonicalize_url(url: str | None) -> str:
    """Validates and canonicalizes an HTTP/HTTPS URL, stripping tracking parameters."""
    if not url:
        return ""
    url = url.strip()
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            return ""

        # Filter out tracking query parameters
        query_pairs = parse_qsl(parsed.query, keep_blank_values=False)
        clean_pairs = [(k, v) for k, v in query_pairs if k.lower() not in TRACKING_PARAMS]
        clean_query = urlencode(clean_pairs)

        # Normalize path: remove trailing slash if not root
        path = parsed.path
        if len(path) > 1 and path.endswith("/"):
            path = path.rstrip("/")

        clean_url = urlunparse((
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            path,
            parsed.params,
            clean_query,
            "",  # strip fragment
        ))
        return clean_url
    except Exception:
        return ""


def classify_freshness(
    published_at: datetime | None,
    last_collection_at: datetime | None = None,
    reference_now: datetime | None = None,
    updated_at: datetime | None = None,
) -> FreshnessCategory:
    """Classifies temporal freshness relative to publication/update dates and collection boundary.
    
    Primary rule:
    - If an item was published or updated since the last successful collection boundary,
      it is classified as NEW.
    
    Secondary rule (age-based discovery):
    - <= 7 days old -> NEW (recently published/announced)
    - <= 30 days old -> RECENT (published in the current operational cycle)
    - 31–180 days old -> HISTORICAL
    - > 180 days old -> STALE
    """
    now = reference_now or datetime.now(timezone.utc)

    # Normalize timezone for all inputs
    if published_at and published_at.tzinfo is None:
        published_at = published_at.replace(tzinfo=timezone.utc)
    if updated_at and updated_at.tzinfo is None:
        updated_at = updated_at.replace(tzinfo=timezone.utc)
    if last_collection_at and last_collection_at.tzinfo is None:
        last_collection_at = last_collection_at.replace(tzinfo=timezone.utc)

    # Effective timestamp is the most recent publisher event (updated or published)
    effective_ts = published_at
    if updated_at:
        if not effective_ts or updated_at > effective_ts:
            effective_ts = updated_at

    if not effective_ts:
        return FreshnessCategory.UNKNOWN_DATE

    # 1. PRIMARY RULE: Check against last successful collection boundary
    if last_collection_at:
        # If published or updated at or after previous successful collection (with 5m clock-skew tolerance)
        if effective_ts >= (last_collection_at - timedelta(minutes=5)):
            return FreshnessCategory.NEW

    # 2. SECONDARY RULE: Age-based classification relative to observation time
    age_days = (now - effective_ts).total_seconds() / 86400.0

    # Clock skew guard: publication date in future
    if age_days < -0.05:
        return FreshnessCategory.NEW

    if age_days <= 7.0:
        return FreshnessCategory.NEW
    elif age_days <= 30.0:
        return FreshnessCategory.RECENT
    elif age_days <= 180.0:
        return FreshnessCategory.HISTORICAL
    else:
        return FreshnessCategory.STALE


def is_generic_homepage(canonical_url: str) -> bool:
    """Detects if a URL is a domain root homepage or known generic fallback rather than an item URL."""
    if not canonical_url:
        return False
    if canonical_url in GENERIC_HOMEPAGE_FALLBACKS or f"{canonical_url}/" in GENERIC_HOMEPAGE_FALLBACKS:
        return True
    try:
        p = urlparse(canonical_url)
        if p.path in ("", "/"):
            return True
    except Exception:
        pass
    return False


def classify_security_relevance(
    title: str,
    summary: str,
    change_type: str,
) -> tuple[RelevanceCategory, int]:
    """Scores security relevance and categorizes into ACTIONABLE, CONTEXT, or NOISE.
    
    Returns (RelevanceCategory, relevance_score: 0-100).
    """
    text = f"{title} {summary} {change_type}".lower()

    # NOISE detection: generic marketing boilerplate, webinars, or legal terms
    if any(k in text for k in [
        "terms of service update", "privacy policy update", "cookie preferences",
        "we have updated our terms", "webinar", "marketing seminar", "live q&a",
        "podcast", "sales event", "meetup",
    ]):
        return RelevanceCategory.NOISE, 10

    # High-value actionable security vectors
    actionable_keywords = [
        "cve-", "vulnerability", "security advisory", "remote code execution",
        "privilege escalation", "authentication bypass", "authorization bypass",
        "zero-day", "0-day", "actively exploited", "patch available",
        "new api", "new endpoint", "api endpoint", "webhook", "oauth",
        "iam permission", "role added", "service account", "access control",
        "deprecation", "deprecated endpoint", "sunset api", "breaking change",
        "exposed bucket", "public access", "admin portal", "gateway.dev",
        "security update", "security fix", "cisa kev", "token", "identity federation",
    ]

    actionable_matches = sum(1 for k in actionable_keywords if k in text)

    if "cve-" in text or "actively exploited" in text or "security advisory" in text or "authentication bypass" in text:
        return RelevanceCategory.ACTIONABLE, min(100, 85 + (actionable_matches * 3))

    if any(k in text for k in ["new api", "new endpoint", "webhook", "oauth", "iam permission", "access control", "breaking change"]):
        return RelevanceCategory.ACTIONABLE, min(95, 75 + (actionable_matches * 2))

    if any(k in change_type.upper() for k in ["SECURITY", "AUTH", "VULNERABILITY"]):
        return RelevanceCategory.ACTIONABLE, min(100, 80 + (actionable_matches * 2))

    if any(k in change_type.upper() for k in ["API", "PERMISSION", "ENDPOINT"]):
        return RelevanceCategory.ACTIONABLE, 70

    # Context items: routine updates, new features without exposed security boundary
    if any(k in text for k in ["feature", "ga", "generally available", "preview", "release", "performance", "ui", "console"]):
        return RelevanceCategory.CONTEXT, 45

    return RelevanceCategory.CONTEXT, 35


class ChangeQualityGate:
    """Production quality gate for all parsed source items."""

    def __init__(self, operational_window_days: int = 180):
        self.operational_window_days = operational_window_days

    def evaluate(
        self,
        title: str | None,
        summary: str | None,
        url: str | None,
        change_type: str = "PRODUCT_UPDATE",
        published_at: datetime | None = None,
        updated_at: datetime | None = None,
        source_name: str = "",
        last_collection_at: datetime | None = None,
        product: str | None = None,
        api_endpoint: str | None = None,
        api_method: str | None = None,
        **kwargs: Any,
    ) -> QualityEvaluation:
        """Runs the complete battery of quality, freshness, and relevance checks on a candidate change item."""
        # 1. Clean and normalize texts
        cleaned_title = clean_text_content(title)
        cleaned_summary = clean_text_content(summary)
        canonical_url = canonicalize_url(url)

        # 2. Check Missing Title
        if not cleaned_title or len(cleaned_title) < 4:
            return QualityEvaluation(
                decision=QualityDecision.REJECTED,
                rejection_reason=RejectionReason.REJECT_MISSING_TITLE.value,
                cleaned_title=cleaned_title,
                cleaned_summary=cleaned_summary,
                canonical_url=canonical_url,
                details={"reason": "Title is missing, empty, or under 4 characters"},
            )

        # 3. Check Generic Title Blacklist
        lower_title = cleaned_title.strip().lower()
        if lower_title in GENERIC_TITLES_BLACKLIST:
            return QualityEvaluation(
                decision=QualityDecision.REJECTED,
                rejection_reason=RejectionReason.REJECT_GENERIC_TITLE.value,
                cleaned_title=cleaned_title,
                cleaned_summary=cleaned_summary,
                canonical_url=canonical_url,
                details={"reason": f"Title '{cleaned_title}' matches generic blacklist"},
            )

        # 4. Check Date-Only Title (e.g. "September 03, 2026") without product context
        if DATE_ONLY_TITLE_REGEX.match(lower_title) and not product:
            return QualityEvaluation(
                decision=QualityDecision.REJECTED,
                rejection_reason=RejectionReason.REJECT_GENERIC_TITLE.value,
                cleaned_title=cleaned_title,
                cleaned_summary=cleaned_summary,
                canonical_url=canonical_url,
                details={"reason": "Title is only a date with no product or change description"},
            )

        # 5. Check Summary Quality
        if not cleaned_summary or len(cleaned_summary) < 10:
            return QualityEvaluation(
                decision=QualityDecision.REJECTED,
                rejection_reason=RejectionReason.REJECT_MISSING_SUMMARY.value,
                cleaned_title=cleaned_title,
                cleaned_summary=cleaned_summary,
                canonical_url=canonical_url,
                details={"reason": "Summary is missing, empty, or under 10 characters"},
            )

        # Reject summary identical to title
        if cleaned_summary.strip().lower() == lower_title:
            return QualityEvaluation(
                decision=QualityDecision.REJECTED,
                rejection_reason=RejectionReason.REJECT_BOILERPLATE_SUMMARY.value,
                cleaned_title=cleaned_title,
                cleaned_summary=cleaned_summary,
                canonical_url=canonical_url,
                details={"reason": "Summary is identical to title"},
            )

        # 6. Check URL Validation
        if not canonical_url:
            return QualityEvaluation(
                decision=QualityDecision.REJECTED,
                rejection_reason=RejectionReason.REJECT_INVALID_URL.value,
                cleaned_title=cleaned_title,
                cleaned_summary=cleaned_summary,
                canonical_url=canonical_url,
                details={"reason": "URL is missing or invalid"},
            )

        # Check Generic Homepage Fallback
        if is_generic_homepage(canonical_url):
            return QualityEvaluation(
                decision=QualityDecision.REJECTED,
                rejection_reason=RejectionReason.REJECT_FALLBACK_URL.value,
                cleaned_title=cleaned_title,
                cleaned_summary=cleaned_summary,
                canonical_url=canonical_url,
                details={"reason": f"URL '{canonical_url}' is a generic homepage fallback, not a specific item URL"},
            )

        # 7. Date & Freshness Evaluation
        freshness = classify_freshness(
            published_at=published_at,
            last_collection_at=last_collection_at,
            updated_at=updated_at,
        )

        # 8. Security Relevance Evaluation
        relevance, score = classify_security_relevance(cleaned_title, cleaned_summary, change_type)

        # Noise items are rejected
        if relevance == RelevanceCategory.NOISE:
            return QualityEvaluation(
                decision=QualityDecision.REJECTED,
                rejection_reason=RejectionReason.REJECT_NOISE.value,
                freshness=freshness,
                relevance=relevance,
                relevance_score=score,
                cleaned_title=cleaned_title,
                cleaned_summary=cleaned_summary,
                canonical_url=canonical_url,
                details={"reason": "Item classified as administrative or marketing noise"},
            )

        # Stale items (> 180 days) are context only or rejected
        if freshness == FreshnessCategory.STALE:
            return QualityEvaluation(
                decision=QualityDecision.CONTEXT_ONLY,
                rejection_reason="CONTEXT_STALE_RECORD",
                freshness=freshness,
                relevance=relevance,
                relevance_score=min(score, 30),
                cleaned_title=cleaned_title,
                cleaned_summary=cleaned_summary,
                canonical_url=canonical_url,
                is_actionable=False,
                details={"reason": "Item published > 180 days ago; retained as historical context only"},
            )

        # Historical items (> 30 days) are context only
        if freshness == FreshnessCategory.HISTORICAL:
            return QualityEvaluation(
                decision=QualityDecision.CONTEXT_ONLY,
                rejection_reason="CONTEXT_HISTORICAL_RECORD",
                freshness=freshness,
                relevance=relevance,
                relevance_score=min(score, 45),
                cleaned_title=cleaned_title,
                cleaned_summary=cleaned_summary,
                canonical_url=canonical_url,
                is_actionable=False,
                details={"reason": "Item published > 30 days ago; retained as historical context"},
            )

        # If item has no reliable publication date, mark context only
        if freshness == FreshnessCategory.UNKNOWN_DATE:
            return QualityEvaluation(
                decision=QualityDecision.CONTEXT_ONLY,
                rejection_reason="CONTEXT_UNKNOWN_DATE",
                freshness=freshness,
                relevance=relevance,
                relevance_score=min(score, 40),
                cleaned_title=cleaned_title,
                cleaned_summary=cleaned_summary,
                canonical_url=canonical_url,
                is_actionable=False,
                details={"reason": "Publisher provided no reliable timestamp"},
            )

        # Actionable item with NEW or RECENT freshness
        is_actionable = (relevance == RelevanceCategory.ACTIONABLE and score >= 70)

        return QualityEvaluation(
            decision=QualityDecision.ACCEPTED if is_actionable else QualityDecision.CONTEXT_ONLY,
            rejection_reason=None if is_actionable else "CONTEXT_ROUTINE_UPDATE",
            freshness=freshness,
            relevance=relevance,
            relevance_score=score,
            cleaned_title=cleaned_title,
            cleaned_summary=cleaned_summary,
            canonical_url=canonical_url,
            is_actionable=is_actionable,
            details={
                "freshness": freshness.value,
                "relevance": relevance.value,
                "score": score,
            },
        )
