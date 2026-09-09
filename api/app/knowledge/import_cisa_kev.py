"""CLI module for importing the CISA KEV catalog into the Security Knowledge Base.

Usage::

    python -m app.knowledge.import_cisa_kev <catalog_path> [--dry-run] [--limit N]

Examples::

    # Full import
    python -m app.knowledge.import_cisa_kev ../cisa_kev_catalog.json

    # Dry run (validate only, no DB writes)
    python -m app.knowledge.import_cisa_kev ../cisa_kev_catalog.json --dry-run

    # Import first 100 entries only
    python -m app.knowledge.import_cisa_kev ../cisa_kev_catalog.json --limit 100
"""
from __future__ import annotations

import argparse
import logging
import sys
import time

from app.db import SessionLocal
from app.knowledge.cisa_kev_ingestor import CISAKEVIngestor

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


def get_sync_db():
    """Yield a synchronous SQLAlchemy session (mirrors app.database.get_sync_db)."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def main(argv: list[str] | None = None) -> int:
    """Entry point for the CLI importer.

    Args:
        argv: Optional argument list (defaults to sys.argv[1:]).

    Returns:
        Exit code (0 = success, 1 = failure).
    """
    parser = argparse.ArgumentParser(
        prog="python -m app.knowledge.import_cisa_kev",
        description="Import CISA KEV catalog into the Security Knowledge Base.",
    )
    parser.add_argument("catalog_path", help="Path to the CISA KEV JSON catalog file.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Validate and normalize without writing to the database.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        metavar="N",
        help="Process only the first N entries (useful for testing).",
    )
    parser.add_argument(
        "--source-version",
        type=str,
        default=None,
        metavar="VERSION",
        help="Override the source version string stored in KnowledgeSource.",
    )

    args = parser.parse_args(argv)

    ingestor = CISAKEVIngestor()

    # ── Load & validate before touching the DB ────────────────────────
    print(f"[import_cisa_kev] Loading catalog from: {args.catalog_path}")
    try:
        catalog = ingestor.load_catalog(args.catalog_path)
    except FileNotFoundError:
        print(f"ERROR: File not found: {args.catalog_path}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"ERROR: Failed to load catalog: {exc}", file=sys.stderr)
        return 1

    is_valid, reason = ingestor.validate_catalog(catalog)
    if not is_valid:
        print(f"ERROR: Catalog validation failed: {reason}", file=sys.stderr)
        return 1

    total_entries = len(catalog.get("vulnerabilities", []))
    process_count = min(args.limit, total_entries) if args.limit else total_entries
    content_hash = ingestor.compute_content_hash(catalog)

    print(f"[import_cisa_kev] Catalog version : {catalog.get('catalogVersion', 'unknown')}")
    print(f"[import_cisa_kev] Total entries    : {total_entries}")
    print(f"[import_cisa_kev] Processing       : {process_count}")
    print(f"[import_cisa_kev] Content hash     : {content_hash[:16]}...")
    print(f"[import_cisa_kev] Dry run          : {args.dry_run}")

    if args.dry_run:
        print("[import_cisa_kev] DRY RUN - validating and normalizing catalog entries in memory...")
        t0 = time.perf_counter()
        valid_count = 0
        err_count = 0
        entries_to_check = catalog.get("vulnerabilities", [])
        if args.limit:
            entries_to_check = entries_to_check[:args.limit]
        for entry in entries_to_check:
            try:
                ingestor._normalize_record(entry)
                valid_count += 1
            except Exception as exc:
                err_count += 1
                logger.warning("Validation failed for entry %s: %s", entry.get("cveID"), exc)
        elapsed = time.perf_counter() - t0
        print("\n[import_cisa_kev] -- Dry Run Summary -------------------------------")
        print(f"  Catalog version : {catalog.get('catalogVersion', 'unknown')}")
        print(f"  Date released   : {catalog.get('dateReleased', 'unknown')}")
        print(f"  Content hash    : {content_hash[:32]}...")
        print(f"  Total verified  : {valid_count}")
        print(f"  Validation errors: {err_count}")
        print(f"  Duration        : {elapsed:.2f}s")
        print(f"  Status          : {'VALID' if err_count == 0 else 'INVALID'}")
        print("[import_cisa_kev] -------------------------------------------------\n")
        return 0 if err_count == 0 else 1

    # -- Run live ingestion --------------------------------------------
    db_gen = get_sync_db()
    db = next(db_gen)
    try:
        t0 = time.perf_counter()
        sync_run = ingestor.ingest(
            db=db,
            catalog_data=catalog,
            limit=args.limit,
            dry_run=False,
            source_version=args.source_version,
        )
        elapsed = time.perf_counter() - t0

        print("\n[import_cisa_kev] -- Ingestion Summary --------------------------")
        print(f"  Status          : {sync_run.status}")
        print(f"  Records seen    : {sync_run.records_seen}")
        print(f"  Records created : {sync_run.records_created}")
        print(f"  Records updated : {sync_run.records_updated}")
        print(f"  Records failed  : {sync_run.records_failed}")
        print(f"  Duration        : {elapsed:.2f}s")
        print("[import_cisa_kev] -------------------------------------------------\n")

    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        logger.exception("Unexpected error during ingestion")
        print(f"ERROR: Unexpected error: {exc}", file=sys.stderr)
        return 1
    finally:
        try:
            db_gen.close()
        except StopIteration:
            pass

    return 0


if __name__ == "__main__":
    sys.exit(main())
