"""ChangeCluster model — groups related changes into unified releases or product evolutions."""
from __future__ import annotations

from datetime import datetime
from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, utcnow


class ChangeCluster(Base):
    __tablename__ = "change_clusters"

    id: Mapped[int] = mapped_column(primary_key=True)
    target_id: Mapped[int | None] = mapped_column(ForeignKey("targets.id"), index=True, nullable=True)
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id"), index=True, nullable=True)
    title: Mapped[str] = mapped_column(String(255))
    summary: Mapped[str] = mapped_column(Text)
    cluster_type: Mapped[str] = mapped_column(String(64), default="product_release")
    primary_category: Mapped[str] = mapped_column(String(64))

    change_ids: Mapped[list] = mapped_column(JSON, default=list)
    affected_urls: Mapped[list] = mapped_column(JSON, default=list)
    source_count: Mapped[int] = mapped_column(Integer, default=1)
    confidence: Mapped[float] = mapped_column(Float, default=0.85)
    relevance_score: Mapped[int] = mapped_column(Integer, default=50)
    priority: Mapped[str] = mapped_column(String(16), default="MEDIUM")
    meta: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
