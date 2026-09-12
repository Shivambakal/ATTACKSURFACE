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
import time
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
_in_memory_locks: dict[int, float] = {}


class CorporateScheduler:
    """Orchestrates continuous 10-minute polling cycles across corporate sources."""

    def __init__(self, redis_client: Redis | None = None):
        self._redis_client = redis_client
        self.engine = ConnectorEngine()

    @property
    def redis(self) -> Redis | None:
        """Lazily initialize Redis client with exception isolation."""
        if self._redis_client is not None:
            return self._redis_client
        try:
            if settings.redis_url and settings.redis_url.startswith(("redis://", "rediss://", "unix://")):
                self._redis_client = Redis.from_url(settings.redis_url)
                return self._redis_client
        except Exception as exc:
            logger.warning("Redis initialization failed; falling back to in-memory locking: %s", exc)
        return None

    def acquire_source_lock(self, source_id: int, ttl: int = DEFAULT_LOCK_TTL) -> bool:
        """Acquires a distributed or in-memory lock for an individual source."""
        now = time.monotonic()
        r = self.redis
        if r is not None:
            try:
                key = f"{LOCK_PREFIX}{source_id}"
                acquired = r.set(key, "locked", nx=True, ex=ttl)
                return bool(acquired)
            except Exception as exc:
                logger.debug("Redis lock error for source %s: %s; falling back to memory", source_id, exc)

        # In-memory lock fallback with expiration
        exp = _in_memory_locks.get(source_id)
        if exp and exp > now:
            return False
        _in_memory_locks[source_id] = now + ttl
        return True

    def release_source_lock(self, source_id: int) -> None:
        """Releases the distributed or in-memory lock."""
        _in_memory_locks.pop(source_id, None)
        r = self.redis
        if r is not None:
            try:
                key = f"{LOCK_PREFIX}{source_id}"
                r.delete(key)
            except Exception as exc:
                logger.debug("Redis release lock error for source %s: %s", source_id, exc)

    def get_due_sources(self, db: Session, limit: int = 100, force: bool = False) -> list[CompanySource]:
        """Returns enabled sources ready for collection."""
        from sqlalchemy import or_
        now = datetime.now(timezone.utc)
        conditions = [
            CompanySource.enabled.is_(True),
            CompanySource.status != SourceStatus.DISABLED.value,
        ]
        if not force:
            conditions.append(or_(CompanySource.next_check_at.is_(None), CompanySource.next_check_at <= now))

        query = (
            select(CompanySource)
            .where(*conditions)
            .order_by(CompanySource.priority.asc(), CompanySource.next_check_at.asc().nullsfirst())
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

    async def run_due_sources(
        self, db: Session, max_sources: int = 50, force: bool = False, enqueue_to_rq: bool = False
    ) -> dict[str, Any]:
        """Runs an execution cycle for all due sources, respecting locks and intervals.

        When enqueue_to_rq=True and Redis is available, dispatches each source to its
        designated RQ priority queue (p0_critical, p1_official, p2_standard, etc.) for worker execution.
        """
        due = self.get_due_sources(db, limit=max_sources, force=force)
        stats: dict[str, Any] = {
            "due_count": len(due),
            "dispatched": 0,
            "locked_skipped": 0,
            "errors": 0,
            "items_found": 0,
            "items_changed": 0,
            "runs": [],
        }

        now = datetime.now(timezone.utc)
        r = self.redis

        for source in due:
            if not self.acquire_source_lock(source.id):
                stats["locked_skipped"] += 1
                continue

            try:
                # Update next_check_at ahead of time to prevent immediate re-selection
                interval = max(source.poll_interval_seconds or 600, 60)
                source.next_check_at = now + timedelta(seconds=interval)
                db.commit()

                if enqueue_to_rq and r is not None:
                    from rq import Queue
                    pri = (source.priority or "P2").upper()
                    queue_name = {
                        "P0": "p0_critical",
                        "P1": "p1_official",
                        "P3": "p3_replay",
                        "P4": "p4_community",
                    }.get(pri, "p2_standard")
                    q = Queue(queue_name, connection=r)
                    job = q.enqueue("app.jobs.corporate_source_job.run_corporate_source_collection", source.id)
                    stats["dispatched"] += 1
                    stats["runs"].append({
                        "source_id": source.id,
                        "source_name": source.name,
                        "status": "ENQUEUED",
                        "queue": queue_name,
                        "job_id": job.id,
                    })
                else:
                    # Execute collection directly
                    result = await self.engine.execute_source(source.id, db)
                    stats["dispatched"] += 1
                    stats["items_found"] += len(result.items)
                    stats["items_changed"] += len(result.items) if result.status == "SUCCESS_CHANGED" else 0
                    stats["runs"].append({
                        "source_id": source.id,
                        "source_name": source.name,
                        "status": result.status,
                        "http_status": result.http_status,
                        "items_found": len(result.items),
                        "duration_ms": result.duration_ms,
                    })
            except Exception as exc:
                logger.error("Error executing source %s: %s", source.id, exc)
                stats["errors"] += 1
                stats["runs"].append({
                    "source_id": source.id,
                    "source_name": source.name,
                    "status": "FAILED",
                    "error": str(exc),
                })
            finally:
                self.release_source_lock(source.id)

        return stats

    async def run_security_intelligence_cycle(self, db: Session) -> dict[str, Any]:
        """Triggers the 10-minute AI security intelligence collector cycle."""
        from ..jobs.security_intelligence_job import run_security_intelligence_collection
        return run_security_intelligence_collection(trigger_mode="scheduled")

