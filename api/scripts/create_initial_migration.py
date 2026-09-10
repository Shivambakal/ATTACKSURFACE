"""
Script to directly create all tables on the Supabase DB using SQLAlchemy metadata,
then stamp Alembic at head so future migrations run correctly.
Run from api/ directory: python scripts/create_initial_migration.py
"""
import os
import sys

# Make sure we load the right DATABASE_URL
db_url = os.environ.get("DATABASE_URL")
if not db_url:
    print("ERROR: DATABASE_URL not set")
    sys.exit(1)

# Convert postgresql:// to postgresql+psycopg2:// if needed
if db_url.startswith("postgresql://"):
    db_url = db_url.replace("postgresql://", "postgresql+psycopg2://", 1)

print(f"Connecting to: {db_url[:50]}...")

from sqlalchemy import create_engine, text, inspect

# Import all models to register them with Base.metadata
import app.models  # noqa: F401 - registers all models
from app.models.base import Base

engine = create_engine(db_url, echo=False)

with engine.connect() as conn:
    # Check if alembic_version table exists
    result = conn.execute(text("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = 'alembic_version'
        )
    """))
    has_alembic = result.scalar()
    print(f"alembic_version table exists: {has_alembic}")

    # Check what tables already exist
    inspector = inspect(engine)
    existing = set(inspector.get_table_names())
    print(f"Existing tables ({len(existing)}): {sorted(existing)}")

# Create all tables that don't exist yet
print("Creating all tables from SQLAlchemy metadata...")
Base.metadata.create_all(engine, checkfirst=True)
print("Tables created.")

# Now stamp with the final head revision
from alembic.config import Config
from alembic import command

cfg = Config("alembic.ini")
# Override sqlalchemy.url
cfg.set_main_option("sqlalchemy.url", db_url)

# Stamp at head (b2f8a1c9e3d4 = our latest migration)
print("Stamping Alembic at head...")
command.stamp(cfg, "head")
print("Done! Database is fully initialized and stamped at head.")

# Verify
with engine.connect() as conn:
    result = conn.execute(text("SELECT version_num FROM alembic_version"))
    rows = result.fetchall()
    print(f"Alembic version: {rows}")
    inspector2 = inspect(engine)
    tables = sorted(inspector2.get_table_names())
    print(f"Total tables: {len(tables)}")
    for t in tables:
        print(f"  - {t}")
