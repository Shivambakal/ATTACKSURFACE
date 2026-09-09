"""Change and ChangeEvidence models — detected diffs with immutable evidence."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, utcnow


class Change(Base):
    __tablename__ = "changes"

    id: Mapped[int] = mapped_column(primary_key=True)
    target_id: Mapped[int] = mapped_column(ForeignKey("targets.id"), index=True)
    snapshot_id: Mapped[int] = mapped_column(ForeignKey("snapshots.id"), index=True)
    fingerprint: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    category: Mapped[str] = mapped_column(String(64))
    confidence: Mapped[float] = mapped_column(Float)
    security_relevance: Mapped[int] = mapped_column(Integer)
    summary: Mapped[str] = mapped_column(Text)
    researcher_note: Mapped[str] = mapped_column(Text)
    source_url: Mapped[str] = mapped_column(Text)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    priority: Mapped[str] = mapped_column(String(16), default="MEDIUM")
    score_factors: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=dict)
    status: Mapped[str] = mapped_column(String(32), default="interesting")

    evidence: Mapped[list["ChangeEvidence"]] = relationship(cascade="all, delete-orphan")


class ChangeEvidence(Base):
    __tablename__ = "change_evidence"

    id: Mapped[int] = mapped_column(primary_key=True)
    change_id: Mapped[int] = mapped_column(ForeignKey("changes.id"), index=True)
    state: Mapped[str] = mapped_column(String(16))
    observation_id: Mapped[int | None] = mapped_column(ForeignKey("observations.id"), nullable=True)
    payload: Mapped[dict] = mapped_column(JSON)
