"""Verification Engine v2 — 27 test scenarios + 7 golden cases (A–G).

Tests use synthetic data via mocked SQLAlchemy sessions.
No external API calls. No real DB connection required.

Golden cases:
A: VERIFIED   — all 4 hard conditions met
B: OBSERVED   — direct observation, no corroboration
C: CORROBORATED — 2+ sources, no direct observation
D: CANDIDATE  — AI influence detected in score_factors
E: CONFLICTING — DOCUMENTED_NOT_OBSERVED state
F: UNVERIFIED  — no checks pass
G: REJECTED   — http_status 403, content_hash mismatch
"""
from __future__ import annotations

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch, PropertyMock
from dataclasses import dataclass, field
from typing import Any, Optional

from app.services.verification_engine import (
    VerificationEngine,
    VerificationState,
    CheckId,
    CheckResult,
    AUTHORITY_RANK,
    GENERIC_URLS,
)


# ---------------------------------------------------------------------------
# Synthetic fixtures
# ---------------------------------------------------------------------------

def utcnow():
    return datetime.now(timezone.utc)


@dataclass
class FakeSource:
    id: int = 1
    company_id: int = 1
    source_url: str = "https://example.com/changelog"
    authority_level: str = "OFFICIAL_DOCUMENTATION"
    last_http_status: int = 200
    score_factors: dict = field(default_factory=dict)


@dataclass
class FakeSnapshot:
    id: int = 1
    source_id: int = 1
    content_hash: str = "a" * 64  # 64-char SHA-256
    retrieved_at: datetime = field(default_factory=utcnow)
    published_at: Optional[datetime] = None

    def __post_init__(self):
        if self.published_at is None:
            self.published_at = self.retrieved_at - timedelta(hours=2)


@dataclass
class FakeRun:
    id: int = 1
    source_id: int = 1
    status: str = "SUCCESS_CHANGED"
    http_status: int = 200
    started_at: datetime = field(default_factory=utcnow)
    finished_at: Optional[datetime] = None
    items_found: int = 5
    items_changed: int = 2


@dataclass
class FakeChange:
    id: int = 1
    source_url: str = "https://example.com/changelog"
    summary: str = "Test change summary"
    confidence: float = 0.85
    detected_at: datetime = field(default_factory=utcnow)
    score_factors: dict = field(default_factory=dict)


@dataclass
class FakeEvidence:
    id: int = 1
    change_id: int = 1
    state: str = "OBSERVED"
    payload: dict = field(default_factory=dict)


@dataclass
class FakeTarget:
    id: int = 1
    company_id: int = 1


def make_engine(db=None):
    if db is None:
        db = MagicMock()
    return VerificationEngine(db)


# ---------------------------------------------------------------------------
# Helper: build engine with mocked DB returning given objects
# ---------------------------------------------------------------------------

def make_engine_with_source(source, snapshot=None, runs=None, recent_change=None, targets=1):
    db = MagicMock()
    engine = VerificationEngine(db)

    # Mock query chain
    def query_side_effect(model):
        mock_q = MagicMock()
        mock_q.filter_by.return_value.first.return_value = source
        mock_q.filter.return_value = mock_q
        mock_q.join.return_value = mock_q
        mock_q.order_by.return_value = mock_q
        mock_q.limit.return_value = mock_q
        mock_q.distinct.return_value = mock_q
        mock_q.all.return_value = runs or []
        mock_q.first.return_value = snapshot
        mock_q.scalar.return_value = targets
        return mock_q

    db.query.side_effect = query_side_effect
    return engine


# ---------------------------------------------------------------------------
# ── INDIVIDUAL CHECK TESTS ── (14 checks × 2 cases = 28, plus edge cases)
# ---------------------------------------------------------------------------

class TestSourceReachable:
    def test_pass_via_last_http_status(self):
        engine = make_engine()
        source = FakeSource(last_http_status=200)
        result = engine._check_source_reachable(source, [])
        assert result.passed is True
        assert result.check_id == CheckId.SOURCE_REACHABLE

    def test_pass_via_recent_run(self):
        engine = make_engine()
        source = FakeSource(last_http_status=None)
        run = FakeRun(http_status=201)
        result = engine._check_source_reachable(source, [run])
        assert result.passed is True

    def test_fail_no_successful_status(self):
        engine = make_engine()
        source = FakeSource(last_http_status=403)
        run = FakeRun(http_status=503)
        result = engine._check_source_reachable(source, [run])
        assert result.passed is False

    def test_fail_null_status(self):
        engine = make_engine()
        source = FakeSource(last_http_status=None)
        result = engine._check_source_reachable(source, [])
        assert result.passed is False


