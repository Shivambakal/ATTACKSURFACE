"""Durable accounting for an explicitly authorized 50-target trial."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, utcnow


class TrialRun(Base):
    __tablename__ = "trial_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128), default="50 Target Trial")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    window_hours: Mapped[int] = mapped_column(Integer, default=24)
    status: Mapped[str] = mapped_column(String(32), default="created", index=True)
    registry_source: Mapped[str] = mapped_column(Text)
    meta: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True, default=dict)

    targets: Mapped[list["TrialTarget"]] = relationship(back_populates="run", cascade="all, delete-orphan")


class TrialTarget(Base):
    __tablename__ = "trial_targets"

    id: Mapped[int] = mapped_column(primary_key=True)
    trial_run_id: Mapped[int] = mapped_column(ForeignKey("trial_runs.id"), index=True)
    target_id: Mapped[int] = mapped_column(ForeignKey("targets.id"), index=True)
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id"), nullable=True, index=True)
    company_name: Mapped[str] = mapped_column(String(255))
    primary_domain: Mapped[str] = mapped_column(String(255))
    scope: Mapped[list] = mapped_column(JSON, default=list)
    authorization_source: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(128))
    collection_status: Mapped[str] = mapped_column(String(32), default="queued", index=True)
    last_successful_collection: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    meta: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True, default=dict)

    run: Mapped[TrialRun] = relationship(back_populates="targets")

    __table_args__ = (UniqueConstraint("trial_run_id", "target_id", name="uq_trial_target_run_target"),)