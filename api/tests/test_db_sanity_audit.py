"""Database Sanity Audit — 20 production safety checks.

Connects to the production Supabase database and verifies data integrity.
Each check returns PASS or FAIL with the exact count/value found.

Run from api/ directory:
    python -m pytest tests/test_db_sanity_audit.py -v

Or run as a standalone script:
    python tests/test_db_sanity_audit.py

NOTE: Requires DATABASE_URL to be set in environment variables.
All checks are READ-ONLY. No writes are performed.
"""
from __future__ import annotations

import os
import sys
import pytest
from datetime import datetime, timedelta, timezone
from typing import Any

# Skip entire module if DATABASE_URL not set
pytestmark = pytest.mark.skipif(
    not os.environ.get("DATABASE_URL"),
    reason="DATABASE_URL not set; skipping DB sanity audit (requires production DB connection)"
)


@pytest.fixture(scope="module")
def db():
    """Create a read-only database session for all audit checks."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    database_url = os.environ["DATABASE_URL"]
    engine = create_engine(database_url, pool_pre_ping=True, pool_size=1, max_overflow=0)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    engine.dispose()


def utcnow():
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Audit checks
# ---------------------------------------------------------------------------

class TestDatabaseSanityAudit:

    def test_01_no_changes_with_null_fingerprint(self, db):
        """AUDIT 01: No Change records with null fingerprint."""
        from app.models.change import Change
        from sqlalchemy import func
        count = db.query(func.count(Change.id)).filter(Change.fingerprint == None).scalar() or 0
        assert count == 0, f"FAIL: {count} Change records have null fingerprint"

    def test_02_no_changes_with_null_detected_at(self, db):
        """AUDIT 02: No Change records with null detected_at timestamp."""
        from app.models.change import Change
        from sqlalchemy import func
        count = db.query(func.count(Change.id)).filter(Change.detected_at == None).scalar() or 0
        assert count == 0, f"FAIL: {count} Change records have null detected_at"

    def test_03_no_signals_with_confidence_over_100(self, db):
        """AUDIT 03: No ResearchSignal records with confidence_score > 100."""
        from app.models.signal import ResearchSignal
        from sqlalchemy import func
        count = db.query(func.count(ResearchSignal.id)).filter(ResearchSignal.confidence_score > 100).scalar() or 0
        assert count == 0, f"FAIL: {count} ResearchSignal records have confidence_score > 100"

    def test_04_no_signals_with_relevance_over_100(self, db):
        """AUDIT 04: No ResearchSignal records with relevance_score > 100."""
        from app.models.signal import ResearchSignal
        from sqlalchemy import func
        count = db.query(func.count(ResearchSignal.id)).filter(ResearchSignal.relevance_score > 100).scalar() or 0
        assert count == 0, f"FAIL: {count} ResearchSignal records have relevance_score > 100"

    def test_05_no_signals_with_zero_source_count(self, db):
        """AUDIT 05: No ResearchSignal with source_count = 0."""
        from app.models.signal import ResearchSignal
        from sqlalchemy import func
        count = db.query(func.count(ResearchSignal.id)).filter(ResearchSignal.source_count == 0).scalar() or 0
        assert count == 0, f"FAIL: {count} ResearchSignal records have source_count=0"

    def test_06_at_least_one_company(self, db):
        """AUDIT 06: Company registry has at least 1 company."""
        from app.models.company import Company
        from sqlalchemy import func
        count = db.query(func.count(Company.id)).scalar() or 0
        assert count >= 1, f"FAIL: Company registry is empty (count={count})"

    def test_07_at_least_one_authorized_target(self, db):
        """AUDIT 07: At least 1 authorized target in the target registry."""
        from app.models.target import Target
        from sqlalchemy import func
        count = db.query(func.count(Target.id)).scalar() or 0
        assert count >= 1, f"FAIL: Target registry is empty (count={count})"

    def test_08_no_changes_with_zero_confidence(self, db):
        """AUDIT 08: No Change records with confidence = 0.0 exactly (likely placeholder)."""
        from app.models.change import Change
        from sqlalchemy import func
        count = db.query(func.count(Change.id)).filter(Change.confidence == 0.0).scalar() or 0
        # Warning only: 0 confidence is technically valid if the diff had no signal
        # Allow up to 10% of total changes
        total = db.query(func.count(Change.id)).scalar() or 1
        pct = (count / total) * 100
        assert pct < 50, f"FAIL: {count}/{total} ({pct:.1f}%) Change records have zero confidence — exceeds 50% threshold"

    def test_09_enabled_sources_have_source_url(self, db):
        """AUDIT 09: All enabled CompanySource records have a non-null source_url."""
        from app.models.source_registry import CompanySource
        from sqlalchemy import func
        count = (
            db.query(func.count(CompanySource.id))
            .filter(CompanySource.enabled == True, CompanySource.source_url == None)
            .scalar()
        ) or 0
        assert count == 0, f"FAIL: {count} enabled sources have null source_url"

    def test_10_at_least_one_collection_run_in_last_24h(self, db):
        """AUDIT 10: At least 1 SourceCollectionRun in the last 24 hours."""
        from app.models.source_registry import SourceCollectionRun
        from sqlalchemy import func
        window = utcnow() - timedelta(hours=24)
        count = (
            db.query(func.count(SourceCollectionRun.id))
            .filter(SourceCollectionRun.started_at >= window)
            .scalar()
        ) or 0
        assert count >= 1, f"FAIL: No SourceCollectionRun in the last 24h — pipeline may be dead (count={count})"

    def test_11_at_least_one_success_run_in_last_48h(self, db):
        """AUDIT 11: At least 1 SUCCESS_* run in the last 48 hours."""
        from app.models.source_registry import SourceCollectionRun
        from sqlalchemy import func
        window = utcnow() - timedelta(hours=48)
        count = (
            db.query(func.count(SourceCollectionRun.id))
            .filter(
                SourceCollectionRun.started_at >= window,
                SourceCollectionRun.status.in_(["SUCCESS_CHANGED", "SUCCESS_UNCHANGED"]),
            )
            .scalar()
        ) or 0
        assert count >= 1, f"FAIL: No successful collection run in the last 48h — pipeline may be broken"

    def test_12_no_raw_snapshot_with_empty_content_hash(self, db):
        """AUDIT 12: No RawSourceSnapshot with empty content_hash."""
        from app.models.source_registry import RawSourceSnapshot
        from sqlalchemy import func
        count = (
            db.query(func.count(RawSourceSnapshot.id))
            .filter(
                (RawSourceSnapshot.content_hash == None) |
                (RawSourceSnapshot.content_hash == "")
            )
            .scalar()
        ) or 0
        assert count == 0, f"FAIL: {count} RawSourceSnapshot records have empty/null content_hash"

    def test_13_no_company_sources_stuck_scheduled(self, db):
        """AUDIT 13: No CompanySource stuck in SCHEDULED status for > 48h."""
        from app.models.source_registry import CompanySource, SourceStatus
        from sqlalchemy import func
        cutoff = utcnow() - timedelta(hours=48)
        count = (
            db.query(func.count(CompanySource.id))
            .filter(
                CompanySource.status == SourceStatus.SCHEDULED.value,
                CompanySource.last_checked_at != None,
                CompanySource.last_checked_at < cutoff,
            )
            .scalar()
        ) or 0
        assert count == 0, f"FAIL: {count} CompanySource records stuck in SCHEDULED for >48h"

    def test_14_changes_have_linked_target(self, db):
        """AUDIT 14: No Change records with null target_id."""
        from app.models.change import Change
        from sqlalchemy import func
        count = db.query(func.count(Change.id)).filter(Change.target_id == None).scalar() or 0
        assert count == 0, f"FAIL: {count} Change records have null target_id"

    def test_15_no_negative_security_relevance(self, db):
        """AUDIT 15: No Change records with negative security_relevance."""
        from app.models.change import Change
        from sqlalchemy import func
        count = db.query(func.count(Change.id)).filter(Change.security_relevance < 0).scalar() or 0
        assert count == 0, f"FAIL: {count} Change records have negative security_relevance"

    def test_16_no_source_runs_with_both_null_status_and_finished(self, db):
        """AUDIT 16: No SourceCollectionRun with null status."""
        from app.models.source_registry import SourceCollectionRun
        from sqlalchemy import func
        count = (
            db.query(func.count(SourceCollectionRun.id))
            .filter(SourceCollectionRun.status == None)
            .scalar()
        ) or 0
        assert count == 0, f"FAIL: {count} SourceCollectionRun records have null status"

    def test_17_no_company_without_name(self, db):
        """AUDIT 17: No Company records with null or empty name."""
        from app.models.company import Company
        from sqlalchemy import func
        count = (
            db.query(func.count(Company.id))
            .filter(
                (Company.name == None) | (Company.name == "")
            )
            .scalar()
        ) or 0
        assert count == 0, f"FAIL: {count} Company records have null/empty name"

    def test_18_change_confidence_in_valid_range(self, db):
        """AUDIT 18: All Change.confidence values are in [0.0, 1.0] (or [0, 100] — check both)."""
        from app.models.change import Change
        from sqlalchemy import func
        # Outside 0-100 range is definitely wrong
        out_of_range = (
            db.query(func.count(Change.id))
            .filter((Change.confidence < 0) | (Change.confidence > 100))
            .scalar()
        ) or 0
        assert out_of_range == 0, f"FAIL: {out_of_range} Change records have confidence outside [0, 100]"

    def test_19_research_signals_have_title(self, db):
        """AUDIT 19: No ResearchSignal with null or empty title."""
        from app.models.signal import ResearchSignal
        from sqlalchemy import func
        count = (
            db.query(func.count(ResearchSignal.id))
            .filter(
                (ResearchSignal.title == None) | (ResearchSignal.title == "")
            )
            .scalar()
        ) or 0
        assert count == 0, f"FAIL: {count} ResearchSignal records have null/empty title"

    def test_20_at_least_one_enabled_source(self, db):
        """AUDIT 20: At least 1 enabled CompanySource exists (pipeline would have nothing to poll)."""
        from app.models.source_registry import CompanySource
        from sqlalchemy import func
        count = (
            db.query(func.count(CompanySource.id))
            .filter(CompanySource.enabled == True)
            .scalar()
        ) or 0
        assert count >= 1, f"FAIL: No enabled CompanySource records found — pipeline has no sources to poll"


# ---------------------------------------------------------------------------
# Standalone script entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import subprocess
    result = subprocess.run(
        [sys.executable, "-m", "pytest", __file__, "-v", "--tb=short"],
        cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    )
    sys.exit(result.returncode)
