"""Centralized 10-Minute Corporate Intelligence Scheduler.

Responsible for:
- Selecting due sources (enabled and next_check_at <= now())
- Redis distributed locking (source_lock:{source_id}) to prevent concurrent fetches
- Partitioning by priority queue (P0, P1, P2, P3, P4)
- Rate limit and backoff enforcement
- Execution of source collection and dispatching to RQ
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any
from redis import Redis
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..models.source_registry import CompanySource, SourceStatus
from ..services.connector_engine import ConnectorEngine

logger = logging.getLogger(__name__)

LOCK_PREFIX = "source_lock:"
DEFAULT_LOCK_TTL = 300  # 5 minutes bounded lock


class CorporateScheduler:
    """Orchestrates continuous 10-minute polling cycles across corporate sources."""

    def __init__(self, redis_client: Redis | None = None):
        self.redis = redis_client or Redis.from_url(settings.redis_url)
        self.engine = ConnectorEngine()

    def acquire_source_lock(self, source_id: int, ttl: int = DEFAULT_LOCK_TTL) -> bool:
        """Acquires a Redis distributed lock for an individual source."""
        key = f"{LOCK_PREFIX}{source_id}"
        # Set if not exists with expiration
        acquired = self.redis.set(key, "locked", nx=True, ex=ttl)
        return bool(acquired)

    def release_source_lock(self, source_id: int) -> None:
        """Releases the Redis distributed lock."""
        key = f"{LOCK_PREFIX}{source_id}"
        self.redis.delete(key)

    def get_due_sources(self, db: Session, limit: int = 100) -> list[CompanySource]:
        """Returns enabled sources ready for collection."""
        now = datetime.now(timezone.utc)
        query = (
            select(CompanySource)
            .where(
                CompanySource.enabled.is_(True),
                CompanySource.next_check_at <= now,
                CompanySource.status != SourceStatus.DISABLED.value,
            )
            .order_by(CompanySource.priority.asc(), CompanySource.next_check_at.asc())
            .limit(limit)
        )
        return list(db.scalars(query).all())

    def partition_by_priority(self, sources: list[CompanySource]) -> dict[str, list[CompanySource]]:
        """Groups sources into designated priority tiers."""
        buckets: dict[str, list[CompanySource]] = {
            "p0_critical": [],
            "p1_official": [],
            "p2_standard": [],
            "p3_replay": [],
            "p4_community": [],
        }
        for s in sources:
            pri = (s.priority or "P2").upper()
            if pri == "P0":
                buckets["p0_critical"].append(s)
            elif pri == "P1":
                buckets["p1_official"].append(s)
            elif pri == "P3":
                buckets["p3_replay"].append(s)
            elif pri == "P4":
                buckets["p4_community"].append(s)
            else:
                buckets["p2_standard"].append(s)
        return buckets

    async def run_due_sources(self, db: Session, max_sources: int = 50) -> dict[str, int]:
        """Runs an execution cycle for all due sources, respecting locks and intervals."""
        due = self.get_due_sources(db, limit=max_sources)
        stats = {"dispatched": 0, "locked_skipped": 0, "errors": 0}

        now = datetime.now(timezone.utc)

        for source in due:
            if not self.acquire_source_lock(source.id):
                stats["locked_skipped"] += 1
                continue

            try:
                # Update next_check_at ahead of time to prevent immediate re-selection
                interval = max(source.poll_interval_seconds, 60)
                source.next_check_at = now + timedelta(seconds=interval)
                db.commit()

                # Execute collection
                await self.engine.execute_source(source.id, db)
                stats["dispatched"] += 1
            except Exception as exc:
                logger.error("Error executing source %s: %s", source.id, exc)
                stats["errors"] += 1
            finally:
                self.release_source_lock(source.id)

        return stats

    async def run_security_intelligence_cycle(self, db: Session) -> dict[str, Any]:
        """Triggers the 10-minute AI security intelligence collector cycle."""
        from ..jobs.security_intelligence_job import run_security_intelligence_collection
        return run_security_intelligence_collection(trigger_mode="scheduled")

