"""Security history models — CVEs, KEV entries, security events."""
from __future__ import annotations

from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, Float, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, utcnow


class SecurityRelationshipType(str, Enum):
    """Canonical relationship between a security advisory/event and an organization."""
    DIRECT_COMPANY_EVENT = "DIRECT_COMPANY_EVENT"
    RELATED_PRODUCT_CONTEXT = "RELATED_PRODUCT_CONTEXT"
    RELATED_TECHNOLOGY_CONTEXT = "RELATED_TECHNOLOGY_CONTEXT"
    GLOBAL_KNOWLEDGE = "GLOBAL_KNOWLEDGE"
    UNVERIFIED = "UNVERIFIED"


class SecurityEvent(Base):
    __tablename__ = "security_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id"), nullable=True, index=True)
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id"), nullable=True, index=True)
    asset_id: Mapped[int | None] = mapped_column(ForeignKey("assets.id"), nullable=True, index=True)
    target_id: Mapped[int | None] = mapped_column(ForeignKey("targets.id"), nullable=True, index=True)

    cve_id: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    security_advisory_id: Mapped[int | None] = mapped_column(ForeignKey("security_advisories.id", ondelete="SET NULL"), nullable=True, index=True)
    relationship_type: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)  # VULNERABILITY_AFFECTS_PRODUCT, VULNERABILITY_AFFECTS_TECHNOLOGY, VENDOR_ADVISORY, SECURITY_EVENT
    vulnerability_class: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    affected_component: Mapped[str | None] = mapped_column(String(255), nullable=True)
    affected_versions: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)
    confidence: Mapped[float] = mapped_column(Float, default=0.9)
    evidence: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str] = mapped_column(String(64))
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    severity: Mapped[str | None] = mapped_column(String(32), nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    published: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    modified: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    references: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)
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


class KevEntry(Base):
    __tablename__ = "kev_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    cve_id: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    vendor: Mapped[str | None] = mapped_column(String(255), nullable=True)
    product: Mapped[str | None] = mapped_column(String(255), nullable=True)
    vulnerability_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    date_added: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ransomware_use: Mapped[str | None] = mapped_column(String(32), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
