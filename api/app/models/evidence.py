"""Immutable evidence model.

Evidence records are never silently overwritten. Every AI summary
must be traceable back to evidence.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, utcnow


class Evidence(Base):
    __tablename__ = "evidence"

    id: Mapped[int] = mapped_column(primary_key=True)
    target_id: Mapped[int | None] = mapped_column(ForeignKey("targets.id"), nullable=True, index=True)
    source: Mapped[str] = mapped_column(String(64))
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    content_hash: Mapped[str] = mapped_column(String(64), index=True)
    before_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    after_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    evidence_type: Mapped[str] = mapped_column(String(64))
    excerpt: Mapped[str | None] = mapped_column(Text, nullable=True)
    meta: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True, default=dict)

    def __setattr__(self, name, value):
        if name == "metadata":
            name = "meta"
        super().__setattr__(name, value)

    def __getattr__(self, name):
        if name == "metadata":
            return self.meta
        raise AttributeError(name)
    collector_version: Mapped[str] = mapped_column(String(32), default="0.1")
