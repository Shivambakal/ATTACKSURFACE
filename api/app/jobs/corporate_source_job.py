"""Corporate source collection background job for RQ workers.

Executes source collection asynchronously via ConnectorEngine outside the web/scheduler process.
Opens its own isolated database session and writes results to Supabase.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from ..db import SessionLocal
from ..services.connector_engine import ConnectorEngine

logger = logging.getLogger(__name__)


def run_corporate_source_collection(source_id: int) -> dict[str, Any]:
    """RQ background job that executes collection for a corporate source."""
    logger.info("Starting RQ corporate source collection job for source_id=%d", source_id)
    db = SessionLocal()
    try:
        engine = ConnectorEngine()
        result = asyncio.run(engine.execute_source(source_id, db))
        logger.info(
            "Corporate source collection completed for source_id=%d: status=%s items=%d duration=%dms",
            source_id,
            result.status,
            len(result.items),
            result.duration_ms,
        )
        return {
            "source_id": source_id,
            "status": result.status,
            "http_status": result.http_status,
            "items_found": len(result.items),
            "items_changed": len(result.items) if result.status == "SUCCESS_CHANGED" else 0,
            "duration_ms": result.duration_ms,
            "error": result.error_message,
        }
    except Exception as exc:
        logger.exception("Corporate source collection job failed for source_id=%d: %s", source_id, exc)
        return {
            "source_id": source_id,
            "status": "FAILED",
            "error": str(exc),
        }
    finally:
        db.close()
