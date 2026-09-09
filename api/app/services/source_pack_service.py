"""Source pack management and seed synchronizer service.

Parses source_registry.yaml, validates officiality criteria, and idempotently
syncs reference sources for companies registered in the Company table.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import yaml
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models.company import Company
from ..models.source_registry import (
    CompanySource, SourceType, SourceAuthorityLevel, SourceStatus, SourceHealthState
)

logger = logging.getLogger(__name__)

DEFAULT_SEED_FILE = Path(__file__).resolve().parent.parent.parent / "data" / "source_registry.yaml"


class SourcePackService:
    """Manages templates and registration of corporate intelligence sources."""

    def __init__(self, seed_file: Path | str | None = None):
        self.seed_file = Path(seed_file or DEFAULT_SEED_FILE)

    def load_seed_sources(self) -> list[dict[str, Any]]:
        """Load sources from YAML seed file."""
        if not self.seed_file.exists():
            logger.warning("Source seed file not found at: %s", self.seed_file)
            return []
        with open(self.seed_file, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return data.get("sources", []) if isinstance(data, dict) else []

    def sync_reference_sources(self, db: Session) -> dict[str, int]:
        """Syncs reference sources into the database for all matched companies."""
        raw_sources = self.load_seed_sources()
        stats = {"created": 0, "updated": 0, "skipped": 0, "errors": 0}

        # Cache companies by canonical domain
        companies = {c.canonical_domain.lower(): c for c in db.scalars(select(Company)).all()}

        for item in raw_sources:
            domain = str(item.get("company_domain", "")).strip().lower()
            company = companies.get(domain)
            if not company:
                stats["skipped"] += 1
                continue

            source_url = item.get("source_url")
            if not source_url:
                continue

            existing = db.scalar(
                select(CompanySource).where(
                    CompanySource.company_id == company.id,
                    CompanySource.source_url == source_url
                )
            )

            now = datetime.now(timezone.utc)

            if existing:
                # Update attributes
                existing.name = item.get("name", existing.name)
                existing.source_type = item.get("source_type", existing.source_type)
                existing.authority_level = item.get("authority_level", existing.authority_level)
                existing.product_scope = item.get("product_scope", existing.product_scope)
                existing.platform_scope = item.get("platform_scope", existing.platform_scope)
                existing.parser_strategy = item.get("parser_strategy", existing.parser_strategy)
                existing.collection_method = item.get("collection_method", existing.collection_method)
                existing.feed_url = item.get("feed_url", existing.feed_url)
                existing.api_url = item.get("api_url", existing.api_url)
                existing.repository_url = item.get("repository_url", existing.repository_url)
                existing.poll_interval_seconds = item.get("poll_interval_seconds", existing.poll_interval_seconds)
                existing.priority = item.get("priority", existing.priority)
                existing.notes = item.get("notes", existing.notes)
                stats["updated"] += 1
            else:
                new_src = CompanySource(
                    company_id=company.id,
                    name=item.get("name", "Corporate Source"),
                    source_url=source_url,
                    source_type=item.get("source_type", SourceType.OFFICIAL_PRODUCT_CHANGE.value),
                    authority_level=item.get("authority_level", SourceAuthorityLevel.OFFICIAL_RELEASE.value),
                    product_scope=item.get("product_scope"),
                    platform_scope=item.get("platform_scope"),
                    parser_strategy=item.get("parser_strategy", "generic_feed"),
                    collection_method=item.get("collection_method", "POLL"),
                    feed_url=item.get("feed_url"),
                    api_url=item.get("api_url"),
                    repository_url=item.get("repository_url"),
                    requires_auth=bool(item.get("requires_auth", False)),
                    credential_name=item.get("credential_name"),
                    poll_interval_seconds=item.get("poll_interval_seconds", 600),
                    priority=item.get("priority", "P2"),
                    enabled=True,
                    status=SourceStatus.NEVER_CHECKED.value,
                    next_check_at=now,
                    notes=item.get("notes"),
                )
                db.add(new_src)
                stats["created"] += 1

        db.commit()
        return stats


if __name__ == "__main__":
    import sys
    from ..db import SessionLocal
    logging.basicConfig(level=logging.INFO)
    db = SessionLocal()
    try:
        service = SourcePackService()
        result = service.sync_reference_sources(db)
        print(f"Source Pack Sync complete: created={result['created']}, updated={result['updated']}, skipped={result['skipped']}")
    finally:
        db.close()
