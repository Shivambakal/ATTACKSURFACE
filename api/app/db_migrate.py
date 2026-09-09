"""Alembic migration orchestrator & database readiness manager.

Guarantees that:
1. `alembic_version` always exists on the database.
2. Migrations are executed up to `head` safely.
3. If legacy tables were created via create_all, the database is safely stamped with head.
"""
from __future__ import annotations

import logging
import os
import sys
from sqlalchemy import inspect, text
from alembic.config import Config
from alembic import command

from .config import settings
from .db import engine

logger = logging.getLogger("app.db_migrate")
logging.basicConfig(level=logging.INFO)


def get_alembic_config() -> Config:
    """Constructs Alembic config pointing to api/alembic.ini."""
    # Locate alembic.ini relative to this file
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    ini_path = os.path.join(base_dir, "alembic.ini")
    cfg = Config(ini_path)
    cfg.set_main_option("sqlalchemy.url", settings.database_url)
    cfg.set_main_option("script_location", os.path.join(base_dir, "alembic"))
    return cfg


def run_database_migrations() -> str:
    """Ensures database schema and alembic_version are fully up to date."""
    cfg = get_alembic_config()

    try:
        with engine.connect() as conn:
            inspector = inspect(conn)
            table_names = inspector.get_table_names()

            has_alembic_version = "alembic_version" in table_names
            has_app_tables = "companies" in table_names or "users" in table_names

            if not has_alembic_version:
                if has_app_tables:
                    logger.info("Existing application tables detected without alembic_version. Stamping 'head'...")
                    command.stamp(cfg, "head")
                else:
                    logger.info("Fresh database detected. Running full migration to 'head'...")
                    command.upgrade(cfg, "head")
            else:
                logger.info("alembic_version present. Upgrading to 'head'...")
                command.upgrade(cfg, "head")

            # Verify active version
            res = conn.execute(text("SELECT version_num FROM alembic_version")).scalar()
            logger.info("Active database migration version: %s", res)
            return str(res or "unknown")

    except Exception as exc:
        logger.error("Database migration check encountered an error: %s", exc)
        raise


if __name__ == "__main__":
    current = run_database_migrations()
    print(f"Migration completed successfully. Active version: {current}")
