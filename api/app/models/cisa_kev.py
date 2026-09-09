"""CISA Known Exploited Vulnerabilities (KEV) models.

Represents immutable raw snapshots of the official CISA KEV feed and exact
source-faithful normalized items with zero data fabrication.
"""
from __future__ import annotations

from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, utcnow


class CISAFeedSnapshot(Base):
    """Immutable raw content snapshot of the official CISA KEV feed."""
    __tablename__ = "cisa_feed_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_url: Mapped[str] = mapped_column(Text)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    http_status: Mapped[int] = mapped_column(Integer, default=200)
    content_sha256: Mapped[str] = mapped_column(String(64), index=True)
    catalog_version: Mapped[str] = mapped_column(String(64), index=True)
    date_released: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    declared_count: Mapped[int] = mapped_column(Integer, default=0)
    raw_payload: Mapped[str] = mapped_column(Text)  # Immutable raw response JSON
    parser_version: Mapped[str] = mapped_column(String(32), default="1.0.0")
    fetch_duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    success: Mapped[bool] = mapped_column(Boolean, default=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    # Relationships
    items: Mapped[list["CISAKEVItem"]] = relationship(back_populates="snapshot")

    __table_args__ = (
        Index("ix_cisa_snapshots_hash", "content_sha256"),
        Index("ix_cisa_snapshots_version", "catalog_version"),
    )


class CISAKEVItem(Base):
    """Normalized, exact source-faithful CISA KEV vulnerability record."""
    __tablename__ = "cisa_kev_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    cve_id: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    vendor_project: Mapped[str] = mapped_column(String(255), index=True)
    product: Mapped[str] = mapped_column(String(255), index=True)
    vulnerability_name: Mapped[str] = mapped_column(Text)
    date_added: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    short_description: Mapped[str] = mapped_column(Text)
    required_action: Mapped[str | None] = mapped_column(Text, nullable=True)
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    known_ransomware_campaign_use: Mapped[str | None] = mapped_column(String(32), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    cwes: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)

    # Catalog progression & provenance
    first_seen_catalog_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_seen_catalog_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    source_snapshot_id: Mapped[int | None] = mapped_column(ForeignKey("cisa_feed_snapshots.id", ondelete="SET NULL"), nullable=True, index=True)
    raw_source_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    data_origin: Mapped[str] = mapped_column(String(32), default="SOURCE_VERIFIED")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)  # Still present in latest catalog

    # Relationships
    snapshot: Mapped["CISAFeedSnapshot | None"] = relationship(back_populates="items")

    __table_args__ = (
        Index("ix_cisa_kev_vendor_product", "vendor_project", "product"),
        Index("ix_cisa_kev_date_added", "date_added"),
    )
