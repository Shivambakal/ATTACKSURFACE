"""Alert digest background jobs for RQ workers.

Compiles daily and weekly attack surface digests for registered researchers.
"""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from app.db import SessionLocal
from app.models.base import utcnow
from app.models import User, Target, TimelineEvent, Alert

logger = logging.getLogger(__name__)


def send_daily_digest(user_id: int) -> dict[str, Any]:
    """RQ background job to generate and dispatch the daily attack surface digest.

    Aggregates events and alerts detected across the user's targets over the last 24 hours.
    """
    logger.info("Generating daily digest for user_id=%d", user_id)
    db = SessionLocal()

    try:
        user = db.get(User, user_id)
        if not user:
            logger.warning("User %d not found for daily digest", user_id)
            return {"status": "error", "message": f"User {user_id} not found."}

        targets = db.query(Target).filter(Target.user_id == user_id).all()
        target_ids = [t.id for t in targets]

        if not target_ids:
            logger.info("User %d has no registered targets; skipping daily digest", user_id)
            return {"status": "skipped", "message": "No targets configured."}

        now = utcnow()
        cutoff = now - timedelta(days=1)

        # Query timeline events observed in the past 24 hours
        events = (
            db.query(TimelineEvent)
            .filter(
                TimelineEvent.target_id.in_(target_ids),
                TimelineEvent.observed_at >= cutoff,
            )
            .order_by(TimelineEvent.relevance_score.desc())
            .all()
        )

        critical_count = sum(1 for e in events if e.priority == "CRITICAL")
        high_count = sum(1 for e in events if e.priority == "HIGH")
        medium_count = sum(1 for e in events if e.priority == "MEDIUM")

        if not events:
            summary = "No new attack surface changes or security events detected in the last 24 hours."
            priority = "INFO"
        else:
            summary = (
                f"Daily Digest: {len(events)} events detected across {len(targets)} targets. "
                f"Breakdown: {critical_count} Critical, {high_count} High, {medium_count} Medium priority. "
                f"Top event: {events[0].title}."
            )
            priority = "HIGH" if (critical_count > 0 or high_count > 0) else "INFO"

        # Create daily digest alert record
        digest_alert = Alert(
            user_id=user_id,
            alert_type="daily_digest",
            entity_type="digest",
            entity_id=None,
            title=f"Daily Security Digest ({now.strftime('%Y-%m-%d')})",
            summary=summary,
            priority=priority,
            read=False,
            created_at=now,
        )
        db.add(digest_alert)
        db.commit()

        logger.info("Daily digest created successfully for user_id=%d: %d events", user_id, len(events))
        return {
            "status": "complete",
            "user_id": user_id,
            "period": "daily",
            "events_count": len(events),
            "critical_count": critical_count,
            "high_count": high_count,
        }

    except Exception as exc:
        db.rollback()
        logger.error("Failed to generate daily digest for user_id=%d: %s", user_id, exc, exc_info=True)
        return {"status": "failed", "user_id": user_id, "error": str(exc)}

    finally:
        db.close()


def send_weekly_digest(user_id: int) -> dict[str, Any]:
    """RQ background job to generate and dispatch the weekly attack surface digest.

    Aggregates attack surface trends, new features, and security exposures over the last 7 days.
    """
    logger.info("Generating weekly digest for user_id=%d", user_id)
    db = SessionLocal()

    try:
        user = db.get(User, user_id)
        if not user:
            logger.warning("User %d not found for weekly digest", user_id)
            return {"status": "error", "message": f"User {user_id} not found."}

        targets = db.query(Target).filter(Target.user_id == user_id).all()
        target_ids = [t.id for t in targets]

        if not target_ids:
            logger.info("User %d has no registered targets; skipping weekly digest", user_id)
            return {"status": "skipped", "message": "No targets configured."}

        now = utcnow()
        cutoff = now - timedelta(days=7)

        events = (
            db.query(TimelineEvent)
            .filter(
                TimelineEvent.target_id.in_(target_ids),
                TimelineEvent.observed_at >= cutoff,
            )
            .order_by(TimelineEvent.relevance_score.desc())
            .all()
        )

        critical_count = sum(1 for e in events if e.priority == "CRITICAL")
        high_count = sum(1 for e in events if e.priority == "HIGH")
        new_apis = sum(1 for e in events if "api" in e.event_type.lower())
        auth_changes = sum(1 for e in events if "auth" in e.event_type.lower())

        if not events:
            summary = "Weekly Summary: No significant attack surface changes observed across your targets."
            priority = "INFO"
        else:
            summary = (
                f"Weekly Attack Surface Report: {len(events)} total changes across {len(targets)} targets. "
                f"Security Highlights: {critical_count} critical alerts, {high_count} high alerts, "
                f"{new_apis} API modifications, and {auth_changes} authentication changes."
            )
            priority = "HIGH" if (critical_count > 0 or high_count > 0) else "INFO"

        digest_alert = Alert(
            user_id=user_id,
            alert_type="weekly_digest",
            entity_type="digest",
            entity_id=None,
            title=f"Weekly Attack Surface Digest (Week of {cutoff.strftime('%b %d')})",
            summary=summary,
            priority=priority,
            read=False,
            created_at=now,
        )
        db.add(digest_alert)
        db.commit()

        logger.info("Weekly digest created successfully for user_id=%d: %d events", user_id, len(events))
        return {
            "status": "complete",
            "user_id": user_id,
            "period": "weekly",
            "events_count": len(events),
            "critical_count": critical_count,
            "high_count": high_count,
            "new_apis": new_apis,
            "auth_changes": auth_changes,
        }

    except Exception as exc:
        db.rollback()
        logger.error("Failed to generate weekly digest for user_id=%d: %s", user_id, exc, exc_info=True)
        return {"status": "failed", "user_id": user_id, "error": str(exc)}

    finally:
        db.close()
