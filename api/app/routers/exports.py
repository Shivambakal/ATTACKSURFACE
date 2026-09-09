"""Researcher Export Center API Router."""
from __future__ import annotations

import os
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..db import get_db
from ..models.user import User
from ..routers.deps import get_current_user, get_optional_user
from ..services.export_service import ExportService

router = APIRouter(
    prefix="/api/v1/exports",
    tags=["Researcher Export Center"],
)


class CreateExportRequest(BaseModel):
    export_type: str
    format: str = "JSON"
    filters: dict[str, Any] | None = None
    scope: str | None = "ALL"


class ExportJobResponse(BaseModel):
    id: int
    export_uuid: str
    export_type: str
    format: str
    status: str
    row_count: int
    file_size_bytes: int
    checksum_sha256: str | None
    download_token: str
    download_url: str
    download_count: int
    expires_at: str
    created_at: str
    completed_at: str | None
    error_message: str | None


def _serialize_job(job: Any) -> dict[str, Any]:
    return {
        "id": job.id,
        "export_uuid": job.export_uuid,
        "export_type": job.export_type,
        "format": job.format,
        "status": job.status,
        "row_count": job.row_count,
        "file_size_bytes": job.file_size_bytes,
        "checksum_sha256": job.checksum_sha256,
        "download_token": job.download_token,
        "download_url": f"/api/v1/exports/download/{job.download_token}",
        "download_count": job.download_count,
        "expires_at": job.expires_at.isoformat() if job.expires_at else "",
        "created_at": job.created_at.isoformat() if job.created_at else "",
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        "error_message": job.error_message,
    }


@router.post("/create", response_model=dict[str, Any], status_code=status.HTTP_201_CREATED)
def create_export(
    payload: CreateExportRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Requests generation of a researcher export package."""
    service = ExportService(db)
    try:
        job = service.create_export_job(
            user_id=current_user.id,
            export_type=payload.export_type,
            export_format=payload.format,
            filters=payload.filters,
            scope=payload.scope,
        )
        # Execute synchronously for responsiveness; in background worker for heavy tasks
        job = service.execute_job(job.id)
        return _serialize_job(job)
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err))


@router.get("", response_model=list[dict[str, Any]])
def list_my_exports(
    limit: int = Query(default=50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    """Returns all export jobs created by the authenticated researcher."""
    service = ExportService(db)
    jobs = service.get_user_exports(user_id=current_user.id, limit=limit)
    return [_serialize_job(j) for j in jobs]


@router.get("/{job_id}", response_model=dict[str, Any])
def get_export_status(
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Retrieves status and metadata for a specific export job."""
    from ..models.export import ExportJob
    job = db.get(ExportJob, job_id)
    if not job or (job.user_id != current_user.id and not current_user.is_admin):
        raise HTTPException(status_code=404, detail="Export job not found or unauthorized.")
    return _serialize_job(job)


@router.get("/download/{download_token}")
def download_export_file(
    download_token: str,
    current_user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    """Securely streams the export artifact if the token is valid, unexpired, and authorized."""
    service = ExportService(db)
    try:
        job = service.get_export_by_token(
            download_token=download_token,
            user_id=current_user.id if current_user else None,
            is_admin=current_user.is_admin if current_user else False,
        )
    except PermissionError as p_err:
        raise HTTPException(status_code=403, detail=str(p_err))
    except ValueError as v_err:
        raise HTTPException(status_code=400, detail=str(v_err))

    filename = os.path.basename(job.file_path)
    media_type = "application/octet-stream"
    if job.format == "JSON":
        media_type = "application/json"
    elif job.format == "CSV":
        media_type = "text/csv"
    elif job.format == "ZIP":
        media_type = "application/zip"

    return FileResponse(
        path=job.file_path,
        filename=filename,
        media_type=media_type,
        headers={
            "X-Checksum-SHA256": job.checksum_sha256 or "",
            "X-Export-ID": job.export_uuid,
        },
    )