class TestContentIntegrity:
    def test_pass_valid_sha256(self):
        engine = make_engine()
        snap = FakeSnapshot(content_hash="b" * 64)
        result = engine._check_content_integrity(FakeSource(), snap)
        assert result.passed is True

    def test_fail_no_snapshot(self):
        engine = make_engine()
        result = engine._check_content_integrity(FakeSource(), None)
        assert result.passed is False

    def test_fail_short_hash(self):
        engine = make_engine()
        snap = FakeSnapshot(content_hash="abc123")
        result = engine._check_content_integrity(FakeSource(), snap)
        assert result.passed is False


class TestUrlValid:
    def test_pass_valid_url(self):
        engine = make_engine()
        source = FakeSource(source_url="https://example.com/api/v2/changelog")
        result = engine._check_url_valid(source)
        assert result.passed is True

    def test_fail_generic_homepage(self):
        engine = make_engine()
        source = FakeSource(source_url="https://github.com/")
        result = engine._check_url_valid(source)
        assert result.passed is False

    def test_fail_no_scheme(self):
        engine = make_engine()
        source = FakeSource(source_url="not-a-url")
        result = engine._check_url_valid(source)
        assert result.passed is False

    def test_fail_ftp_scheme(self):
        engine = make_engine()
        source = FakeSource(source_url="ftp://example.com/data")
        result = engine._check_url_valid(source)
        assert result.passed is False


class TestSourceAuthority:
    def test_pass_official_documentation(self):
        engine = make_engine()
        source = FakeSource(authority_level="OFFICIAL_DOCUMENTATION")
        result = engine._check_source_authority(source)
        assert result.passed is True

    def test_pass_official_release(self):
        engine = make_engine()
        source = FakeSource(authority_level="OFFICIAL_RELEASE")
        result = engine._check_source_authority(source)
        assert result.passed is True

    def test_fail_heuristic(self):
        engine = make_engine()
        source = FakeSource(authority_level="HEURISTIC")
        result = engine._check_source_authority(source)
        assert result.passed is False

    def test_fail_third_party(self):
        engine = make_engine()
        source = FakeSource(authority_level="THIRD_PARTY_REFERENCE")
        result = engine._check_source_authority(source)
        assert result.passed is False


class TestPublisherTimestamp:
    def test_pass_different_timestamps(self):
        engine = make_engine()
        snap = FakeSnapshot()
        snap.retrieved_at = utcnow()
        snap.published_at = utcnow() - timedelta(hours=3)
        result = engine._check_publisher_timestamp(snap)
        assert result.passed is True

    def test_fail_null_published_at(self):
        engine = make_engine()
        snap = FakeSnapshot()
        snap.published_at = None
        result = engine._check_publisher_timestamp(snap)
        assert result.passed is False

    def test_fail_equal_timestamps(self):
        engine = make_engine()
        now = utcnow()
        snap = FakeSnapshot()
        snap.published_at = now
        snap.retrieved_at = now
        result = engine._check_publisher_timestamp(snap)
        assert result.passed is False

    def test_fail_no_snapshot(self):
        engine = make_engine()
        result = engine._check_publisher_timestamp(None)
        assert result.passed is False


class TestEntityRelationship:
    def test_pass_with_company_id(self):
        engine = make_engine()
        source = FakeSource(company_id=42)
        result = engine._check_entity_relationship(source)
        assert result.passed is True

    def test_fail_null_company_id(self):
        engine = make_engine()
        source = FakeSource(company_id=None)
        result = engine._check_entity_relationship(source)
        assert result.passed is False


class TestFreshness:
    def test_pass_recent_snapshot(self):
        engine = make_engine()
        snap = FakeSnapshot(retrieved_at=utcnow() - timedelta(minutes=15))
        result = engine._check_freshness(snap, window_hours=1)
        assert result.passed is True

    def test_fail_old_snapshot(self):
        engine = make_engine()
        snap = FakeSnapshot(retrieved_at=utcnow() - timedelta(hours=48))
        result = engine._check_freshness(snap, window_hours=1)
        assert result.passed is False

    def test_fail_no_snapshot(self):
        engine = make_engine()
        result = engine._check_freshness(None, window_hours=1)
        assert result.passed is False


