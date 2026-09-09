"""Background job for reconstructing company historical intelligence."""
from __future__ import annotations

import asyncio
import logging
from typing import Any
from app.db import SessionLocal
from app.services.historical_reconstruction_service import HistoricalReconstructionService

logger = logging.getLogger(__name__)


def reconstruct_company_history_job(company_id: int, stage: int = 1, db: Any = None) -> dict[str, Any]:
    """RQ background worker job for asynchronous historical reconstruction."""
    own_session = False
    if db is None:
        db = SessionLocal()
        own_session = True
    try:
        logger.info("Starting historical reconstruction job for company_id=%s (stage=%s)", company_id, stage)
        result = asyncio.run(
            HistoricalReconstructionService.reconstruct_company_history(db, company_id, stage=stage)
        )
        logger.info("Historical reconstruction job complete for company_id=%s: %s", company_id, result)
        return result
    except Exception as exc:
        logger.exception("Historical reconstruction job failed for company_id=%s: %s", company_id, exc)
        return {"status": "error", "message": str(exc), "company_id": company_id}
    finally:
        if own_session:
            db.close()

