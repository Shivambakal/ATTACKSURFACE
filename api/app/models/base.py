"""Shared base and utilities for all models."""
from datetime import datetime, timezone

from sqlalchemy.orm import DeclarativeBase


def utcnow() -> datetime:
    """Return the current UTC time with timezone info."""
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass
