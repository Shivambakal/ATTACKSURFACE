"""Security program and scope rules models."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, utcnow


class InclusionType(str, Enum):
    INCLUDE = "INCLUDE"
    EXCLUDE = "EXCLUDE"
    CONDITIONAL = "CONDITIONAL"
    UNKNOWN = "UNKNOWN"


class ScopeStatus(str, Enum):
    IN_SCOPE = "IN_SCOPE"
    RELATED = "RELATED"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"
    UNKNOWN = "UNKNOWN"
    PENDING_VERIFICATION = "PENDING_VERIFICATION"


class VerificationStatus(str, Enum):
    VERIFIED = "VERIFIED"
    PARTIALLY_VERIFIED = "PARTIALLY_VERIFIED"
    UNVERIFIED = "UNVERIFIED"
    STALE = "STALE"


class SecurityProgram(Base):
    __tablename__ = "security_programs"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    platform: Mapped[str] = mapped_column(String(64), default="Self-Hosted", index=True)
    program_name: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    program_handle: Mapped[str | None] = mapped_column(String(128), index=True, nullable=True)
    program_type: Mapped[str] = mapped_column(String(64), default="BUG_BOUNTY", index=True)
    program_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    policy_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="ACTIVE", index=True)
    is_public: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    offers_bounties: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    min_bounty: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_bounty: Mapped[float | None] = mapped_column(Float, nullable=True)
    currency: Mapped[str] = mapped_column(String(16), default="USD")
    submission_state: Mapped[str] = mapped_column(String(32), default="OPEN", index=True)
    scope_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    meta: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True, default=dict)
    discovered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    company: Mapped["Company"] = relationship(back_populates="security_programs")
    rules: Mapped[list["ProgramScopeRule"]] = relationship(
        back_populates="program", cascade="all, delete-orphan"
    )
    snapshots: Mapped[list["ProgramSnapshot"]] = relationship(
        back_populates="program", cascade="all, delete-orphan"
    )
    change_events: Mapped[list["ProgramChangeEvent"]] = relationship(
        back_populates="program", cascade="all, delete-orphan"
    )


class ProgramScopeRule(Base):
    __tablename__ = "program_scope_rules"

    id: Mapped[int] = mapped_column(primary_key=True)
    security_program_id: Mapped[int] = mapped_column(ForeignKey("security_programs.id"), index=True)
    pattern: Mapped[str] = mapped_column(String(255), index=True)
    asset_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    inclusion_type: Mapped[str] = mapped_column(String(32), default=InclusionType.INCLUDE.value, index=True)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.9)
    valid_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    valid_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    program: Mapped["SecurityProgram"] = relationship(back_populates="rules")


class ProgramSnapshot(Base):
    __tablename__ = "program_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    security_program_id: Mapped[int] = mapped_column(ForeignKey("security_programs.id", ondelete="CASCADE"), index=True)
    snapshot_hash: Mapped[str] = mapped_column(String(64), index=True)
    scope_count: Mapped[int] = mapped_column(default=0)
    scope_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    bounty_table: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=dict)
    raw_payload_reference: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=dict)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    program: Mapped["SecurityProgram"] = relationship(back_populates="snapshots")


class ProgramChangeEvent(Base):
    __tablename__ = "program_change_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    security_program_id: Mapped[int] = mapped_column(ForeignKey("security_programs.id", ondelete="CASCADE"), index=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    change_type: Mapped[str] = mapped_column(String(64), index=True)  # PROGRAM_SCOPE_ADDED, PROGRAM_SCOPE_REMOVED, PROGRAM_POLICY_CHANGED, PROGRAM_REWARD_CHANGED
    summary: Mapped[str] = mapped_column(String(512))
    diff_details: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=dict)
    evidence: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    program: Mapped["SecurityProgram"] = relationship(back_populates="change_events")

