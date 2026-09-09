"""Asset and Technology models for target and company infrastructure tracking."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, utcnow


class Asset(Base):
    __tablename__ = "assets"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id"), nullable=True, index=True)
    target_id: Mapped[int | None] = mapped_column(ForeignKey("targets.id"), nullable=True, index=True)

    name: Mapped[str] = mapped_column(String(255))
    hostname: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    normalized_hostname: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    scheme: Mapped[str | None] = mapped_column(String(16), default="https")
    url: Mapped[str | None] = mapped_column(Text, nullable=True)
    asset_type: Mapped[str] = mapped_column(String(64), default="SUBDOMAIN", index=True)
    parent_domain: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)

    source: Mapped[str] = mapped_column(String(64), default="discovery")
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.9)
    scope_status: Mapped[str] = mapped_column(String(32), default="UNKNOWN", index=True)
    verification_status: Mapped[str] = mapped_column(String(32), default="UNVERIFIED", index=True)
    lifecycle_status: Mapped[str] = mapped_column(String(32), default="ACTIVE", index=True)
    status: Mapped[str] = mapped_column(String(32), default="active")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    first_observed: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_observed: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    discovered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    meta: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True, default=dict)

    def __setattr__(self, name, value):
        if name == "metadata":
            name = "meta"
        super().__setattr__(name, value)

    def __getattr__(self, name):
        if name == "metadata":
            return self.meta
        raise AttributeError(name)

    company: Mapped["Company | None"] = relationship(back_populates="assets")
    evidence_records: Mapped[list["AssetEvidence"]] = relationship(
        back_populates="asset", cascade="all, delete-orphan"
    )
    technologies: Mapped[list["AssetTechnology"]] = relationship(cascade="all, delete-orphan")


class Technology(Base):
    __tablename__ = "technologies"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128), index=True)
    version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    category: Mapped[str | None] = mapped_column(String(64), nullable=True)
    first_observed: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_observed: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AssetTechnology(Base):
    __tablename__ = "asset_technologies"

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"), index=True)
    technology_id: Mapped[int] = mapped_column(ForeignKey("technologies.id"), index=True)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
