"""Security Knowledge Base models — Advisories, References, CWEs, OWASP, Sources, and Private Tenant Programs."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Table,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, utcnow

# Many-to-Many Association: SecurityAdvisory <-> CWEEntry
advisory_cwe_association = Table(
    "advisory_cwe_association",
    Base.metadata,
    Column("advisory_id", Integer, ForeignKey("security_advisories.id", ondelete="CASCADE"), primary_key=True),
    Column("cwe_id", Integer, ForeignKey("cwe_entries.id", ondelete="CASCADE"), primary_key=True),
)

# Association: CWEEntry <-> OWASPCategory
cwe_owasp_association = Table(
    "cwe_owasp_association",
    Base.metadata,
    Column("cwe_id", Integer, ForeignKey("cwe_entries.id", ondelete="CASCADE"), primary_key=True),
    Column("owasp_category_id", Integer, ForeignKey("owasp_categories.id", ondelete="CASCADE"), primary_key=True),
    Column("mapping_type", String(32), default="OFFICIAL_OWASP", nullable=False),
    Column("confidence", Float, default=1.0, nullable=False),
)

# Many-to-Many Association: SecurityAdvisory <-> OWASPCategory
advisory_owasp_association = Table(
    "advisory_owasp_association",
    Base.metadata,
    Column("advisory_id", Integer, ForeignKey("security_advisories.id", ondelete="CASCADE"), primary_key=True),
    Column("owasp_category_id", Integer, ForeignKey("owasp_categories.id", ondelete="CASCADE"), primary_key=True),
)


class CWEEntry(Base):
    """Canonical Common Weakness Enumeration (CWE) entry."""
    __tablename__ = "cwe_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    cwe_id: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)  # e.g., "CWE-287"
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str | None] = mapped_column(String(64), default="MITRE", nullable=True)
    source_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    # Relationships
    advisories: Mapped[list[SecurityAdvisory]] = relationship(
        "SecurityAdvisory",
        secondary=advisory_cwe_association,
        back_populates="cwes",
    )
    owasp_categories: Mapped[list[OWASPCategory]] = relationship(
        "OWASPCategory",
        secondary=cwe_owasp_association,
        back_populates="cwes",
    )


class OWASPCategory(Base):
    """Versioned OWASP Taxonomy category (e.g., OWASP 2021 A01 Broken Access Control)."""
    __tablename__ = "owasp_categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    taxonomy: Mapped[str] = mapped_column(String(32), default="OWASP", nullable=False)
    taxonomy_version: Mapped[str] = mapped_column(String(32), index=True, nullable=False)  # e.g., "2021", "2025"
    category_id: Mapped[str] = mapped_column(String(32), index=True, nullable=False)  # e.g., "A01", "A01:2021"
    category_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    # Relationships
    cwes: Mapped[list[CWEEntry]] = relationship(
        "CWEEntry",
        secondary=cwe_owasp_association,
        back_populates="owasp_categories",
    )
    advisories: Mapped[list[SecurityAdvisory]] = relationship(
        "SecurityAdvisory",
        secondary=advisory_owasp_association,
        back_populates="owasp_categories",
    )


class SecurityAdvisory(Base):
    """Global Security Knowledge advisory record (e.g. CISA KEV, NVD, OSV, GHSA).
    
    Distinct from company-specific SecurityEvents.
    """
    __tablename__ = "security_advisories"

    id: Mapped[int] = mapped_column(primary_key=True)
    canonical_id: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    provider: Mapped[str] = mapped_column(String(64), index=True, nullable=False)  # CISA_KEV, NVD, OSV, GHSA
    provider_record_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    cve_id: Mapped[str | None] = mapped_column(String(32), index=True, nullable=True)
    ghsa_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)

    title: Mapped[str] = mapped_column(String(512), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    vendor: Mapped[str | None] = mapped_column(String(255), index=True, nullable=True)
    product: Mapped[str | None] = mapped_column(String(255), index=True, nullable=True)
    affected_versions: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)

    severity: Mapped[str | None] = mapped_column(String(32), nullable=True)
    cvss_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    modified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    date_added: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    known_ransomware_use: Mapped[str | None] = mapped_column(String(32), nullable=True)
    forensic_triage: Mapped[str | None] = mapped_column(String(32), nullable=True)

    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    raw_payload_reference: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=dict)
    confidence: Mapped[float] = mapped_column(Float, default=0.95, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    # Relationships
    references: Mapped[list[VulnerabilityReference]] = relationship(
        "VulnerabilityReference",
        back_populates="advisory",
        cascade="all, delete-orphan",
    )
    cwes: Mapped[list[CWEEntry]] = relationship(
        "CWEEntry",
        secondary=advisory_cwe_association,
        back_populates="advisories",
    )
    owasp_categories: Mapped[list[OWASPCategory]] = relationship(
        "OWASPCategory",
        secondary=advisory_owasp_association,
        back_populates="advisories",
    )



class VulnerabilityReference(Base):
    """Cross-provider identifier and document reference."""
    __tablename__ = "vulnerability_references"

    id: Mapped[int] = mapped_column(primary_key=True)
    advisory_id: Mapped[int] = mapped_column(ForeignKey("security_advisories.id", ondelete="CASCADE"), index=True, nullable=False)
    reference_type: Mapped[str] = mapped_column(String(32), index=True, nullable=False)  # CVE, GHSA, NVD, VENDOR, BOD, URL
    reference_value: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    advisory: Mapped[SecurityAdvisory] = relationship("SecurityAdvisory", back_populates="references")


class KnowledgeSource(Base):
    """External vulnerability intelligence feed/source catalog tracking."""
    __tablename__ = "knowledge_sources"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_type: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)  # CISA_KEV, NVD, OSV, GHSA, OWASP, CWE
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    retrieved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    record_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="ACTIVE", nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    sync_runs: Mapped[list[KnowledgeSyncRun]] = relationship(
        "KnowledgeSyncRun",
        back_populates="source",
        cascade="all, delete-orphan",
    )


class KnowledgeSyncRun(Base):
    """Telemetry and observability record for a single knowledge synchronization run."""
    __tablename__ = "knowledge_sync_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("knowledge_sources.id", ondelete="CASCADE"), index=True, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="QUEUED", index=True, nullable=False)  # QUEUED, RUNNING, COMPLETED, FAILED, PARTIAL
    records_seen: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    records_created: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    records_updated: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    records_skipped: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    records_failed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=dict)

    source: Mapped[KnowledgeSource] = relationship("KnowledgeSource", back_populates="sync_runs")


# =========================================================================
# PRIVATE TENANT PROGRAM ARCHITECTURE (Phases 22 - 23)
# Segregated from global public knowledge.
# =========================================================================

class PrivateProgram(Base):
    """Tenant-isolated private bug bounty program."""
    __tablename__ = "private_programs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    platform: Mapped[str] = mapped_column(String(64), nullable=False)  # HACKERONE, BUGCROWD, INTIGRI, INTERNAL
    external_program_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    program_name: Mapped[str] = mapped_column(String(255), nullable=False)
    handle: Mapped[str | None] = mapped_column(String(128), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    program_metadata: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    reports: Mapped[list[PrivateReport]] = relationship("PrivateReport", back_populates="program", cascade="all, delete-orphan")
    scope_rules: Mapped[list[PrivateScopeRule]] = relationship("PrivateScopeRule", back_populates="program", cascade="all, delete-orphan")


class PrivateReport(Base):
    """Tenant-isolated private vulnerability disclosure report."""
    __tablename__ = "private_reports"

    id: Mapped[int] = mapped_column(primary_key=True)
    program_id: Mapped[int] = mapped_column(ForeignKey("private_programs.id", ondelete="CASCADE"), index=True, nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    external_report_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    severity: Mapped[str | None] = mapped_column(String(32), nullable=True)
    state: Mapped[str | None] = mapped_column(String(64), nullable=True)
    disclosed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    program: Mapped[PrivateProgram] = relationship("PrivateProgram", back_populates="reports")


class PrivateFinding(Base):
    """Tenant-isolated researcher finding."""
    __tablename__ = "private_findings"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    program_id: Mapped[int | None] = mapped_column(ForeignKey("private_programs.id", ondelete="SET NULL"), index=True, nullable=True)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    vulnerability_class: Mapped[str | None] = mapped_column(String(64), nullable=True)
    affected_asset: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class PrivateScopeRule(Base):
    """Tenant-isolated private program scope rules."""
    __tablename__ = "private_scope_rules"

    id: Mapped[int] = mapped_column(primary_key=True)
    program_id: Mapped[int] = mapped_column(ForeignKey("private_programs.id", ondelete="CASCADE"), index=True, nullable=False)
    target_pattern: Mapped[str] = mapped_column(String(255), nullable=False)
    scope_type: Mapped[str] = mapped_column(String(32), default="IN_SCOPE", nullable=False)
    instruction: Mapped[str | None] = mapped_column(Text, nullable=True)
    valid_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    valid_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    program: Mapped[PrivateProgram] = relationship("PrivateProgram", back_populates="scope_rules")


class BountyEvidence(Base):
    """Verified public bug bounty award record and provenance for a vulnerability class."""
    __tablename__ = "bounty_evidence"

    id: Mapped[int] = mapped_column(primary_key=True)
    vulnerability_class: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    source: Mapped[str] = mapped_column(String(128), nullable=False)
    source_type: Mapped[str] = mapped_column(String(64), default="PUBLIC_DISCLOSURE")
    program_name: Mapped[str] = mapped_column(String(128), nullable=False)
    program_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    award_amount: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(16), default="USD")
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    cve_id: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    measurement_type: Mapped[str] = mapped_column(String(32), default="OBSERVED")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_payload_reference: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
