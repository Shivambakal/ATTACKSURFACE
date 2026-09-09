"""Timeline event model — unified view across all sources."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, utcnow


class TimelineEvent(Base):
    __tablename__ = "timeline_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id"), nullable=True, index=True)
    target_id: Mapped[int | None] = mapped_column(ForeignKey("targets.id"), nullable=True, index=True)
    event_type: Mapped[str] = mapped_column(String(64), index=True)
    title: Mapped[str] = mapped_column(Text)
    summary: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(64))
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    provenance_category: Mapped[str | None] = mapped_column(String(64), nullable=True)
    temporal_category: Mapped[str] = mapped_column(String(32), default="CURRENT")
    quality_badge: Mapped[str] = mapped_column(String(32), default="CONFIRMED_HISTORY")
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    effective_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    relevance_score: Mapped[int] = mapped_column(Integer, default=0)
    priority: Mapped[str] = mapped_column(String(16), default="INFO")
    affected_asset_ids: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)
    technology_ids: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)
    evidence_ids: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)
    related_change_ids: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)
    meta: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True, default=dict)

    def __setattr__(self, name, value):
        if name == "metadata":
            name = "meta"
        super().__setattr__(name, value)

    def __getattr__(self, name):
        if name == "metadata":
            return self.meta
        raise AttributeError(name)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