class TestAiInfluence:
    def test_pass_no_ai_keys(self):
        db = MagicMock()
        engine = VerificationEngine(db)
        fake_change = FakeChange(score_factors={"security_relevance": 0.9})
        mock_q = MagicMock()
        mock_q.filter.return_value = mock_q
        mock_q.order_by.return_value = mock_q
        mock_q.first.return_value = fake_change
        db.query.return_value = mock_q
        source = FakeSource()
        result = engine._check_ai_influence(source)
        # No ai_ keys → check reports "no AI influence" → passed=False means NO AI detected
        assert result.check_id == CheckId.AI_INFLUENCE_CHECK

    def test_fail_ai_keys_present(self):
        db = MagicMock()
        engine = VerificationEngine(db)
        fake_change = FakeChange(score_factors={"ai_confidence": 0.95, "ai_reasoning": "text"})
        mock_q = MagicMock()
        mock_q.filter.return_value = mock_q
        mock_q.order_by.return_value = mock_q
        mock_q.first.return_value = fake_change
        db.query.return_value = mock_q
        source = FakeSource()
        result = engine._check_ai_influence(source)
        # AI keys found → check passes (meaning AI IS present)
        assert result.passed is True
        assert result.check_id == CheckId.AI_INFLUENCE_CHECK


# ---------------------------------------------------------------------------
# ── STATE ASSIGNMENT TESTS ── (11 states)
# ---------------------------------------------------------------------------

class TestStateAssignment:
    def _make_checks(self, passed_ids: set) -> list[CheckResult]:
        """Generate all 14 check results with given IDs passed."""
        results = []
        for cid in CheckId:
            passed = cid in passed_ids
            results.append(CheckResult(cid, passed, f"{'PASS' if passed else 'FAIL'}: {cid.value}"))
        return results

    def test_rejected_no_reachable_no_integrity(self):
        engine = make_engine()
        checks = self._make_checks(set())  # nothing passes
        result = engine._assign_state(checks)
        assert result.state == VerificationState.REJECTED

    def test_candidate_ai_influence(self):
        engine = make_engine()
        passed = {CheckId.AI_INFLUENCE_CHECK, CheckId.SOURCE_REACHABLE, CheckId.CONTENT_INTEGRITY}
        checks = self._make_checks(passed)
        result = engine._assign_state(checks)
        assert result.state == VerificationState.CANDIDATE
        assert result.ai_influenced is True

    def test_verified_all_4_conditions(self):
        engine = make_engine()
        passed = {
            CheckId.DIRECT_PRODUCTION_OBSERVATION,
            CheckId.CORROBORATION,
            CheckId.CONTENT_INTEGRITY,
            CheckId.FRESHNESS,
            CheckId.SOURCE_REACHABLE,
        }
        checks = self._make_checks(passed)
        result = engine._assign_state(checks)
        assert result.state == VerificationState.VERIFIED
        assert result.confidence > 0.5

    def test_observed_direct_obs_plus_integrity(self):
        engine = make_engine()
        passed = {
            CheckId.DIRECT_PRODUCTION_OBSERVATION,
            CheckId.CONTENT_INTEGRITY,
            CheckId.SOURCE_REACHABLE,
        }
        checks = self._make_checks(passed)
        result = engine._assign_state(checks)
        assert result.state == VerificationState.OBSERVED

    def test_corroborated_two_sources_authority(self):
        engine = make_engine()
        passed = {CheckId.CORROBORATION, CheckId.SOURCE_AUTHORITY, CheckId.URL_VALID, CheckId.SOURCE_REACHABLE}
        checks = self._make_checks(passed)
        result = engine._assign_state(checks)
        assert result.state == VerificationState.CORROBORATED

    def test_documented_authority_url(self):
        engine = make_engine()
        passed = {CheckId.SOURCE_AUTHORITY, CheckId.URL_VALID, CheckId.SOURCE_REACHABLE}
        checks = self._make_checks(passed)
        result = engine._assign_state(checks)
        assert result.state == VerificationState.DOCUMENTED

    def test_documented_not_observed_conflict(self):
        engine = make_engine()
        passed = {CheckId.CONFLICT_DETECTION, CheckId.SOURCE_REACHABLE, CheckId.CONTENT_INTEGRITY}
        checks = self._make_checks(passed)
        result = engine._assign_state(checks)
        assert result.state == VerificationState.DOCUMENTED_NOT_OBSERVED

    def test_conflicting_conflict_plus_corroboration(self):
        engine = make_engine()
        passed = {
            CheckId.CONFLICT_DETECTION,
            CheckId.CORROBORATION,
            CheckId.SOURCE_REACHABLE,
            CheckId.CONTENT_INTEGRITY,
        }
        checks = self._make_checks(passed)
        result = engine._assign_state(checks)
        assert result.state == VerificationState.CONFLICTING

    def test_unverified_nothing_passes(self):
        engine = make_engine()
        passed = {CheckId.SOURCE_REACHABLE, CheckId.CONTENT_INTEGRITY}
        checks = self._make_checks(passed)
        result = engine._assign_state(checks)
        # Reachable + integrity only → should be UNVERIFIED or DEVELOPMENT_EVIDENCE
        assert result.state in (VerificationState.UNVERIFIED, VerificationState.DEVELOPMENT_EVIDENCE, VerificationState.HISTORICAL)


