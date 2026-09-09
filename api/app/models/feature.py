"""Feature tracking models."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, utcnow


class Feature(Base):
    __tablename__ = "features"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id"), nullable=True, index=True)
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id"), nullable=True, index=True)
    asset_id: Mapped[int | None] = mapped_column(ForeignKey("assets.id"), nullable=True, index=True)
    target_id: Mapped[int | None] = mapped_column(ForeignKey("targets.id"), nullable=True, index=True)

    name: Mapped[str] = mapped_column(String(255))
    category: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    first_observed: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_observed: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    status: Mapped[str] = mapped_column(String(32), default="NEW")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.9)
    affected_assets: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)
    source_ids: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)
    evidence_ids: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)

    product: Mapped["Product | None"] = relationship(back_populates="features")
    observations: Mapped[list["FeatureObservation"]] = relationship(cascade="all, delete-orphan")


class FeatureObservation(Base):
    __tablename__ = "feature_observations"

    id: Mapped[int] = mapped_column(primary_key=True)
    feature_id: Mapped[int] = mapped_column(ForeignKey("features.id"), index=True)
    snapshot_id: Mapped[int | None] = mapped_column(ForeignKey("snapshots.id"), nullable=True)
    evidence_ids: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)
    source_ids: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
