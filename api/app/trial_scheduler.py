"""Conservative recurring scheduler for an active 50 Target Trial."""
from __future__ import annotations

import logging
import time

from redis import Redis
from rq import Queue
from sqlalchemy import or_

from app.config import settings
from app.db import SessionLocal
from app.models import Snapshot, TrialRun, TrialTarget
from app.models.base import utcnow

logger = logging.getLogger(__name__)
POLL_SECONDS = 900
MIN_TARGET_INTERVAL_SECONDS = 3600
LOCK_KEY = "lock:50_target_trial_scheduler"


def enqueue_due_targets() -> int:
    db = SessionLocal()
    redis = Redis.from_url(settings.redis_url)
    lock = redis.lock(LOCK_KEY, timeout=POLL_SECONDS - 30, blocking=False)
    if not lock.acquire():
        db.close()
        return 0
    try:
        run = db.query(TrialRun).filter_by(status="running").order_by(TrialRun.started_at.desc()).first()
        if not run:
            return 0
        queue = Queue("snapshots", connection=redis)
        queued = 0
        for trial_target in db.query(TrialTarget).filter_by(trial_run_id=run.id).all():
            latest = db.query(Snapshot).filter_by(target_id=trial_target.target_id).order_by(Snapshot.collected_at.desc()).first()
            if latest and (utcnow() - latest.collected_at).total_seconds() < MIN_TARGET_INTERVAL_SECONDS:
                continue
            queue.enqueue("app.jobs.snapshot_job.run_snapshot", trial_target.target_id)
            trial_target.collection_status = "queued"
            queued += 1
        db.commit()
        return queued
    finally:
        lock.release()
        db.close()


def sync_cisa_kev_if_due() -> None:
    """Periodically check and synchronize official CISA KEV catalog and entity links."""
    db = SessionLocal()
    try:
        from app.services.cisa_feed_service import CISAFeedService
        from app.services.cisa_entity_resolver import CISAEntityResolver
        from app.models.cisa_kev import CISAFeedSnapshot

        latest = db.query(CISAFeedSnapshot).order_by(CISAFeedSnapshot.fetched_at.desc()).first()
        now = utcnow()
        # If no snapshot exists or latest is older than 2 hours, perform full sync
        if not latest or (now - latest.fetched_at).total_seconds() > 7200:
            logger.info("CISA KEV catalog background sync starting (previous snapshot: %s)...", latest.fetched_at if latest else "never")
            service = CISAFeedService(db)
            sync_res = service.sync_catalog(force=True)
            logger.info("CISA KEV catalog synced: %s", sync_res.get("status", "SUCCESS"))

            resolver = CISAEntityResolver(db)
            ent_res = resolver.sync_confirmed_events(limit=2000)
            logger.info("CISA KEV entity resolution: %s", ent_res)
    except Exception:
        logger.exception("Background CISA KEV sync encountered an error; will retry next cycle")
    finally:
        db.close()


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    logger.info("Starting AttackSurface continuous trial scheduler and background intelligence loop...")
    while True:
        try:
            # 1. Synchronize CISA KEV and entity advisories
            sync_cisa_kev_if_due()

            # 2. Queue due trial target snapshots
            queued = enqueue_due_targets()
            if queued:
                logger.info("Queued %d due trial targets", queued)
        except Exception:
            logger.exception("Trial scheduler cycle failed; retrying next cycle")
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
