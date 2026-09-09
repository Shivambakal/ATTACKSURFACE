"""Shared pytest fixtures."""
from __future__ import annotations

import pytest
from app.db import SessionLocal


@pytest.fixture
def db_session():
    """Provides a transactional database session for tests."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()
