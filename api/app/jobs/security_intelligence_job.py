"""Background RQ Job for AI-Powered Security Intelligence Collection.

Executes on a 10-minute schedule and supports manual on-demand triggers.
Uses Redis distributed locking to prevent overlapping concurrent runs.
"""
from __future__ import annotations

import logging
from typing import Any, Optional

import redis
from app.config import settings
from app.db import SessionLocal
from app.services.security_intelligence_collector import SecurityIntelligenceCollector

logger = logging.getLogger(__name__)

LOCK_KEY = "lock:security_intelligence_collector"
LOCK_TIMEOUT = 600  # 10 minutes max run time


def run_security_intelligence_collection(
    trigger_mode: str = "scheduled",
    target_focus: Optional[str] = None,
    max_items: int = 20,
) -> dict[str, Any]:
    """Execute AI search-grounded security news & CVE collection job.

    Args:
        trigger_mode: 'scheduled' or 'manual'
        target_focus: Optional entity or domain focus
        max_items: Maximum items to collect and persist

    Returns:
        Dict detailing execution status and counts.
    """
    logger.info(
        "run_security_intelligence_collection started: trigger=%s target_focus=%s max_items=%d",
        trigger_mode,
        target_focus,
        max_items,
    )

    # Redis distributed lock acquisition
    redis_conn = None
    lock = None
    have_lock = False

    try:
        redis_conn = redis.from_url(settings.redis_url)
        lock = redis_conn.lock(LOCK_KEY, timeout=LOCK_TIMEOUT, blocking_timeout=2)
        have_lock = lock.acquire(blocking=False)
        if not have_lock:
            logger.warning("Another security intelligence collector job is currently executing. Skipping.")
            return {
                "status": "skipped",
                "reason": "Collector is currently executing in another process.",
            }
    except Exception as exc:
        logger.warning("Redis lock error (proceeding without distributed lock): %s", exc)

    db = SessionLocal()
    try:
        collector = SecurityIntelligenceCollector()
        if not collector.is_configured():
            logger.warning("Gemini API key is not configured. Collector cannot run.")
            return {
                "status": "error",
                "message": "Gemini API key is not configured.",
            }

        events = collector.collect_sync(db, target_focus=target_focus, max_items=max_items)

        high_priority_count = sum(1 for e in events if e.priority in ("CRITICAL", "HIGH"))
        actively_exploited_count = sum(1 for e in events if e.actively_exploited)

        result = {
            "status": "completed",
            "trigger_mode": trigger_mode,
            "events_collected": len(events),
            "high_priority_count": high_priority_count,
            "actively_exploited_count": actively_exploited_count,
        }
        logger.info("Security intelligence collection job completed: %s", result)
        return result
    except Exception as exc:
        logger.exception("Security intelligence collection job failed: %s", exc)
        return {
            "status": "error",
            "message": str(exc),
        }
    finally:
        db.close()
        if have_lock and lock:
            try:
                lock.release()
            except Exception as exc:
                logger.debug("Failed to release Redis lock: %s", exc)
