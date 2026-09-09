"""Security Intelligence Event Model.

Stores AI-discovered, search-grounded public security news, CVE disclosures,
zero-days, active exploit alerts, vendor advisories, and bug bounty developments.

IMPORTANT:
AI-discovered news is INTELLIGENCE/EVIDENCE, not proof of target vulnerability.
All records maintain immutable raw responses and web grounding citations.
"""
from __future__ import annotations

from datetime import datetime
from sqlalchemy import Boolean, DateTime, Float, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, utcnow


class SecurityIntelligenceEvent(Base):
    __tablename__ = "security_intelligence_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(500), index=True)
    summary: Mapped[str] = mapped_column(Text)
    event_type: Mapped[str] = mapped_column(String(64), index=True, default="SECURITY_NEWS")
    # Published timestamp according to external source
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Primary and secondary citations
    source_url: Mapped[str] = mapped_column(Text)
    source_name: Mapped[str] = mapped_column(String(255), default="Web")
    additional_sources: Mapped[list] = mapped_column(JSON, default=list)

    # Entities and vulnerability references
    cve_ids: Mapped[list] = mapped_column(JSON, default=list)
    cwe_ids: Mapped[list] = mapped_column(JSON, default=list)
    affected_products: Mapped[list] = mapped_column(JSON, default=list)
    affected_companies: Mapped[list] = mapped_column(JSON, default=list)

    # Threat and exploitation severity
    severity: Mapped[str] = mapped_column(String(32), default="UNKNOWN", index=True)
    actively_exploited: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    known_exploitation_evidence: Mapped[str | None] = mapped_column(Text, nullable=True)
    security_relevance: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.7)

    # Deduplication and auditability
    fingerprint: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    parser_version: Mapped[str] = mapped_column(String(32), default="1.0.0")

    # Multi-factor priority scoring (0-100)
    severity_score: Mapped[int] = mapped_column(Integer, default=50)
    freshness_score: Mapped[int] = mapped_column(Integer, default=50)
    exploitation_score: Mapped[int] = mapped_column(Integer, default=0)
    relevance_score: Mapped[int] = mapped_column(Integer, default=50)
    priority_score: Mapped[int] = mapped_column(Integer, default=50, index=True)
    priority: Mapped[str] = mapped_column(String(16), default="MEDIUM", index=True)

    # Grounding metadata and raw payload for auditability
    grounding_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=dict)
    raw_model_response: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=dict)

    # Correlation back-references to existing platform entities
    correlated_company_ids: Mapped[list] = mapped_column(JSON, default=list)
    correlated_product_ids: Mapped[list] = mapped_column(JSON, default=list)
    correlated_technology_ids: Mapped[list] = mapped_column(JSON, default=list)
    correlated_advisory_ids: Mapped[list] = mapped_column(JSON, default=list)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
