"""Target model — approved observation domain."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, utcnow


class Target(Base):
    __tablename__ = "targets"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id"), nullable=True, index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    domain: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    company_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    program_source: Mapped[str | None] = mapped_column(String(128), nullable=True, default="Direct Authorization")
    authorization_source: Mapped[str | None] = mapped_column(Text, nullable=True)
    scope: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)
    scope_type: Mapped[str | None] = mapped_column(String(32), nullable=True, default="DOMAIN")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    authorization_record: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=dict)
    authorization_confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
    monitoring_status: Mapped[str] = mapped_column(String(32), default="active")
    last_visited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    company: Mapped["Company | None"] = relationship(back_populates="targets")
    snapshots: Mapped[list["Snapshot"]] = relationship(back_populates="target", cascade="all, delete-orphan")
