"""Deterministic verification layer for internet-derived intelligence.

The verification engine is deliberately separate from AI scoring. It never treats an
LLM output, a title match, or a single weak source as proof. It records the exact
checks that were satisfied and returns a conservative claim state that downstream
UIs can render without inventing confidence.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone, timedelta
from typing import Any
from urllib.parse import urlparse
import hashlib
import re


VERIFIED_SOURCE_TYPES = {
    "OFFICIAL_PRODUCT_CHANGE",
    "OFFICIAL_RELEASE",
    "OFFICIAL_API_CHANGELOG",
    "OFFICIAL_DEVELOPER_DOCS",
    "OFFICIAL_SECURITY_ADVISORY",
    "OFFICIAL_BLOG",
    "OFFICIAL_GITHUB",
    "OFFICIAL_STATUS",
    "OFFICIAL_ROADMAP",
    "OFFICIAL_APP_STORE",
    "OFFICIAL_PACKAGE_REGISTRY",
    "DIRECT_PRODUCTION_OBSERVATION",
    "VULNERABILITY_INTELLIGENCE",
}

WEAK_SOURCE_TYPES = {
    "COMMUNITY",
    "SOCIAL_SIGNAL",
    "THIRD_PARTY_ENRICHMENT",
    "COMMUNITY_REPORT",
    "HEURISTIC",
}

BLOCKED_PLACEHOLDERS = {
    "unknown",
    "n/a",
    "na",
    "none",
    "null",
    "undefined",
    "untitled",
    "unnamed",
}

CVE_RE = re.compile(r"\bCVE-\d{4}-\d{4,7}\b", re.IGNORECASE)


@dataclass(frozen=True)
class VerificationCheck:
    name: str
    passed: bool
    detail: str
    weight: float


@dataclass(frozen=True)
class VerificationResult:
    state: str
    score: float
    checks: list[VerificationCheck]
    blockers: list[str]
    evidence_class: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "state": self.state,
            "score": self.score,
            "evidence_class": self.evidence_class,
            "blockers": self.blockers,
            "checks": [asdict(c) for c in self.checks],
            "verified_at": datetime.now(timezone.utc).isoformat(),
            "engine_version": "2.0.0",
        }


class VerificationEngine:
    """Conservative verification gate for records created from internet sources."""

    VERSION = "2.0.0"

    def evaluate(
        self,
        *,
        title: str | None,
        summary: str | None,
        item_url: str | None,
        source_url: str | None,
        source_type: str | None,
        authority_level: str | None,
        source_content_hash: str | None,
        published_at: datetime | None = None,
        updated_at: datetime | None = None,
        ai_generated: bool = False,
        direct_production_observed: bool = False,
        corroborating_source_count: int = 0,
        entity_relationship_verified: bool = False,
    ) -> VerificationResult:
        checks: list[VerificationCheck] = []
        blockers: list[str] = []

        def add(name: str, passed: bool, detail: str, weight: float) -> None:
            checks.append(VerificationCheck(name=name, passed=passed, detail=detail, weight=weight))

        clean_title = (title or "").strip()
        clean_summary = (summary or "").strip()
        source_type_u = (source_type or "").upper()
        authority_u = (authority_level or "").upper()

        item_host = self._host(item_url)
        source_host = self._host(source_url)

        add("TITLE_PRESENT", bool(clean_title) and clean_title.lower() not in BLOCKED_PLACEHOLDERS,
            "Specific publisher-supplied title is present.", 0.10)
        add("SUMMARY_PRESENT", len(clean_summary) >= 10 and clean_summary.lower() not in BLOCKED_PLACEHOLDERS,
            "Specific publisher-supplied summary is present.", 0.08)
        add("ITEM_URL_VALID", bool(item_host),
            "Item URL is an absolute HTTP(S) URL." if item_host else "Item URL is missing or invalid.", 0.12)
        add("SOURCE_URL_VALID", bool(source_host),
            "Source URL is an absolute HTTP(S) URL." if source_host else "Source URL is missing or invalid.", 0.10)
        add("SNAPSHOT_INTEGRITY", bool(source_content_hash) and bool(re.fullmatch(r"[0-9a-fA-F]{64}", source_content_hash or "")),
            "Upstream body has a SHA-256 integrity hash." if source_content_hash else "No upstream content hash is available.", 0.15)
        add("NON_HEURISTIC_SOURCE", source_type_u not in WEAK_SOURCE_TYPES and authority_u not in WEAK_SOURCE_TYPES,
            "Source is not classified as community/heuristic-only." if source_type_u not in WEAK_SOURCE_TYPES and authority_u not in WEAK_SOURCE_TYPES else "Source is weak or heuristic and cannot establish a verified claim.", 0.15)
        add("ENTITY_RELATIONSHIP", entity_relationship_verified,
            "Source-to-company/entity relationship is explicitly verified." if entity_relationship_verified else "Entity relationship is not explicitly verified.", 0.12)
        add("PUBLISHED_TIME_VALID", self._valid_publisher_time(published_at, updated_at),
            "Publisher timestamp is present and within a reasonable clock-skew window." if self._valid_publisher_time(published_at, updated_at) else "Publisher timestamp is absent or implausibly in the future.", 0.08)
        add("NOT_AI_ONLY", not ai_generated,
            "Record is not being represented as verified solely because an AI produced it." if not ai_generated else "AI-generated material is never treated as proof by itself.", 0.10)
        add("CORROBORATION", corroborating_source_count >= 1 or direct_production_observed,
            "Independent corroboration or direct production observation exists." if (corroborating_source_count >= 1 or direct_production_observed) else "No independent corroboration or direct observation is recorded.", 0.20)

        # Security identifiers get an extra deterministic sanity check.
        cves = sorted(set(m.group(0).upper() for m in CVE_RE.finditer(f"{clean_title} {clean_summary}")))
        if cves:
            add("CVE_FORMAT", all(bool(re.fullmatch(r"CVE-\d{4}-\d{4,7}", c)) for c in cves),
                f"Parsed CVE identifier(s): {', '.join(cves)}.", 0.05)

        score = sum(c.weight for c in checks if c.passed)
        score = round(min(score, 1.0), 3)

        if not clean_title or not clean_summary or not item_host or not source_host or not source_content_hash:
            blockers.append("missing_core_provenance")
        if source_type_u in WEAK_SOURCE_TYPES or authority_u in WEAK_SOURCE_TYPES:
            blockers.append("weak_source")
        if ai_generated:
            blockers.append("ai_only")
        if not entity_relationship_verified:
            blockers.append("entity_relationship_unverified")
        if not self._valid_publisher_time(published_at, updated_at):
            blockers.append("publisher_time_unverified")

        if direct_production_observed:
            state = "CONFIRMED" if not blockers or (blockers == ["entity_relationship_unverified"] and item_host == source_host) else "OBSERVED"
            evidence_class = "DIRECT_PRODUCTION_OBSERVATION"
        elif corroborating_source_count >= 1 and not blockers:
            state = "CORROBORATED"
            evidence_class = "MULTI_SOURCE"
        elif source_type_u in VERIFIED_SOURCE_TYPES and authority_u in {
            "OFFICIAL_SECURITY_ADVISORY",
            "OFFICIAL_RELEASE",
            "OFFICIAL_DOCUMENTATION",
            "OFFICIAL_GITHUB",
            "RECOGNIZED_SECURITY_DATABASE",
        } and not any(b in blockers for b in ("missing_core_provenance", "ai_only", "weak_source")):
            state = "DOCUMENTED"
            evidence_class = "AUTHORITATIVE_PUBLISHER"
        else:
            state = "UNVERIFIED"
            evidence_class = "SINGLE_SOURCE_OR_WEAK"

        return VerificationResult(
            state=state,
            score=score,
            checks=checks,
            blockers=sorted(set(blockers)),
            evidence_class=evidence_class,
        )

    @staticmethod
    def _host(url: str | None) -> str:
        if not url:
            return ""
        try:
            parsed = urlparse(url.strip())
            if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
                return ""
            return parsed.hostname.lower() if parsed.hostname else ""
        except Exception:
            return ""

    @staticmethod
    def _valid_publisher_time(published_at: datetime | None, updated_at: datetime | None) -> bool:
        ts = updated_at or published_at
        if not ts:
            return False
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        # A publisher timestamp more than 6 hours in the future is not trusted.
        return ts <= datetime.now(timezone.utc) + timedelta(hours=6)

    @staticmethod
    def body_sha256(body: str | bytes) -> str:
        raw = body.encode("utf-8") if isinstance(body, str) else body
        return hashlib.sha256(raw).hexdigest()


__all__ = ["VerificationEngine", "VerificationResult", "VerificationCheck"]
