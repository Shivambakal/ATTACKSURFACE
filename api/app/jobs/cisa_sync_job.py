"""CISA KEV scheduled background synchronization job."""
from __future__ import annotations

import logging
from ..db import SessionLocal
from ..services.cisa_feed_service import CISAFeedService
from ..services.cisa_entity_resolver import CISAEntityResolver

logger = logging.getLogger(__name__)


def run_cisa_sync(force: bool = False) -> dict:
    """Executes CISA KEV catalog sync and entity resolution in background worker."""
    db = SessionLocal()
    try:
        logger.info("Starting CISA KEV background synchronization job (force=%s)", force)
        service = CISAFeedService(db)
        sync_result = service.sync_catalog(force=force)

        resolution_result = {}
        if sync_result.get("success"):
            resolver = CISAEntityResolver(db)
            resolution_result = resolver.sync_confirmed_events(limit=2000)

        logger.info("CISA KEV background job completed: %s", sync_result.get("status", "SUCCESS"))
        return {
            "sync": sync_result,
            "resolution": resolution_result,
        }
    except Exception as exc:
        logger.exception("CISA KEV background sync failed: %s", exc)
        return {"success": False, "error": str(exc)}
    finally:
        db.close()
