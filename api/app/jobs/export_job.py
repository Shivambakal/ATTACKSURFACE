"""Export processing background job."""
from __future__ import annotations

import logging
from ..db import SessionLocal
from ..services.export_service import ExportService

logger = logging.getLogger(__name__)


def run_export_job(job_id: int) -> dict:
    """Executes chunked artifact generation for an export job in background worker."""
    db = SessionLocal()
    try:
        logger.info("Starting background export generation for job #%d", job_id)
        service = ExportService(db)
        job = service.execute_job(job_id)
        logger.info("Export job #%d finished with status: %s", job_id, job.status)
        return {
            "job_id": job.id,
            "status": job.status,
            "row_count": job.row_count,
            "file_size": job.file_size_bytes,
            "checksum": job.checksum_sha256,
        }
    except Exception as exc:
        logger.exception("Export background job #%d failed: %s", job_id, exc)
        return {"job_id": job_id, "status": "FAILED", "error": str(exc)}
    finally:
        db.close()
