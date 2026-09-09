"""Product model for organization software, cloud, and service suites."""
from __future__ import annotations

from datetime import datetime
from sqlalchemy import DateTime, Float, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, utcnow


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    domain_ids: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)
    source_urls: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)
    confidence: Mapped[float] = mapped_column(Float, default=0.9)
    status: Mapped[str] = mapped_column(String(32), default="ACTIVE")
    meta: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True, default=dict)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    company: Mapped["Company"] = relationship(back_populates="products")
    features: Mapped[list["Feature"]] = relationship(back_populates="product")
    api_surfaces: Mapped[list["ApiSurface"]] = relationship(back_populates="product")
