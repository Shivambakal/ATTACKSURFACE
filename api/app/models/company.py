"""Company / Organization model — root entity for the attack surface graph."""
from __future__ import annotations

from datetime import datetime
from sqlalchemy import DateTime, Float, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, utcnow


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    canonical_domain: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    legal_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    industry: Mapped[str | None] = mapped_column(String(128), nullable=True)
    country: Mapped[str | None] = mapped_column(String(64), nullable=True)
    logo_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    website_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    security_policy_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    bug_bounty_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    disclosure_policy_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_confidence: Mapped[float] = mapped_column(Float, default=1.0)
    aliases: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)
    meta: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True, default=dict)
    last_enriched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    tracking_status: Mapped[str] = mapped_column(String(32), default="INITIALIZING")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    def __setattr__(self, name, value):
        if name == "metadata":
            name = "meta"
        super().__setattr__(name, value)

    def __getattr__(self, name):
        if name == "metadata":
            return self.meta
        raise AttributeError(name)

    # Relationships
    security_programs: Mapped[list["SecurityProgram"]] = relationship(
        back_populates="company", cascade="all, delete-orphan"
    )
    products: Mapped[list["Product"]] = relationship(
        back_populates="company", cascade="all, delete-orphan"
    )
    assets: Mapped[list["Asset"]] = relationship(
        back_populates="company", cascade="all, delete-orphan"
    )
    targets: Mapped[list["Target"]] = relationship(
        back_populates="company"
    )
    research_signals: Mapped[list["ResearchSignal"]] = relationship(
        back_populates="company", cascade="all, delete-orphan"
    )
    historical_coverage: Mapped["HistoricalCoverage | None"] = relationship(
        "HistoricalCoverage", back_populates="company", uselist=False, cascade="all, delete-orphan"
    )
    historical_releases: Mapped[list["HistoricalRelease"]] = relationship(
        "HistoricalRelease", back_populates="company", cascade="all, delete-orphan"
    )
    sources: Mapped[list["CompanySource"]] = relationship(
        "CompanySource", back_populates="company", cascade="all, delete-orphan"
    )
