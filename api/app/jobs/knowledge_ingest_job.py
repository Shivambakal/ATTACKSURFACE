"""Background job for CISA KEV catalog ingestion.

Compatible with RQ (Redis Queue) worker infrastructure.
Enqueue with::

    from rq import Queue
    from app.jobs.knowledge_ingest_job import knowledge_ingest_cisa_kev
    q = Queue(connection=redis_conn)
    job = q.enqueue(knowledge_ingest_cisa_kev, catalog_path="../cisa_kev_catalog.json")
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from app.db import SessionLocal
from app.knowledge.cisa_kev_ingestor import CISAKEVIngestor

logger = logging.getLogger(__name__)


def knowledge_ingest_cisa_kev(
    catalog_path: str,
    limit: Optional[int] = None,
    dry_run: bool = False,
    source_version: Optional[str] = None,
) -> dict[str, Any]:
    """RQ-compatible job function for ingesting the CISA KEV catalog.

    Args:
        catalog_path: Path to the CISA KEV JSON catalog file.
        limit: Optional cap on entries processed (useful for staging).
        dry_run: If True, validate but do not persist to the database.
        source_version: Override the source version string.

    Returns:
        Dict with ingestion statistics and status.
    """
    logger.info(
        "knowledge_ingest_cisa_kev started: path=%s limit=%s dry_run=%s",
        catalog_path, limit, dry_run,
    )
    db = SessionLocal()
    try:
        ingestor = CISAKEVIngestor()
        sync_run = ingestor.ingest(
            db=db,
            catalog_path=catalog_path,
            limit=limit,
            dry_run=dry_run,
            source_version=source_version,
        )
        result = {
            "status": sync_run.status,
            "sync_run_id": sync_run.id,
            "records_seen": sync_run.records_seen,
            "records_created": sync_run.records_created,
            "records_updated": sync_run.records_updated,
            "records_skipped": sync_run.records_skipped,
            "records_failed": sync_run.records_failed,
            "error_count": sync_run.error_count,
            "content_hash": sync_run.content_hash,
        }
        logger.info("knowledge_ingest_cisa_kev complete: %s", result)
        return result
    except Exception as exc:
        logger.exception("knowledge_ingest_cisa_kev failed: %s", exc)
        return {
            "status": "error",
            "message": str(exc),
            "catalog_path": catalog_path,
        }
    finally:
        db.close()
