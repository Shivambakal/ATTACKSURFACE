"""Production 10-Minute Recurring Scheduler.

Continuously runs outside Vercel, orchestrating the 10-minute intelligence loop:
1. Knowledge Base Sync: Enqueues CISA KEV catalog sync to Upstash Redis ('p1_official')
2. Corporate Intelligence: Selects due corporate sources and enqueues to priority queues on Upstash Redis
3. AI Security Intelligence: Enqueues Gemini security intelligence collection to Upstash Redis ('ai')
4. Target Snapshots: Enqueues due trial/target snapshots to Upstash Redis ('snapshots')
5. Logs execution metrics, job IDs, and next scheduled run (interval: 600s).
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from redis import Redis
from rq import Queue
from sqlalchemy.orm import Session

from .config import settings
from .db import SessionLocal
from .services.corporate_scheduler import CorporateScheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [Scheduler] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("Scheduler")

SCHEDULER_LOCK_KEY = "lock:production_scheduler_loop"
DEFAULT_INTERVAL_SECONDS = 600  # 10 minutes


class ProductionScheduler:
    """Orchestrates continuous 10-minute intelligence cycles via Upstash Redis queues."""

    def __init__(self, interval_seconds: int = DEFAULT_INTERVAL_SECONDS):
        self.interval_seconds = interval_seconds
        self.redis = Redis.from_url(settings.redis_url)
        self.corporate_scheduler = CorporateScheduler(redis_client=self.redis)

    def run_cycle(self, cycle_num: int = 1) -> dict:
        cycle_id = str(uuid.uuid4())
        started_at = datetime.now(timezone.utc)
        logger.info("=" * 80)
        logger.info(
            "STARTING PRODUCTION SCHEDULER CYCLE #%d (ID: %s) at %s",
            cycle_num,
            cycle_id,
            started_at.isoformat(),
        )
        logger.info("Connected Upstash Redis: %s", settings.redis_url.split("@")[-1])
        logger.info("=" * 80)

        db: Session = SessionLocal()
        enqueued_jobs = []

        try:
            # 1. Enqueue Knowledge Base / CISA KEV sync
            try:
                q_p1 = Queue("p1_official", connection=self.redis)
                cisa_job = q_p1.enqueue(
                    "app.jobs.cisa_sync_job.run_cisa_sync",
                    force=False,
                    job_timeout=300,
                )
                enqueued_jobs.append({
                    "task": "cisa_kev_knowledge_sync",
                    "queue": "p1_official",
                    "job_id": cisa_job.id,
                })
                logger.info("Enqueued CISA KEV sync job: ID %s on queue 'p1_official'", cisa_job.id)
            except Exception as exc:
                logger.warning("Failed to enqueue CISA KEV sync job: %s", exc)

            # 2. Enqueue due corporate sources across priority queues
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                due_stats = loop.run_until_complete(
                    self.corporate_scheduler.run_due_sources(
                        db, max_sources=15, force=False, enqueue_to_rq=True
                    )
                )
                loop.close()
                for r in due_stats.get("runs", []):
                    if r.get("status") == "ENQUEUED":
                        enqueued_jobs.append({
                            "task": f"corporate_source:{r.get('source_id')}:{r.get('source_name')}",
                            "queue": r.get("queue"),
                            "job_id": r.get("job_id"),
                        })
                logger.info(
                    "Corporate sources dispatch: %d due, %d enqueued to RQ",
                    due_stats.get("due_count", 0),
                    due_stats.get("dispatched", 0),
                )
            except Exception as exc:
                logger.warning("Failed to enqueue corporate sources: %s", exc)

            # 3. Enqueue AI Security Intelligence collection
            try:
                q_ai = Queue("ai", connection=self.redis)
                ai_job = q_ai.enqueue(
                    "app.jobs.security_intelligence_job.run_security_intelligence_collection",
                    trigger_mode="scheduled",
                    max_items=20,
                    job_timeout=300,
                )
                enqueued_jobs.append({
                    "task": "ai_security_intelligence",
                    "queue": "ai",
                    "job_id": ai_job.id,
                })
                logger.info("Enqueued AI intelligence job: ID %s on queue 'ai'", ai_job.id)
            except Exception as exc:
                logger.warning("Failed to enqueue AI intelligence job: %s", exc)

            finished_at = datetime.now(timezone.utc)
            duration_ms = int((finished_at - started_at).total_seconds() * 1000)
            next_run_at = started_at + timedelta(seconds=self.interval_seconds)

            cycle_summary = {
                "cycle_num": cycle_num,
                "cycle_id": cycle_id,
                "started_at": started_at.isoformat(),
                "finished_at": finished_at.isoformat(),
                "duration_ms": duration_ms,
                "next_run_at": next_run_at.isoformat(),
                "jobs_enqueued_count": len(enqueued_jobs),
                "enqueued_jobs": enqueued_jobs,
            }

            logger.info(
                "CYCLE #%d DISPATCH COMPLETED: %d jobs enqueued in %dms. Next run scheduled at %s",
                cycle_num,
                len(enqueued_jobs),
                duration_ms,
                next_run_at.isoformat(),
            )
            return cycle_summary

        finally:
            db.close()

    def start_forever(self, max_cycles: int | None = None) -> None:
        logger.info("Starting persistent 10-minute scheduler loop (interval=%ds)...", self.interval_seconds)
        cycle_num = 1
        while True:
            try:
                self.run_cycle(cycle_num=cycle_num)
                if max_cycles and cycle_num >= max_cycles:
                    logger.info("Reached maximum cycles limit (%d). Exiting scheduler loop.", max_cycles)
                    break
                cycle_num += 1
                logger.info("Scheduler sleeping for %d seconds until next cycle...", self.interval_seconds)
                time.sleep(self.interval_seconds)
            except KeyboardInterrupt:
                logger.info("Scheduler stopped by user.")
                break
            except Exception as exc:
                logger.exception("Unexpected error in scheduler loop: %s. Retrying in 30s...", exc)
                time.sleep(30)


def main():
    parser = argparse.ArgumentParser(description="AttackSurface Production 10-Minute Scheduler")
    parser.add_argument("--interval", type=int, default=DEFAULT_INTERVAL_SECONDS, help="Polling interval in seconds")
    parser.add_argument("--once", action="store_true", help="Run a single cycle and exit")
    parser.add_argument("--max-cycles", type=int, default=None, help="Maximum cycles to run")
    args = parser.parse_args()

    scheduler = ProductionScheduler(interval_seconds=args.interval)
    if args.once:
        scheduler.run_cycle(cycle_num=1)
    else:
        scheduler.start_forever(max_cycles=args.max_cycles)


if __name__ == "__main__":
    main()
