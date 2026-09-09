"""Monetization and subscription billing models."""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from enum import Enum
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, utcnow


class SubscriptionTier(str, Enum):
    FREE = "FREE"
    RESEARCHER = "RESEARCHER"
    PRO = "PRO"
    ADVANCED = "ADVANCED"
    TEAM = "ADVANCED"


class SubscriptionStatus(str, Enum):
    ACTIVE = "ACTIVE"
    PAST_DUE = "PAST_DUE"
    CANCELED = "CANCELED"
    TRIALING = "TRIALING"


class PaymentStatus(str, Enum):
    CREATED = "CREATED"
    AUTHORIZED = "AUTHORIZED"
    CAPTURED = "CAPTURED"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"
    CANCELED = "CANCELED"
    TEST_SIMULATED = "TEST_SIMULATED"


class Subscription(Base):
    """Tracks researcher and organization subscription tier and entitlement."""
    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True)
    tier: Mapped[str] = mapped_column(String(32), default=SubscriptionTier.FREE.value, index=True)
    status: Mapped[str] = mapped_column(String(32), default=SubscriptionStatus.ACTIVE.value, index=True)
    provider: Mapped[str] = mapped_column(String(32), default="INTERNAL")
    provider_subscription_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    provider_customer_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    is_verified_payment: Mapped[bool] = mapped_column(Boolean, default=False)
    current_period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    current_period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancel_at_period_end: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    # Relationships
    user: Mapped["User"] = relationship()


class PaymentTransaction(Base):
    """Audit log of order attempts, payments, and gateway verification."""
    __tablename__ = "payment_transactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    order_id: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    payment_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    plan_tier: Mapped[str] = mapped_column(String(32), default=SubscriptionTier.RESEARCHER.value, index=True)
    billing_interval: Mapped[str] = mapped_column(String(16), default="monthly", index=True)
    amount_inr: Mapped[int] = mapped_column(Integer, default=0)
    expected_amount_paisa: Mapped[int] = mapped_column(Integer, default=0)
    currency: Mapped[str] = mapped_column(String(10), default="INR")
    status: Mapped[str] = mapped_column(String(32), default=PaymentStatus.CREATED.value, index=True)
    payment_state: Mapped[str] = mapped_column(String(32), default=PaymentStatus.CREATED.value, index=True)
    gateway_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    environment: Mapped[str] = mapped_column(String(32), default="TEST MODE")
    gateway_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    signature: Mapped[str | None] = mapped_column(String(255), nullable=True)
    receipt: Mapped[str | None] = mapped_column(String(128), nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    user: Mapped["User"] = relationship()