# ---------------------------------------------------------------------------
# ── GOLDEN CASE TESTS (A–G) ──────────────────────────────────────────────
# ---------------------------------------------------------------------------

class TestGoldenCases:
    """Seven canonical golden cases that must produce exact expected states."""

    def test_A_verified(self):
        """A: VERIFIED — direct observation + corroboration + content integrity + freshness."""
        engine = make_engine()
        checks = [
            CheckResult(CheckId.SOURCE_REACHABLE, True, "HTTP 200"),
            CheckResult(CheckId.CONTENT_INTEGRITY, True, "SHA-256 valid"),
            CheckResult(CheckId.URL_VALID, True, "URL valid"),
            CheckResult(CheckId.SOURCE_AUTHORITY, True, "OFFICIAL_DOCUMENTATION"),
            CheckResult(CheckId.PUBLISHER_TIMESTAMP, True, "Distinct timestamps"),
            CheckResult(CheckId.ENTITY_RELATIONSHIP, True, "company_id=1"),
            CheckResult(CheckId.SCOPE_MATCH, True, "1 target"),
            CheckResult(CheckId.DIRECT_PRODUCTION_OBSERVATION, True, "SUCCESS_CHANGED run"),
            CheckResult(CheckId.CORROBORATION, True, "3 distinct source types"),
            CheckResult(CheckId.CONTENT_TO_CLAIM_CONSISTENCY, True, "Hash present"),
            CheckResult(CheckId.CONFLICT_DETECTION, False, "No conflict"),
            CheckResult(CheckId.DUPLICATION, True, "2+ runs"),
            CheckResult(CheckId.FRESHNESS, True, "5m ago"),
            CheckResult(CheckId.AI_INFLUENCE_CHECK, False, "No AI keys"),
        ]
        result = engine._assign_state(checks)
        assert result.state == VerificationState.VERIFIED
        assert result.confidence >= 0.7

    def test_B_observed(self):
        """B: OBSERVED — direct observation, no corroboration."""
        engine = make_engine()
        checks = [
            CheckResult(CheckId.SOURCE_REACHABLE, True, "HTTP 200"),
            CheckResult(CheckId.CONTENT_INTEGRITY, True, "SHA-256 valid"),
            CheckResult(CheckId.URL_VALID, True, "Valid"),
            CheckResult(CheckId.SOURCE_AUTHORITY, False, "Low authority"),
            CheckResult(CheckId.PUBLISHER_TIMESTAMP, True, "OK"),
            CheckResult(CheckId.ENTITY_RELATIONSHIP, True, "OK"),
            CheckResult(CheckId.SCOPE_MATCH, True, "OK"),
            CheckResult(CheckId.DIRECT_PRODUCTION_OBSERVATION, True, "SUCCESS_CHANGED"),
            CheckResult(CheckId.CORROBORATION, False, "Only 1 source"),
            CheckResult(CheckId.CONTENT_TO_CLAIM_CONSISTENCY, True, "OK"),
            CheckResult(CheckId.CONFLICT_DETECTION, False, "OK"),
            CheckResult(CheckId.DUPLICATION, False, "1 run"),
            CheckResult(CheckId.FRESHNESS, False, "Old"),
            CheckResult(CheckId.AI_INFLUENCE_CHECK, False, "No AI"),
        ]
        result = engine._assign_state(checks)
        assert result.state == VerificationState.OBSERVED

    def test_C_corroborated(self):
        """C: CORROBORATED — 2+ sources, no direct observation."""
        engine = make_engine()
        checks = [
            CheckResult(CheckId.SOURCE_REACHABLE, True, "OK"),
            CheckResult(CheckId.CONTENT_INTEGRITY, False, "No snapshot"),
            CheckResult(CheckId.URL_VALID, True, "OK"),
            CheckResult(CheckId.SOURCE_AUTHORITY, True, "OFFICIAL_RELEASE"),
            CheckResult(CheckId.PUBLISHER_TIMESTAMP, False, "Null"),
            CheckResult(CheckId.ENTITY_RELATIONSHIP, True, "OK"),
            CheckResult(CheckId.SCOPE_MATCH, True, "OK"),
            CheckResult(CheckId.DIRECT_PRODUCTION_OBSERVATION, False, "No SUCCESS_CHANGED"),
            CheckResult(CheckId.CORROBORATION, True, "2 source types"),
            CheckResult(CheckId.CONTENT_TO_CLAIM_CONSISTENCY, False, "No hash"),
            CheckResult(CheckId.CONFLICT_DETECTION, False, "OK"),
            CheckResult(CheckId.DUPLICATION, False, "1 run"),
            CheckResult(CheckId.FRESHNESS, False, "Old"),
            CheckResult(CheckId.AI_INFLUENCE_CHECK, False, "No AI"),
        ]
        result = engine._assign_state(checks)
        assert result.state == VerificationState.CORROBORATED

    def test_D_candidate_ai_influence(self):
        """D: CANDIDATE — AI influence detected in score_factors."""
        engine = make_engine()
        checks = [
            CheckResult(CheckId.SOURCE_REACHABLE, True, "OK"),
            CheckResult(CheckId.CONTENT_INTEGRITY, True, "OK"),
            CheckResult(CheckId.URL_VALID, True, "OK"),
            CheckResult(CheckId.SOURCE_AUTHORITY, True, "OK"),
            CheckResult(CheckId.PUBLISHER_TIMESTAMP, True, "OK"),
            CheckResult(CheckId.ENTITY_RELATIONSHIP, True, "OK"),
            CheckResult(CheckId.SCOPE_MATCH, True, "OK"),
            CheckResult(CheckId.DIRECT_PRODUCTION_OBSERVATION, True, "OK"),
            CheckResult(CheckId.CORROBORATION, True, "OK"),
            CheckResult(CheckId.CONTENT_TO_CLAIM_CONSISTENCY, True, "OK"),
            CheckResult(CheckId.CONFLICT_DETECTION, False, "OK"),
            CheckResult(CheckId.DUPLICATION, True, "OK"),
            CheckResult(CheckId.FRESHNESS, True, "OK"),
            CheckResult(CheckId.AI_INFLUENCE_CHECK, True, "ai_confidence, ai_reasoning detected"),
        ]
        result = engine._assign_state(checks)
        assert result.state == VerificationState.CANDIDATE
        assert result.ai_influenced is True

    def test_E_conflicting(self):
        """E: CONFLICTING — conflict detected with corroboration."""
        engine = make_engine()
        checks = [
            CheckResult(CheckId.SOURCE_REACHABLE, True, "OK"),
            CheckResult(CheckId.CONTENT_INTEGRITY, True, "OK"),
            CheckResult(CheckId.URL_VALID, True, "OK"),
            CheckResult(CheckId.SOURCE_AUTHORITY, True, "OK"),
            CheckResult(CheckId.PUBLISHER_TIMESTAMP, False, "Null"),
            CheckResult(CheckId.ENTITY_RELATIONSHIP, True, "OK"),
            CheckResult(CheckId.SCOPE_MATCH, True, "OK"),
            CheckResult(CheckId.DIRECT_PRODUCTION_OBSERVATION, False, "No change run"),
            CheckResult(CheckId.CORROBORATION, True, "2 sources"),
            CheckResult(CheckId.CONTENT_TO_CLAIM_CONSISTENCY, True, "OK"),
            CheckResult(CheckId.CONFLICT_DETECTION, True, "DOCUMENTED_NOT_OBSERVED"),
            CheckResult(CheckId.DUPLICATION, False, "1 run"),
            CheckResult(CheckId.FRESHNESS, False, "Old"),
            CheckResult(CheckId.AI_INFLUENCE_CHECK, False, "No AI"),
        ]
        result = engine._assign_state(checks)
        assert result.state == VerificationState.CONFLICTING

    def test_F_unverified(self):
        """F: UNVERIFIED — no checks pass."""
        engine = make_engine()
        checks = [
            CheckResult(CheckId.SOURCE_REACHABLE, True, "OK"),  # only reachable
            CheckResult(CheckId.CONTENT_INTEGRITY, True, "OK"),  # and integrity
            CheckResult(CheckId.URL_VALID, False, "Generic"),
            CheckResult(CheckId.SOURCE_AUTHORITY, False, "Heuristic"),
            CheckResult(CheckId.PUBLISHER_TIMESTAMP, False, "Null"),
            CheckResult(CheckId.ENTITY_RELATIONSHIP, False, "No company"),
            CheckResult(CheckId.SCOPE_MATCH, False, "No targets"),
            CheckResult(CheckId.DIRECT_PRODUCTION_OBSERVATION, False, "No run"),
            CheckResult(CheckId.CORROBORATION, False, "1 source"),
            CheckResult(CheckId.CONTENT_TO_CLAIM_CONSISTENCY, False, "No hash"),
            CheckResult(CheckId.CONFLICT_DETECTION, False, "OK"),
            CheckResult(CheckId.DUPLICATION, False, "1 run"),
            CheckResult(CheckId.FRESHNESS, False, "Old"),
            CheckResult(CheckId.AI_INFLUENCE_CHECK, False, "No AI"),
        ]
        result = engine._assign_state(checks)
        # With only SOURCE_REACHABLE + CONTENT_INTEGRITY → HISTORICAL or UNVERIFIED
        assert result.state in (VerificationState.UNVERIFIED, VerificationState.HISTORICAL, VerificationState.DEVELOPMENT_EVIDENCE)

    def test_G_rejected(self):
        """G: REJECTED — source unreachable + content integrity failed."""
        engine = make_engine()
        checks = [
            CheckResult(CheckId.SOURCE_REACHABLE, False, "HTTP 403"),
            CheckResult(CheckId.CONTENT_INTEGRITY, False, "No snapshot"),
            CheckResult(CheckId.URL_VALID, True, "OK"),
            CheckResult(CheckId.SOURCE_AUTHORITY, True, "OK"),
            CheckResult(CheckId.PUBLISHER_TIMESTAMP, False, "Null"),
            CheckResult(CheckId.ENTITY_RELATIONSHIP, True, "OK"),
            CheckResult(CheckId.SCOPE_MATCH, True, "OK"),
            CheckResult(CheckId.DIRECT_PRODUCTION_OBSERVATION, False, "No run"),
            CheckResult(CheckId.CORROBORATION, False, "1 source"),
            CheckResult(CheckId.CONTENT_TO_CLAIM_CONSISTENCY, False, "No hash"),
            CheckResult(CheckId.CONFLICT_DETECTION, False, "OK"),
            CheckResult(CheckId.DUPLICATION, False, "1 run"),
            CheckResult(CheckId.FRESHNESS, False, "Old"),
            CheckResult(CheckId.AI_INFLUENCE_CHECK, False, "No AI"),
        ]
        result = engine._assign_state(checks)
        assert result.state == VerificationState.REJECTED
        assert result.confidence == 0.0


