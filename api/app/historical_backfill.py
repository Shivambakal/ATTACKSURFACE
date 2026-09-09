"""CLI command for controlled historical backfill."""
from __future__ import annotations

import argparse
import asyncio
import logging
import sys

from app.db import SessionLocal
from app.models.company import Company
from app.services.historical_reconstruction_service import HistoricalReconstructionService

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run controlled historical intelligence backfill.")
    parser.add_argument("--company-id", type=int, help="Specific company ID to backfill")
    parser.add_argument("--limit", type=int, default=10, help="Maximum number of companies to backfill")
    parser.add_argument("--stage", type=int, default=1, choices=[1, 2, 3], help="Reconstruction stage depth (1=Fast, 2=Medium, 3=Deep)")
    parser.add_argument("--dry-run", action="store_true", help="Print targets without performing reconstruction")

    args = parser.parse_args()
    db = SessionLocal()

    try:
        if args.company_id:
            companies = db.query(Company).filter(Company.id == args.company_id).all()
        else:
            companies = db.query(Company).limit(args.limit).all()

        logger.info("Identified %s organization(s) for historical backfill", len(companies))

        for comp in companies:
            logger.info("Target: [%s] %s (%s)", comp.id, comp.name, comp.canonical_domain)
            if args.dry_run:
                continue

            result = asyncio.run(
                HistoricalReconstructionService.reconstruct_company_history(
                    db, comp.id, stage=args.stage
                )
            )
            logger.info("Result for %s: %s", comp.canonical_domain, result)

        logger.info("Historical backfill completed successfully.")
    except Exception as exc:
        logger.error("Backfill failed: %s", exc)
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
