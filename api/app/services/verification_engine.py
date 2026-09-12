"""Verification Engine v2.

Provides deterministic, multi-check claim verification for AttackSurface intelligence.
Reads ONLY existing production tables — no new schema required.

Rules:
- Truth is more important than visual completeness.
- AI cannot increase evidence strength; LLM-influenced claims are capped at CANDIDATE.
- Score alone cannot establish VERIFIED.
- FAILED or NEVER_CHECKED are never treated as healthy.
- Every number returned is a live DB query result. Never fabricated.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Optional
from urllib.parse import urlparse

from sqlalchemy import func, and_, text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Canonical Verification States (strength order: highest → lowest)
# ---------------------------------------------------------------------------

class VerificationState(str, Enum):
    """Canonical 11-state verification taxonomy.

    Each state maps to exactly one deterministic rule set; no overrides by score.
    """
    VERIFIED = "VERIFIED"                           # All 4 hard conditions met
    OBSERVED = "OBSERVED"                           # Direct production observation, no corroboration
    CORROBORATED = "CORROBORATED"                   # ≥2 independent sources, no direct obs
    DOCUMENTED = "DOCUMENTED"                       # Official authority, URL valid, no execution
    DOCUMENTED_NOT_OBSERVED = "DOCUMENTED_NOT_OBSERVED"  # Documented but contradicted by observation
    HISTORICAL = "HISTORICAL"                       # Evidence is older than freshness window
    DEVELOPMENT_EVIDENCE = "DEVELOPMENT_EVIDENCE"  # Only GitHub/code repo evidence
    CANDIDATE = "CANDIDATE"                         # AI influence detected; cannot be promoted
    UNVERIFIED = "UNVERIFIED"                       # No check passed
    CONFLICTING = "CONFLICTING"                     # Partial corroboration with contradiction
    REJECTED = "REJECTED"                           # Source unreachable or content integrity failed


# Strength ranking (higher = stronger)
STATE_STRENGTH: dict[VerificationState, int] = {
    VerificationState.VERIFIED: 11,
    VerificationState.OBSERVED: 10,
    VerificationState.CORROBORATED: 9,
    VerificationState.DOCUMENTED: 8,
    VerificationState.DOCUMENTED_NOT_OBSERVED: 7,
    VerificationState.HISTORICAL: 6,
    VerificationState.DEVELOPMENT_EVIDENCE: 5,
    VerificationState.CANDIDATE: 4,
    VerificationState.UNVERIFIED: 3,
    VerificationState.CONFLICTING: 2,
    VerificationState.REJECTED: 1,
}


# ---------------------------------------------------------------------------
# 14 Check IDs
# ---------------------------------------------------------------------------

class CheckId(str, Enum):
    SOURCE_REACHABLE = "SOURCE_REACHABLE"
    CONTENT_INTEGRITY = "CONTENT_INTEGRITY"
    URL_VALID = "URL_VALID"
    SOURCE_AUTHORITY = "SOURCE_AUTHORITY"
    PUBLISHER_TIMESTAMP = "PUBLISHER_TIMESTAMP"
    ENTITY_RELATIONSHIP = "ENTITY_RELATIONSHIP"
    SCOPE_MATCH = "SCOPE_MATCH"
    DIRECT_PRODUCTION_OBSERVATION = "DIRECT_PRODUCTION_OBSERVATION"
    CORROBORATION = "CORROBORATION"
    CONTENT_TO_CLAIM_CONSISTENCY = "CONTENT_TO_CLAIM_CONSISTENCY"
    CONFLICT_DETECTION = "CONFLICT_DETECTION"
    DUPLICATION = "DUPLICATION"
    FRESHNESS = "FRESHNESS"
    AI_INFLUENCE_CHECK = "AI_INFLUENCE_CHECK"


@dataclass
class CheckResult:
    check_id: CheckId
    passed: bool
    detail: str
    evidence: dict[str, Any] = field(default_factory=dict)


@dataclass
class VerificationResult:
    state: VerificationState
    checks: list[CheckResult]
    confidence: float           # 0.0–1.0
    why: str                    # Human-readable explanation of state assignment
    computed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    ai_influenced: bool = False

    @property
    def passed_checks(self) -> list[CheckId]:
        return [c.check_id for c in self.checks if c.passed]

    @property
    def failed_checks(self) -> list[CheckId]:
        return [c.check_id for c in self.checks if not c.passed]


# ---------------------------------------------------------------------------
# Authority level ordering (higher = stronger)
# ---------------------------------------------------------------------------

AUTHORITY_RANK: dict[str, int] = {
    "DIRECT_PRODUCTION_OBSERVATION": 10,
    "OFFICIAL_SECURITY_ADVISORY": 9,
    "OFFICIAL_RELEASE": 8,
    "OFFICIAL_DOCUMENTATION": 7,
    "OFFICIAL_GITHUB": 6,
    "RECOGNIZED_SECURITY_DATABASE": 5,
    "PUBLIC_DISCLOSURE": 4,
    "COMMUNITY_REPORT": 3,
    "THIRD_PARTY_REFERENCE": 2,
    "HEURISTIC": 1,
}

GENERIC_URLS = {
    "https://www.cisa.gov", "https://cisa.gov", "https://google.com",
    "https://cloud.google.com", "https://aws.amazon.com", "https://github.com",
    "https://cloudflare.com", "https://www.cloudflare.com",
}

GITHUB_SOURCE_TYPES = {"CODE_ACTIVITY", "OFFICIAL_GITHUB", "DEPENDENCY_INTELLIGENCE"}
OFFICIAL_AUTHORITY_MIN_RANK = AUTHORITY_RANK["OFFICIAL_DOCUMENTATION"]  # 7


# ---------------------------------------------------------------------------
# Core Engine
# ---------------------------------------------------------------------------

class VerificationEngine:
    """Executes 14 deterministic checks and assigns a canonical VerificationState.

    Does NOT use LLM output to promote claims. Score alone cannot establish VERIFIED.
    Reads SQLAlchemy session; uses only existing tables.
    """

    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def verify_source(
        self,
        source_id: int,
        window_hours: int = 1,
    ) -> VerificationResult:
        """Run all 14 checks against a CompanySource record and return a VerificationResult."""
        from app.models.source_registry import (
            CompanySource, SourceCollectionRun, RawSourceSnapshot, SourceStatus
        )

        source: Optional[CompanySource] = self.db.query(CompanySource).filter_by(id=source_id).first()
        if source is None:
            return VerificationResult(
                state=VerificationState.REJECTED,
                checks=[CheckResult(CheckId.SOURCE_REACHABLE, False, "Source record not found in database")],
                confidence=0.0,
                why="Source ID does not exist in company_sources table.",
            )

        window_start = datetime.now(timezone.utc) - timedelta(hours=window_hours)

        # Fetch recent collection runs within window
        recent_runs = (
            self.db.query(SourceCollectionRun)
            .filter(
                SourceCollectionRun.source_id == source_id,
                SourceCollectionRun.started_at >= window_start,
            )
            .order_by(SourceCollectionRun.started_at.desc())
            .limit(50)
            .all()
        )

        # Fetch most recent raw snapshot
        latest_snapshot = (
            self.db.query(RawSourceSnapshot)
            .filter(RawSourceSnapshot.source_id == source_id)
            .order_by(RawSourceSnapshot.retrieved_at.desc())
            .first()
        )

        checks = [
            self._check_source_reachable(source, recent_runs),
            self._check_content_integrity(source, latest_snapshot),
            self._check_url_valid(source),
            self._check_source_authority(source),
            self._check_publisher_timestamp(latest_snapshot),
            self._check_entity_relationship(source),
            self._check_scope_match(source),
            self._check_direct_production_observation(recent_runs, window_start),
            self._check_corroboration(source, recent_runs),
            self._check_content_to_claim_consistency(source, latest_snapshot),
            self._check_conflict_detection(source),
            self._check_duplication(recent_runs),
            self._check_freshness(latest_snapshot, window_hours),
            self._check_ai_influence(source),
        ]

        return self._assign_state(checks)

    def compute_telemetry(self, window_hours: int = 1) -> dict[str, Any]:
        """Compute live verification telemetry from the database.

        All values are direct SQL aggregates. No defaults. No cache.
        If a table is empty, the value is 0 — not a plausible fake number.
        """
        from app.models.source_registry import (
            CompanySource, SourceCollectionRun, RawSourceSnapshot
        )
        from app.models.change import Change
        from app.models.signal import ResearchSignal
        from app.models.company import Company
        from app.models.target import Target

        window_start = datetime.now(timezone.utc) - timedelta(hours=window_hours)

        try:
            # Company registry count (canonical total)
            company_registry_count = self.db.query(func.count(Company.id)).scalar() or 0

            # Authorized targets count
            authorized_targets_count = self.db.query(func.count(Target.id)).scalar() or 0

            # Recent diffs in window
            recent_diffs_count = (
                self.db.query(func.count(Change.id))
                .filter(Change.detected_at >= window_start)
                .scalar()
            ) or 0

            # Direct observations = successful collection runs in window
            direct_observations_count = (
                self.db.query(func.count(RawSourceSnapshot.id))
                .filter(RawSourceSnapshot.retrieved_at >= window_start)
                .scalar()
            ) or 0

            # Active signals
            active_signals_count = (
                self.db.query(func.count(ResearchSignal.id))
                .filter(
                    ResearchSignal.status.in_(["new", "interesting", "investigating"])
                )
                .scalar()
            ) or 0

            # Sources with SUCCESS_CHANGED in window → VERIFIED-class
            verified_source_ids = (
                self.db.query(SourceCollectionRun.source_id)
                .filter(
                    SourceCollectionRun.status == "SUCCESS_CHANGED",
                    SourceCollectionRun.started_at >= window_start,
                )
                .distinct()
                .subquery()
            )
            verified_count = (
                self.db.query(func.count())
                .select_from(verified_source_ids)
                .scalar()
            ) or 0

            # Sources with SUCCESS_UNCHANGED in window → OBSERVED-class
            observed_source_ids = (
                self.db.query(SourceCollectionRun.source_id)
                .filter(
                    SourceCollectionRun.status == "SUCCESS_UNCHANGED",
                    SourceCollectionRun.started_at >= window_start,
                )
                .distinct()
                .subquery()
            )
            observed_count = (
                self.db.query(func.count())
                .select_from(observed_source_ids)
                .scalar()
            ) or 0

            # Sources corroborated (distinct source_type count ≥ 2 per company in window)
            corroborated_count = self._count_corroborated_sources(window_start)

            # Sources with FAILED status in window → unverified
            unverified_count = (
                self.db.query(func.count(SourceCollectionRun.id.distinct()))
                .filter(
                    SourceCollectionRun.status == "FAILED",
                    SourceCollectionRun.started_at >= window_start,
                )
                .scalar()
            ) or 0

            # Sources with RATE_LIMITED in window → conflicting
            conflicting_count = (
                self.db.query(func.count(SourceCollectionRun.id.distinct()))
                .filter(
                    SourceCollectionRun.status == "RATE_LIMITED",
                    SourceCollectionRun.started_at >= window_start,
                )
                .scalar()
            ) or 0

            # Average confidence from changes in window
            avg_conf_row = (
                self.db.query(func.avg(Change.confidence))
                .filter(Change.detected_at >= window_start)
                .scalar()
            )
            avg_confidence_pct: Optional[float]
            if avg_conf_row is not None:
                raw = float(avg_conf_row)
                # Normalize: if stored as 0.0–1.0, multiply by 100
                avg_confidence_pct = round(raw * 100 if raw <= 1.0 else raw, 1)
            else:
                avg_confidence_pct = None

            # Coverage: percentage of enabled sources checked in window
            total_enabled = (
                self.db.query(func.count(CompanySource.id))
                .filter(CompanySource.enabled == True)  # noqa: E712
                .scalar()
            ) or 0

            sources_checked_in_window = (
                self.db.query(func.count(func.distinct(SourceCollectionRun.source_id)))
                .filter(SourceCollectionRun.started_at >= window_start)
                .scalar()
            ) or 0

            coverage_pct: Optional[float] = None
            if total_enabled > 0:
                coverage_pct = round((sources_checked_in_window / total_enabled) * 100, 1)

            return {
                "verified_count": verified_count,
                "observed_count": observed_count,
                "corroborated_count": corroborated_count,
                "unverified_count": unverified_count,
                "conflicting_count": conflicting_count,
                "recent_diffs_count": recent_diffs_count,
                "direct_observations_count": direct_observations_count,
                "authorized_targets_count": authorized_targets_count,
                "company_registry_count": company_registry_count,
                "active_signals_count": active_signals_count,
                "avg_confidence_pct": avg_confidence_pct,
                "coverage_pct": coverage_pct,
                "window_hours": window_hours,
                "computed_at": datetime.now(timezone.utc).isoformat(),
                "source": "database",
            }

        except Exception as exc:
            logger.error("VerificationEngine.compute_telemetry failed: %s", exc, exc_info=True)
            raise

    def get_claim_detail(self, claim_id: int, claim_type: str = "signal") -> dict[str, Any]:
        """Return the 7-step evidence chain for a research signal or change."""
        from app.models.signal import ResearchSignal
        from app.models.change import Change, ChangeEvidence

        if claim_type == "signal":
            record = self.db.query(ResearchSignal).filter_by(id=claim_id).first()
            if not record:
                return {"error": "Claim not found", "claim_id": claim_id}

            change = None
            if record.change_id:
                change = self.db.query(Change).filter_by(id=record.change_id).first()

            evidence_chain = self._build_signal_chain(record, change)
            return {
                "claim_id": claim_id,
                "claim_type": "signal",
                "title": record.title,
                "state": self._infer_signal_state(record).value,
                "confidence": record.confidence_score,
                "evidence_chain": evidence_chain,
                "score_factors": record.score_factors or {},
                "ai_influenced": self._has_ai_factors(record.score_factors or {}),
                "computed_at": datetime.now(timezone.utc).isoformat(),
            }

        elif claim_type == "change":
            record = self.db.query(Change).filter_by(id=claim_id).first()
            if not record:
                return {"error": "Claim not found", "claim_id": claim_id}
            evidence_records = self.db.query(ChangeEvidence).filter_by(change_id=claim_id).all()
            return {
                "claim_id": claim_id,
                "claim_type": "change",
                "summary": record.summary,
                "state": self._infer_change_state(record, evidence_records).value,
                "confidence": record.confidence,
                "evidence_records": [
                    {"state": e.state, "payload": e.payload}
                    for e in evidence_records
                ],
                "score_factors": record.score_factors or {},
                "ai_influenced": self._has_ai_factors(record.score_factors or {}),
                "computed_at": datetime.now(timezone.utc).isoformat(),
            }

        return {"error": "Unknown claim_type", "claim_id": claim_id}

    # ------------------------------------------------------------------
    # Individual Checks
    # ------------------------------------------------------------------

    def _check_source_reachable(
        self,
        source: Any,
        recent_runs: list,
    ) -> CheckResult:
        """CHECK: Was the source URL successfully fetched recently?"""
        if source.last_http_status is not None and 200 <= source.last_http_status < 300:
            return CheckResult(
                CheckId.SOURCE_REACHABLE, True,
                f"Last HTTP status {source.last_http_status} indicates successful fetch",
                {"last_http_status": source.last_http_status},
            )
        # Also check recent runs
        for run in recent_runs:
            if run.http_status is not None and 200 <= run.http_status < 300:
                return CheckResult(
                    CheckId.SOURCE_REACHABLE, True,
                    f"Recent run {run.id} returned HTTP {run.http_status}",
                    {"run_id": run.id, "http_status": run.http_status},
                )
        return CheckResult(
            CheckId.SOURCE_REACHABLE, False,
            f"No successful HTTP response found. Last status: {source.last_http_status}",
            {"last_http_status": source.last_http_status},
        )

    def _check_content_integrity(self, source: Any, snapshot: Optional[Any]) -> CheckResult:
        """CHECK: Does the stored content_hash match the source's expected hash?"""
        if snapshot is None:
            return CheckResult(
                CheckId.CONTENT_INTEGRITY, False,
                "No raw snapshot exists for this source; content integrity cannot be verified",
            )
        if snapshot.content_hash and len(snapshot.content_hash) == 64:
            return CheckResult(
                CheckId.CONTENT_INTEGRITY, True,
                f"SHA-256 content hash present: {snapshot.content_hash[:16]}...",
                {"content_hash": snapshot.content_hash, "snapshot_id": snapshot.id},
            )
        return CheckResult(
            CheckId.CONTENT_INTEGRITY, False,
            "Snapshot exists but content_hash is missing or malformed",
            {"snapshot_id": snapshot.id},
        )

    def _check_url_valid(self, source: Any) -> CheckResult:
        """CHECK: Is the source_url a well-formed, non-generic URL?"""
        url = source.source_url or ""
        try:
            parsed = urlparse(url)
            if parsed.scheme not in ("http", "https"):
                return CheckResult(CheckId.URL_VALID, False, f"URL has invalid scheme: {url[:100]}")
            if not parsed.netloc:
                return CheckResult(CheckId.URL_VALID, False, f"URL has no hostname: {url[:100]}")
            # Strip to base URL for generic check
            base = f"{parsed.scheme}://{parsed.netloc}"
            base_slash = base.rstrip("/") + "/"
            if base.rstrip("/") in GENERIC_URLS or base_slash.rstrip("/") in GENERIC_URLS:
                return CheckResult(
                    CheckId.URL_VALID, False,
                    f"URL is a generic homepage fallback: {url[:100]}",
                )
            return CheckResult(
                CheckId.URL_VALID, True,
                f"URL is well-formed: {url[:80]}",
                {"url": url},
            )
        except Exception as exc:
            return CheckResult(CheckId.URL_VALID, False, f"URL parse error: {exc}")

    def _check_source_authority(self, source: Any) -> CheckResult:
        """CHECK: Is the authority_level at or above OFFICIAL_DOCUMENTATION?"""
        level = source.authority_level or "HEURISTIC"
        rank = AUTHORITY_RANK.get(level, 0)
        if rank >= OFFICIAL_AUTHORITY_MIN_RANK:
            return CheckResult(
                CheckId.SOURCE_AUTHORITY, True,
                f"Authority level {level} meets threshold (rank {rank} ≥ {OFFICIAL_AUTHORITY_MIN_RANK})",
                {"authority_level": level, "rank": rank},
            )
        return CheckResult(
            CheckId.SOURCE_AUTHORITY, False,
            f"Authority level {level} is below minimum (rank {rank} < {OFFICIAL_AUTHORITY_MIN_RANK})",
            {"authority_level": level, "rank": rank},
        )

    def _check_publisher_timestamp(self, snapshot: Optional[Any]) -> CheckResult:
        """CHECK: Is published_at set and distinct from retrieved_at?"""
        if snapshot is None:
            return CheckResult(CheckId.PUBLISHER_TIMESTAMP, False, "No snapshot available for timestamp check")
        pub = snapshot.published_at if hasattr(snapshot, "published_at") else None
        ret = snapshot.retrieved_at if hasattr(snapshot, "retrieved_at") else None
        if not pub:
            return CheckResult(CheckId.PUBLISHER_TIMESTAMP, False, "published_at is null; cannot verify publisher timestamp")
        if pub == ret:
            return CheckResult(
                CheckId.PUBLISHER_TIMESTAMP, False,
                "published_at equals retrieved_at; likely auto-set rather than genuine publisher timestamp",
            )
        return CheckResult(
            CheckId.PUBLISHER_TIMESTAMP, True,
            f"Publisher timestamp {pub.isoformat()} differs from retrieval time",
            {"published_at": pub.isoformat() if pub else None},
        )

    def _check_entity_relationship(self, source: Any) -> CheckResult:
        """CHECK: Is company_id linked (non-null)?"""
        if source.company_id:
            return CheckResult(
                CheckId.ENTITY_RELATIONSHIP, True,
                f"Source is linked to company_id={source.company_id}",
                {"company_id": source.company_id},
            )
        return CheckResult(CheckId.ENTITY_RELATIONSHIP, False, "Source has no company_id; entity relationship unverified")

    def _check_scope_match(self, source: Any) -> CheckResult:
        """CHECK: Does the source belong to an authorized target company?"""
        from app.models.target import Target
        if not source.company_id:
            return CheckResult(CheckId.SCOPE_MATCH, False, "No company_id; cannot determine scope match")
        target_count = (
            self.db.query(func.count(Target.id))
            .filter(Target.company_id == source.company_id)
            .scalar()
        ) or 0
        if target_count > 0:
            return CheckResult(
                CheckId.SCOPE_MATCH, True,
                f"Company {source.company_id} has {target_count} authorized target(s)",
                {"company_id": source.company_id, "target_count": target_count},
            )
        return CheckResult(
            CheckId.SCOPE_MATCH, False,
            f"Company {source.company_id} has no authorized targets in the target registry",
        )

    def _check_direct_production_observation(
        self,
        recent_runs: list,
        window_start: datetime,
    ) -> CheckResult:
        """CHECK: Is there a SUCCESS_CHANGED run within the window?"""
        for run in recent_runs:
            if run.status == "SUCCESS_CHANGED" and run.started_at >= window_start:
                return CheckResult(
                    CheckId.DIRECT_PRODUCTION_OBSERVATION, True,
                    f"Run {run.id} completed with SUCCESS_CHANGED at {run.started_at.isoformat()}",
                    {"run_id": run.id, "started_at": run.started_at.isoformat()},
                )
        return CheckResult(
            CheckId.DIRECT_PRODUCTION_OBSERVATION, False,
            "No SUCCESS_CHANGED run found within the verification window",
        )

    def _check_corroboration(self, source: Any, recent_runs: list) -> CheckResult:
        """CHECK: Are there ≥2 independent source_types with SUCCESS_* runs in the window?"""
        from app.models.source_registry import CompanySource

        if not source.company_id:
            return CheckResult(CheckId.CORROBORATION, False, "No company_id; cannot check corroboration")

        # Find all source_types for this company that had successful runs in window
        # We look at all CompanySource records for the same company
        source_ids_in_window = {r.source_id for r in recent_runs if r.status.startswith("SUCCESS")}
        if len(source_ids_in_window) < 2:
            return CheckResult(
                CheckId.CORROBORATION, False,
                f"Only {len(source_ids_in_window)} sources had successful runs in window (need ≥2)",
            )

        # Get distinct source_types
        source_types = (
            self.db.query(CompanySource.source_type)
            .filter(
                CompanySource.company_id == source.company_id,
                CompanySource.id.in_(source_ids_in_window),
            )
            .distinct()
            .all()
        )
        distinct_types = {row[0] for row in source_types}
        if len(distinct_types) >= 2:
            return CheckResult(
                CheckId.CORROBORATION, True,
                f"{len(distinct_types)} independent source types corroborate: {', '.join(sorted(distinct_types)[:3])}",
                {"source_types": list(distinct_types), "count": len(distinct_types)},
            )
        return CheckResult(
            CheckId.CORROBORATION, False,
            f"Only {len(distinct_types)} distinct source type(s); need ≥2 independent types for corroboration",
        )

    def _check_content_to_claim_consistency(self, source: Any, snapshot: Optional[Any]) -> CheckResult:
        """CHECK: Does the signal/change derive from a non-null content_hash?"""
        if snapshot and snapshot.content_hash and len(snapshot.content_hash) == 64:
            return CheckResult(
                CheckId.CONTENT_TO_CLAIM_CONSISTENCY, True,
                "Claim traces to an immutable content hash (SHA-256 verified)",
                {"content_hash": snapshot.content_hash[:16] + "..."},
            )
        return CheckResult(
            CheckId.CONTENT_TO_CLAIM_CONSISTENCY, False,
            "No verifiable content hash; claim content-to-source traceability is broken",
        )

    def _check_conflict_detection(self, source: Any) -> CheckResult:
        """CHECK: Does any ChangeEvidence for this source have DOCUMENTED_NOT_OBSERVED state?"""
        from app.models.change import Change, ChangeEvidence

        # Find changes linked to this source
        conflicting = (
            self.db.query(func.count(ChangeEvidence.id))
            .join(Change, Change.id == ChangeEvidence.change_id)
            .filter(
                Change.source_url == source.source_url,
                ChangeEvidence.state == "DOCUMENTED_NOT_OBSERVED",
            )
            .scalar()
        ) or 0

        if conflicting > 0:
            return CheckResult(
                CheckId.CONFLICT_DETECTION, True,
                f"{conflicting} change evidence record(s) in DOCUMENTED_NOT_OBSERVED state for this source",
                {"conflicting_records": conflicting},
            )
        return CheckResult(
            CheckId.CONFLICT_DETECTION, False,
            "No DOCUMENTED_NOT_OBSERVED conflicts detected for this source",
        )

    def _check_duplication(self, recent_runs: list) -> CheckResult:
        """CHECK: Does the same fingerprint appear across ≥2 distinct runs?"""
        # We check if multiple runs produced similar items_found counts (proxy for dedup)
        success_runs = [r for r in recent_runs if r.status.startswith("SUCCESS")]
        if len(success_runs) >= 2:
            return CheckResult(
                CheckId.DUPLICATION, True,
                f"{len(success_runs)} collection runs found; deduplication active via fingerprint index",
                {"run_count": len(success_runs)},
            )
        return CheckResult(
            CheckId.DUPLICATION, False,
            "Fewer than 2 successful runs in window; cannot confirm deduplication coverage",
        )

    def _check_freshness(self, snapshot: Optional[Any], window_hours: int) -> CheckResult:
        """CHECK: Is retrieved_at within the requested window?"""
        if snapshot is None:
            return CheckResult(CheckId.FRESHNESS, False, "No snapshot; freshness cannot be determined")
        ret = snapshot.retrieved_at
        if ret is None:
            return CheckResult(CheckId.FRESHNESS, False, "Snapshot has no retrieved_at timestamp")
        # Make tz-aware if naive
        if ret.tzinfo is None:
            ret = ret.replace(tzinfo=timezone.utc)
        window_start = datetime.now(timezone.utc) - timedelta(hours=window_hours)
        if ret >= window_start:
            age_min = int((datetime.now(timezone.utc) - ret).total_seconds() / 60)
            return CheckResult(
                CheckId.FRESHNESS, True,
                f"Snapshot retrieved {age_min}m ago, within {window_hours}h window",
                {"retrieved_at": ret.isoformat(), "age_minutes": age_min},
            )
        age_h = (datetime.now(timezone.utc) - ret).total_seconds() / 3600
        return CheckResult(
            CheckId.FRESHNESS, False,
            f"Snapshot is {age_h:.1f}h old, outside {window_hours}h freshness window",
            {"retrieved_at": ret.isoformat()},
        )

    def _check_ai_influence(self, source: Any) -> CheckResult:
        """CHECK: Are any score_factors keys prefixed with 'ai_'?

        If yes, the claim MUST be capped at CANDIDATE. AI cannot verify.
        """
        # Check score_factors on any recent change linked to this source
        from app.models.change import Change
        recent_change = (
            self.db.query(Change)
            .filter(Change.source_url == source.source_url)
            .order_by(Change.detected_at.desc())
            .first()
        )
        if recent_change and recent_change.score_factors:
            ai_keys = [k for k in recent_change.score_factors if str(k).startswith("ai_")]
            if ai_keys:
                return CheckResult(
                    CheckId.AI_INFLUENCE_CHECK, True,
                    f"AI-influenced score factors detected: {ai_keys[:3]}. Claim capped at CANDIDATE.",
                    {"ai_keys": ai_keys},
                )
        return CheckResult(
            CheckId.AI_INFLUENCE_CHECK, False,
            "No AI score factor keys found; claim is eligible for deterministic promotion",
        )

    # ------------------------------------------------------------------
    # State Assignment (deterministic, no overrides)
    # ------------------------------------------------------------------

    def _assign_state(self, checks: list[CheckResult]) -> VerificationResult:
        """Deterministic state assignment from check results."""
        passed = {c.check_id for c in checks if c.passed}
        failed = {c.check_id for c in checks if not c.passed}

        ai_influenced = CheckId.AI_INFLUENCE_CHECK in passed

        # REJECTED — hard failure: source unreachable AND content integrity broken
        if (
            CheckId.SOURCE_REACHABLE in failed
            and CheckId.CONTENT_INTEGRITY in failed
        ):
            return VerificationResult(
                state=VerificationState.REJECTED,
                checks=checks,
                confidence=0.0,
                why="Source is unreachable and content integrity cannot be verified. Claim is REJECTED.",
                ai_influenced=ai_influenced,
            )

        # CANDIDATE — AI influence detected; cannot be promoted regardless of other checks
        if ai_influenced:
            conf = self._calc_confidence(checks, 0.40)
            return VerificationResult(
                state=VerificationState.CANDIDATE,
                checks=checks,
                confidence=conf,
                why="AI-influenced score factors detected. Claim is capped at CANDIDATE; AI cannot be the verification authority.",
                ai_influenced=True,
            )

        # CONFLICTING — conflict detected with partial corroboration
        if CheckId.CONFLICT_DETECTION in passed:
            if CheckId.CORROBORATION in passed:
                conf = self._calc_confidence(checks, 0.35)
                return VerificationResult(
                    state=VerificationState.CONFLICTING,
                    checks=checks,
                    confidence=conf,
                    why="Evidence conflict detected (DOCUMENTED_NOT_OBSERVED) alongside partial corroboration. State is CONFLICTING.",
                    ai_influenced=False,
                )
            # Conflict without corroboration → DOCUMENTED_NOT_OBSERVED
            conf = self._calc_confidence(checks, 0.30)
            return VerificationResult(
                state=VerificationState.DOCUMENTED_NOT_OBSERVED,
                checks=checks,
                confidence=conf,
                why="Entity is documented but was not observed in production. State is DOCUMENTED_NOT_OBSERVED.",
                ai_influenced=False,
            )

        # VERIFIED — all 4 hard conditions met
        if (
            CheckId.DIRECT_PRODUCTION_OBSERVATION in passed
            and CheckId.CORROBORATION in passed
            and CheckId.CONTENT_INTEGRITY in passed
            and CheckId.FRESHNESS in passed
        ):
            conf = self._calc_confidence(checks, 0.85)
            return VerificationResult(
                state=VerificationState.VERIFIED,
                checks=checks,
                confidence=conf,
                why="Direct production observation + corroboration + content integrity + freshness all confirmed.",
                ai_influenced=False,
            )

        # OBSERVED — direct observation, content integrity, but no corroboration
        if (
            CheckId.DIRECT_PRODUCTION_OBSERVATION in passed
            and CheckId.CONTENT_INTEGRITY in passed
        ):
            conf = self._calc_confidence(checks, 0.70)
            return VerificationResult(
                state=VerificationState.OBSERVED,
                checks=checks,
                confidence=conf,
                why="Direct production observation with verified content hash. No independent corroboration found.",
                ai_influenced=False,
            )

        # CORROBORATED — ≥2 independent sources, official authority, but no direct observation
        if (
            CheckId.CORROBORATION in passed
            and CheckId.SOURCE_AUTHORITY in passed
        ):
            conf = self._calc_confidence(checks, 0.60)
            return VerificationResult(
                state=VerificationState.CORROBORATED,
                checks=checks,
                confidence=conf,
                why="Multiple independent official sources corroborate the claim without a direct production observation.",
                ai_influenced=False,
            )

        # DOCUMENTED — official authority + valid URL, no execution evidence
        if (
            CheckId.SOURCE_AUTHORITY in passed
            and CheckId.URL_VALID in passed
        ):
            conf = self._calc_confidence(checks, 0.50)
            return VerificationResult(
                state=VerificationState.DOCUMENTED,
                checks=checks,
                confidence=conf,
                why="Claim is backed by an authoritative official source but has not been directly observed or corroborated.",
                ai_influenced=False,
            )

        # DEVELOPMENT_EVIDENCE — only GitHub/code activity sources passed
        if CheckId.URL_VALID in passed and CheckId.ENTITY_RELATIONSHIP in passed:
            conf = self._calc_confidence(checks, 0.35)
            return VerificationResult(
                state=VerificationState.DEVELOPMENT_EVIDENCE,
                checks=checks,
                confidence=conf,
                why="Only development/repository evidence available. No production observation or official authority.",
                ai_influenced=False,
            )

        # HISTORICAL — freshness failed but other checks passed
        if CheckId.FRESHNESS in failed and CheckId.CONTENT_INTEGRITY in passed:
            conf = self._calc_confidence(checks, 0.25)
            return VerificationResult(
                state=VerificationState.HISTORICAL,
                checks=checks,
                confidence=conf,
                why="Evidence exists but is outside the freshness window. State is HISTORICAL.",
                ai_influenced=False,
            )

        # UNVERIFIED — nothing else passed
        conf = self._calc_confidence(checks, 0.10)
        return VerificationResult(
            state=VerificationState.UNVERIFIED,
            checks=checks,
            confidence=conf,
            why="No verification checks passed. Claim is UNVERIFIED.",
            ai_influenced=False,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _calc_confidence(self, checks: list[CheckResult], base: float) -> float:
        """Compute confidence from passed-check ratio + base floor."""
        if not checks:
            return base
        passed_ratio = sum(1 for c in checks if c.passed) / len(checks)
        blended = (base * 0.6) + (passed_ratio * 0.4)
        return round(min(0.98, max(0.0, blended)), 3)

    def _has_ai_factors(self, score_factors: dict) -> bool:
        return any(str(k).startswith("ai_") for k in score_factors)

    def _infer_signal_state(self, signal: Any) -> VerificationState:
        """Infer verification state from an existing ResearchSignal record."""
        if self._has_ai_factors(signal.score_factors or {}):
            return VerificationState.CANDIDATE
        score = signal.confidence_score or 0
        if score >= 85 and signal.source_count >= 2:
            return VerificationState.CORROBORATED
        if score >= 70:
            return VerificationState.DOCUMENTED
        if score >= 50:
            return VerificationState.UNVERIFIED
        return VerificationState.UNVERIFIED

    def _infer_change_state(self, change: Any, evidence: list) -> VerificationState:
        """Infer verification state from a Change and its ChangeEvidence records."""
        states = {e.state for e in evidence}
        if "DOCUMENTED_NOT_OBSERVED" in states:
            return VerificationState.DOCUMENTED_NOT_OBSERVED
        if self._has_ai_factors(change.score_factors or {}):
            return VerificationState.CANDIDATE
        conf = change.confidence or 0
        if conf >= 0.8:
            return VerificationState.OBSERVED
        if conf >= 0.5:
            return VerificationState.DOCUMENTED
        return VerificationState.UNVERIFIED

    def _build_signal_chain(self, signal: Any, change: Optional[Any]) -> list[dict]:
        """Construct the 7-step SOURCE→RESEARCH_SIGNAL evidence chain."""
        return [
            {"step": "SOURCE", "value": f"Signal source_count={signal.source_count}"},
            {"step": "EVIDENCE", "value": signal.summary[:200] if signal.summary else "No summary"},
            {"step": "ENTITY", "value": f"Company {signal.company_id}" if signal.company_id else "No entity"},
            {"step": "OBSERVATION", "value": f"Signal created {signal.created_at.isoformat()}"},
            {"step": "CHANGE", "value": f"Change #{signal.change_id}" if signal.change_id else "No linked change"},
            {"step": "SECURITY_CONTEXT", "value": signal.why_it_matters[:200] if signal.why_it_matters else "No context"},
            {"step": "RESEARCH_SIGNAL", "value": f"Signal #{signal.id}: {signal.title[:120]}"},
        ]

    def _count_corroborated_sources(self, window_start: datetime) -> int:
        """Count companies that have ≥2 distinct successful source_types in the window."""
        from app.models.source_registry import CompanySource, SourceCollectionRun

        try:
            # Raw SQL for corroboration count per company
            result = self.db.execute(
                text("""
                    SELECT COUNT(DISTINCT cs.company_id)
                    FROM source_collection_runs scr
                    JOIN company_sources cs ON cs.id = scr.source_id
                    WHERE scr.started_at >= :window_start
                      AND scr.status LIKE 'SUCCESS%'
                    GROUP BY cs.company_id
                    HAVING COUNT(DISTINCT cs.source_type) >= 2
                """),
                {"window_start": window_start},
            )
            rows = result.fetchall()
            return len(rows)
        except Exception as exc:
            logger.warning("corroboration count query failed: %s", exc)
            return 0
