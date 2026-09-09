"""Snapshot background job for RQ workers.

Executes target snapshots asynchronously outside the web request cycle.
Opens its own database session and manages pipeline lifecycle.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from app.db import SessionLocal
from app.models.snapshot import Snapshot
from app.services.pipeline import TargetPipeline

logger = logging.getLogger(__name__)


def run_snapshot(target_id: int) -> dict[str, Any]:
    """RQ job that runs the full intelligence pipeline snapshot for a target.

    Opens its own isolated database session, invokes the TargetPipeline,
    updates the snapshot status, and handles errors gracefully.
    """
    logger.info("Starting background snapshot job for target_id=%d", target_id)
    db = SessionLocal()

    try:
        pipeline = TargetPipeline()

        # Safely execute the async pipeline in the synchronous RQ worker process
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                result = pool.submit(asyncio.run, pipeline.run(target_id, db)).result()
        else:
            result = asyncio.run(pipeline.run(target_id, db))

        logger.info(
            "Snapshot job completed successfully for target_id=%d (snapshot_id=%s)",
            target_id,
            result.get("snapshot_id"),
        )
        return result

    except Exception as exc:
        logger.error(
            "Snapshot job failed for target_id=%d: %s", target_id, exc, exc_info=True
        )
        # Attempt to mark the most recent running snapshot as failed if one exists
        try:
            recent_snapshot = (
                db.query(Snapshot)
                .filter(Snapshot.target_id == target_id, Snapshot.status == "running")
                .order_by(Snapshot.id.desc())
                .first()
            )
            if recent_snapshot:
                recent_snapshot.status = "failed"
                recent_snapshot.error = str(exc)
                db.commit()
        except Exception as db_exc:
            logger.error("Failed to record snapshot failure status in database: %s", db_exc)

        return {
            "status": "failed",
            "target_id": target_id,
            "error": str(exc),
        }

    finally:
        db.close()
