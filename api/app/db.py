"""Database engine and session factory."""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .config import settings
from .models.base import Base

connect_args = {}
if "psycopg" in settings.database_url or "postgresql" in settings.database_url:
    connect_args["prepare_threshold"] = None

engine = create_engine(settings.database_url, pool_pre_ping=True, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
