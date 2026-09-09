"""Researcher Export Center models."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone, timedelta
from enum import Enum
from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, utcnow


class ExportType(str, Enum):
    COMPANY_INTELLIGENCE = "COMPANY_INTELLIGENCE"
    VULNERABILITY_INTELLIGENCE = "VULNERABILITY_INTELLIGENCE"
    HISTORICAL_TIMELINE = "HISTORICAL_TIMELINE"
    ATTACK_SURFACE_CHANGES = "ATTACK_SURFACE_CHANGES"
    RESEARCH_SIGNALS = "RESEARCH_SIGNALS"
    SCOPE_EXPORT = "SCOPE_EXPORT"
    EVIDENCE_PACK = "EVIDENCE_PACK"
    FULL_RESEARCH_DATASET = "FULL_RESEARCH_DATASET"


class ExportFormat(str, Enum):
    JSON = "JSON"
    CSV = "CSV"
    NDJSON = "NDJSON"
    ZIP = "ZIP"


class ExportStatus(str, Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    READY = "READY"
    FAILED = "FAILED"
    EXPIRED = "EXPIRED"


def default_expiration() -> datetime:
    return datetime.now(timezone.utc) + timedelta(hours=24)


class ExportJob(Base):
    """Tracks researcher export jobs, signed tokens, checksums, and artifact storage."""
    __tablename__ = "export_jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    export_uuid: Mapped[str] = mapped_column(String(36), default=lambda: str(uuid.uuid4()), unique=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    export_type: Mapped[str] = mapped_column(String(64), index=True, default=ExportType.COMPANY_INTELLIGENCE.value)
    format: Mapped[str] = mapped_column(String(16), default=ExportFormat.JSON.value)
    status: Mapped[str] = mapped_column(String(32), default=ExportStatus.QUEUED.value, index=True)

    # Job parameters & metrics
    filters: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=dict)
    scope: Mapped[str | None] = mapped_column(String(64), nullable=True)
    row_count: Mapped[int] = mapped_column(Integer, default=0)
    file_size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    checksum_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    file_path: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Access control & expiration
    download_token: Mapped[str] = mapped_column(String(64), default=lambda: uuid.uuid4().hex, unique=True, index=True)
    download_count: Mapped[int] = mapped_column(Integer, default=0)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=default_expiration, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    user: Mapped["User"] = relationship()

    __table_args__ = (
        Index("ix_export_jobs_user_status", "user_id", "status"),
    )