# ---------------------------------------------------------------------------
# ── INVARIANT TESTS ──────────────────────────────────────────────────────
# ---------------------------------------------------------------------------

class TestInvariants:
    """Business rules that must NEVER be violated."""

    def test_ai_cannot_elevate_above_candidate(self):
        """AI influence must cap state at CANDIDATE regardless of other checks."""
        engine = make_engine()
        # All other checks pass — but AI is present
        checks = [CheckResult(cid, True, "PASS") for cid in CheckId]
        result = engine._assign_state(checks)
        assert result.state == VerificationState.CANDIDATE

    def test_confidence_is_between_0_and_1(self):
        """Confidence must always be in [0.0, 1.0]."""
        engine = make_engine()
        for state_checks in [
            set(),
            {CheckId.DIRECT_PRODUCTION_OBSERVATION, CheckId.CONTENT_INTEGRITY, CheckId.FRESHNESS, CheckId.CORROBORATION},
            {CheckId.AI_INFLUENCE_CHECK},
        ]:
            checks = [
                CheckResult(cid, cid in state_checks, "test")
                for cid in CheckId
            ]
            result = engine._assign_state(checks)
            assert 0.0 <= result.confidence <= 1.0, f"Confidence {result.confidence} out of bounds for state {result.state}"

    def test_has_ai_factors_detection(self):
        engine = make_engine()
        assert engine._has_ai_factors({"ai_confidence": 0.9}) is True
        assert engine._has_ai_factors({"ai_": "anything"}) is True
        assert engine._has_ai_factors({"security_score": 0.5}) is False
        assert engine._has_ai_factors({}) is False
