"""Source Registry models for the Continuous Corporate Change Intelligence Platform.

Entities:
- CompanySource: Registered data feeds and endpoints monitored for a company
- RawSourceSnapshot: Immutable historical raw source payload with SHA-256 content hash
- SourceCollectionRun: Telemetry and execution metrics per collection attempt
- NormalizedSourceDocument: Extracted, normalized structured items from raw snapshot
- SourceHealth: Real-time and rolling health status for a source
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any
from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, utcnow

if TYPE_CHECKING:
    from .company import Company


class SourceType(str, Enum):
    OFFICIAL_PRODUCT_CHANGE = "OFFICIAL_PRODUCT_CHANGE"
    OFFICIAL_RELEASE = "OFFICIAL_RELEASE"
    OFFICIAL_API_CHANGELOG = "OFFICIAL_API_CHANGELOG"
    OFFICIAL_DEVELOPER_DOCS = "OFFICIAL_DEVELOPER_DOCS"
    OFFICIAL_SECURITY_ADVISORY = "OFFICIAL_SECURITY_ADVISORY"
    OFFICIAL_BLOG = "OFFICIAL_BLOG"
    OFFICIAL_GITHUB = "OFFICIAL_GITHUB"
    OFFICIAL_STATUS = "OFFICIAL_STATUS"
    OFFICIAL_ROADMAP = "OFFICIAL_ROADMAP"
    OFFICIAL_APP_STORE = "OFFICIAL_APP_STORE"
    OFFICIAL_PACKAGE_REGISTRY = "OFFICIAL_PACKAGE_REGISTRY"
    TECHNOGRAPHICS = "TECHNOGRAPHICS"
    DNS = "DNS"
    CERTIFICATE_TRANSPARENCY = "CERTIFICATE_TRANSPARENCY"
    INTERNET_OBSERVATION = "INTERNET_OBSERVATION"
    CODE_ACTIVITY = "CODE_ACTIVITY"
    DEPENDENCY_INTELLIGENCE = "DEPENDENCY_INTELLIGENCE"
    VULNERABILITY_INTELLIGENCE = "VULNERABILITY_INTELLIGENCE"
    JOB_SIGNAL = "JOB_SIGNAL"
    PATENT_SIGNAL = "PATENT_SIGNAL"
    COMMUNITY = "COMMUNITY"
    THIRD_PARTY_ENRICHMENT = "THIRD_PARTY_ENRICHMENT"
    SOCIAL_SIGNAL = "SOCIAL_SIGNAL"


class SourceAuthorityLevel(str, Enum):
    DIRECT_PRODUCTION_OBSERVATION = "DIRECT_PRODUCTION_OBSERVATION"
    OFFICIAL_SECURITY_ADVISORY = "OFFICIAL_SECURITY_ADVISORY"
    OFFICIAL_RELEASE = "OFFICIAL_RELEASE"
    OFFICIAL_DOCUMENTATION = "OFFICIAL_DOCUMENTATION"
    OFFICIAL_GITHUB = "OFFICIAL_GITHUB"
    RECOGNIZED_SECURITY_DATABASE = "RECOGNIZED_SECURITY_DATABASE"
    PUBLIC_DISCLOSURE = "PUBLIC_DISCLOSURE"
    COMMUNITY_REPORT = "COMMUNITY_REPORT"
    THIRD_PARTY_REFERENCE = "THIRD_PARTY_REFERENCE"
    HEURISTIC = "HEURISTIC"


class SourceStatus(str, Enum):
    NEVER_CHECKED = "NEVER_CHECKED"
    SCHEDULED = "SCHEDULED"
    RUNNING = "RUNNING"
    SUCCESS_UNCHANGED = "SUCCESS_UNCHANGED"
    SUCCESS_CHANGED = "SUCCESS_CHANGED"
    RATE_LIMITED = "RATE_LIMITED"
    RETRYING = "RETRYING"
    FAILED = "FAILED"
    DISABLED = "DISABLED"


class SourceHealthState(str, Enum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    FAILED = "FAILED"
    DISABLED = "DISABLED"


class CompanyTrackingState(str, Enum):
    INITIALIZING = "INITIALIZING"
    TRACKING = "TRACKING"
    PARTIAL = "PARTIAL"
    DEGRADED = "DEGRADED"
    STALE = "STALE"
    PAUSED = "PAUSED"


class CompanySource(Base):
    """First-class source registry record tracking a monitored corporate data source."""
    __tablename__ = "company_sources"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    source_url: Mapped[str] = mapped_column(Text)
    source_type: Mapped[str] = mapped_column(String(64), index=True, default=SourceType.OFFICIAL_PRODUCT_CHANGE.value)
    source_subtype: Mapped[str | None] = mapped_column(String(64), nullable=True)
    authority_level: Mapped[str] = mapped_column(String(64), index=True, default=SourceAuthorityLevel.OFFICIAL_RELEASE.value)
    product_scope: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    platform_scope: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    parser_strategy: Mapped[str] = mapped_column(String(64), default="generic_feed")
    collection_method: Mapped[str] = mapped_column(String(64), default="POLL")
    feed_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    api_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    repository_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    requires_auth: Mapped[bool] = mapped_column(Boolean, default=False)
    credential_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    poll_interval_seconds: Mapped[int] = mapped_column(Integer, default=600)  # 10 minutes default
    priority: Mapped[str] = mapped_column(String(16), default="P2", index=True)  # P0, P1, P2, P3, P4
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    status: Mapped[str] = mapped_column(String(32), default=SourceStatus.NEVER_CHECKED.value, index=True)

    # State & Caching
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_changed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_check_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    etag: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_modified: Mapped[str | None] = mapped_column(String(255), nullable=True)
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    parser_version: Mapped[str] = mapped_column(String(32), default="1.0.0")
    consecutive_failures: Mapped[int] = mapped_column(Integer, default=0)
    rate_limit_state: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_http_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Capability and Policy
    coverage_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    coverage_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    historical_capability: Mapped[bool] = mapped_column(Boolean, default=False)
    realtime_capability: Mapped[bool] = mapped_column(Boolean, default=False)
    terms_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    robots_policy: Mapped[str | None] = mapped_column(String(64), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    # Relationships
    company: Mapped["Company"] = relationship("Company", back_populates="sources")
    runs: Mapped[list["SourceCollectionRun"]] = relationship("SourceCollectionRun", back_populates="source", cascade="all, delete-orphan")
    snapshots: Mapped[list["RawSourceSnapshot"]] = relationship("RawSourceSnapshot", back_populates="source", cascade="all, delete-orphan")
    health: Mapped["SourceHealth | None"] = relationship("SourceHealth", back_populates="source", uselist=False, cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("company_id", "source_url", name="uq_company_source_url"),
        Index("ix_company_sources_due", "enabled", "next_check_at"),
    )


class RawSourceSnapshot(Base):
    """Immutable raw content snapshot preserved with SHA-256 integrity hash."""
    __tablename__ = "raw_source_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("company_sources.id", ondelete="CASCADE"), index=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    url: Mapped[str] = mapped_column(Text)
    http_status: Mapped[int] = mapped_column(Integer, default=200)
    etag: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_modified: Mapped[str | None] = mapped_column(String(255), nullable=True)
    content_type: Mapped[str] = mapped_column(String(128), default="application/json")
    content_hash: Mapped[str] = mapped_column(String(64), index=True)  # SHA-256
    body_raw: Mapped[str] = mapped_column(Text)
    body_size: Mapped[int] = mapped_column(Integer, default=0)
    parser_version: Mapped[str] = mapped_column(String(32), default="1.0.0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    # Relationships
    source: Mapped["CompanySource"] = relationship("CompanySource", back_populates="snapshots")
    normalized_docs: Mapped[list["NormalizedSourceDocument"]] = relationship("NormalizedSourceDocument", back_populates="raw_snapshot", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_raw_snapshots_source_hash", "source_id", "content_hash"),
    )


class SourceCollectionRun(Base):
    """Execution log, metrics, and cost record for a single source poll or webhook trigger."""
    __tablename__ = "source_collection_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("company_sources.id", ondelete="CASCADE"), index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(32), index=True)  # SUCCESS_CHANGED, SUCCESS_UNCHANGED, FAILED, RATE_LIMITED
    http_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    items_found: Mapped[int] = mapped_column(Integer, default=0)
    items_changed: Mapped[int] = mapped_column(Integer, default=0)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_snapshot_id: Mapped[int | None] = mapped_column(ForeignKey("raw_source_snapshots.id", ondelete="SET NULL"), nullable=True)

    # Cost & provider attribution
    credits_used: Mapped[float] = mapped_column(Float, default=0.0)
    request_count: Mapped[int] = mapped_column(Integer, default=1)
    response_bytes: Mapped[int] = mapped_column(Integer, default=0)
    estimated_cost: Mapped[float] = mapped_column(Float, default=0.0)

    # Relationships
    source: Mapped["CompanySource"] = relationship("CompanySource", back_populates="runs")


class NormalizedSourceDocument(Base):
    """Normalized structured document extracted from a raw source snapshot."""
    __tablename__ = "normalized_source_documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    raw_snapshot_id: Mapped[int] = mapped_column(ForeignKey("raw_source_snapshots.id", ondelete="CASCADE"), index=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("company_sources.id", ondelete="CASCADE"), index=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(512))
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_type: Mapped[str] = mapped_column(String(64), default="structured_change")
    extracted_items: Mapped[list | dict] = mapped_column(JSON, default=list)
    parsed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    parser_name: Mapped[str] = mapped_column(String(64), default="default")
    parser_version: Mapped[str] = mapped_column(String(32), default="1.0.0")

    # Relationships
    raw_snapshot: Mapped["RawSourceSnapshot"] = relationship("RawSourceSnapshot", back_populates="normalized_docs")


class SourceHealth(Base):
    """Aggregated health metrics and status for an individual source."""
    __tablename__ = "source_health"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("company_sources.id", ondelete="CASCADE"), unique=True, index=True)
    health_state: Mapped[str] = mapped_column(String(32), default=SourceHealthState.HEALTHY.value, index=True)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    consecutive_failures: Mapped[int] = mapped_column(Integer, default=0)
    failure_rate: Mapped[float] = mapped_column(Float, default=0.0)
    change_rate: Mapped[float] = mapped_column(Float, default=0.0)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    # Relationships
    source: Mapped["CompanySource"] = relationship("CompanySource", back_populates="health")
