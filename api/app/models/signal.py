"""ResearchSignal and ResearchSignalFeedback models.

Represents prioritized, actionable attack-surface intelligence
synthesized from normalized observations, diff clusters, and
historical security context.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, utcnow


class SignalType(str, Enum):
    NEW_AUTH_SURFACE = "NEW_AUTH_SURFACE"
    NEW_AUTHZ_SURFACE = "NEW_AUTHZ_SURFACE"
    NEW_API_SURFACE = "NEW_API_SURFACE"
    NEW_FEATURE = "NEW_FEATURE"
    NEW_ASSET = "NEW_ASSET"
    NEW_INTEGRATION = "NEW_INTEGRATION"
    TECHNOLOGY_CHANGE = "TECHNOLOGY_CHANGE"
    SECURITY_CHANGE = "SECURITY_CHANGE"
    POTENTIAL_ATTACK_SURFACE_EXPANSION = "POTENTIAL_ATTACK_SURFACE_EXPANSION"
    OTHER = "OTHER"


class SignalStatus(str, Enum):
    NEW = "new"
    INTERESTING = "interesting"
    INVESTIGATING = "investigating"
    SAVED = "saved"
    IGNORED = "ignored"
    RESOLVED = "resolved"


class FeedbackType(str, Enum):
    USEFUL = "USEFUL"
    INTERESTING = "INTERESTING"  # Alias of USEFUL
    NOT_USEFUL = "NOT_USEFUL"
    NOT_RELEVANT = "NOT_RELEVANT"  # Alias of NOT_USEFUL
    DUPLICATE = "DUPLICATE"
    FALSE_POSITIVE = "FALSE_POSITIVE"
    ALREADY_KNOWN = "ALREADY_KNOWN"
    NOT_IN_SCOPE = "NOT_IN_SCOPE"


class ResearchSignal(Base):
    __tablename__ = "research_signals"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id"), nullable=True, index=True)
    target_id: Mapped[int | None] = mapped_column(ForeignKey("targets.id"), nullable=True, index=True)
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id"), nullable=True, index=True)
    asset_id: Mapped[int | None] = mapped_column(ForeignKey("assets.id"), nullable=True, index=True)
    change_id: Mapped[int | None] = mapped_column(ForeignKey("changes.id"), nullable=True, index=True)
    cluster_id: Mapped[int | None] = mapped_column(ForeignKey("change_clusters.id"), nullable=True, index=True)

    title: Mapped[str] = mapped_column(String(255))
    signal_type: Mapped[str] = mapped_column(String(64), default=SignalType.OTHER.value, index=True)
    summary: Mapped[str] = mapped_column(Text)
    why_it_matters: Mapped[str] = mapped_column(Text)
    recommended_research_area: Mapped[str | None] = mapped_column(Text, nullable=True)

    relevance_score: Mapped[int] = mapped_column(Integer, default=50, index=True)
    confidence_score: Mapped[int] = mapped_column(Integer, default=70)
    security_context_score: Mapped[int] = mapped_column(Integer, default=50)
    priority: Mapped[str] = mapped_column(String(16), default="MEDIUM", index=True)
    status: Mapped[str] = mapped_column(String(32), default=SignalStatus.NEW.value, index=True)

    security_context: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=dict)
    historical_context: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=dict)
    affected_assets: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)
    affected_features: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)
    related_findings: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)
    evidence_ids: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)
    score_factors: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=dict)
    source_count: Mapped[int] = mapped_column(Integer, default=1)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    company: Mapped["Company | None"] = relationship(back_populates="research_signals")
    feedback: Mapped[list["ResearchSignalFeedback"]] = relationship(
        back_populates="signal", cascade="all, delete-orphan"
    )


class ResearchSignalFeedback(Base):
    __tablename__ = "research_signal_feedback"

    id: Mapped[int] = mapped_column(primary_key=True)
    signal_id: Mapped[int] = mapped_column(ForeignKey("research_signals.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    feedback: Mapped[str] = mapped_column(String(32), index=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    signal: Mapped["ResearchSignal"] = relationship(back_populates="feedback")
