"""ApiSurface model — tracks documented and observed API endpoints and schemas."""
from __future__ import annotations

from datetime import datetime
from sqlalchemy import DateTime, Float, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, utcnow


class ApiSurface(Base):
    __tablename__ = "api_surfaces"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id"), nullable=True, index=True)
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id"), nullable=True, index=True)
    asset_id: Mapped[int | None] = mapped_column(ForeignKey("assets.id"), nullable=True, index=True)
    target_id: Mapped[int | None] = mapped_column(ForeignKey("targets.id"), nullable=True, index=True)

    method: Mapped[str] = mapped_column(String(16), default="GET", index=True)
    path: Mapped[str] = mapped_column(String(512), index=True)
    version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    auth_requirement: Mapped[str | None] = mapped_column(String(64), nullable=True)
    parameters: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)
    request_schema: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=dict)
    response_schema: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=dict)
    source: Mapped[str] = mapped_column(String(64), default="documentation")
    confidence: Mapped[float] = mapped_column(Float, default=0.9)
    evidence_ids: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)
    first_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    status: Mapped[str] = mapped_column(String(32), default="ACTIVE")

    product: Mapped["Product | None"] = relationship(back_populates="api_surfaces")
