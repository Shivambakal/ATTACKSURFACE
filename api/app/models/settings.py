"""User settings model — appearance, notifications, research, privacy, developer."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, utcnow


class UserSettings(Base):
    __tablename__ = "user_settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, index=True)

    appearance: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=lambda: {
        "theme": "dark", "density": "comfortable", "reduced_motion": False,
        "timeline_preference": "chronological",
    })
    notifications: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=lambda: {
        "critical_alerts": "instant", "high_alerts": "instant",
        "feature_changes": "daily", "api_changes": "daily",
        "security_events": "instant", "daily_digest": True, "weekly_digest": True,
        "email_notifications": True, "in_app_notifications": True,
    })
    research: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=lambda: {
        "default_priority_threshold": "MEDIUM",
        "preferred_technologies": [], "preferred_vuln_classes": [],
        "default_monitoring_frequency": "daily",
    })
    privacy: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=lambda: {
        "public_profile": False, "telemetry": False,
        "analytics": False, "data_sharing": False,
    })
    developer: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=lambda: {
        "api_keys": [], "webhooks": [],
    })

    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    user = relationship("User", back_populates="settings")
