"""Command-line and module interface for syncing public bug bounty & security program intelligence.

Loads real public programs from HackerOne, Bugcrowd, Intigriti, YesWeHack,
Federacy, and ProjectDiscovery into canonical companies and security programs.
"""
from __future__ import annotations

import logging
import sys
import time

from app.db import SessionLocal
from app.models.company import Company
from app.models.security_program import SecurityProgram, ProgramScopeRule, ProgramSnapshot, ProgramChangeEvent
from app.models.target import Target
from app.services.program_entity_resolution import ProgramEntityResolutionService
from app.services.program_ingestion import fetch_all_public_programs

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("sync_programs")


def run_sync(batch_size: int = 50) -> dict:
    """Executes the public program sync pipeline."""
    start_time = time.time()
    db = SessionLocal()
    try:
        initial_companies = db.query(Company).count()
        initial_programs = db.query(SecurityProgram).count()
        initial_targets = db.query(Target).count()

        logger.info(
            "Starting Public Program Sync. Initial DB state: %d companies, %d security programs, %d authorized targets",
            initial_companies, initial_programs, initial_targets
        )

        all_programs = fetch_all_public_programs()
        logger.info("Fetched %d raw program records from all public ecosystems.", len(all_programs))

        resolver = ProgramEntityResolutionService(db)

        companies_created = 0
        programs_created = 0
        programs_updated = 0
        processed = 0

        for i, prog in enumerate(all_programs, 1):
            try:
                sp, comp_created, p_created = resolver.ingest_program_record(prog)
                if comp_created:
                    companies_created += 1
                if p_created:
                    programs_created += 1
                elif sp:
                    programs_updated += 1
                processed += 1

                if i % batch_size == 0:
                    db.commit()
                    logger.info(
                        "Progress: %d/%d processed (+%d companies, +%d programs)",
                        i, len(all_programs), companies_created, programs_created
                    )
            except Exception as e:
                db.rollback()
                logger.error("Error ingesting program %s: %s", prog.get("program_name"), e)

        db.commit()

        final_companies = db.query(Company).count()
        final_programs = db.query(SecurityProgram).count()
        final_targets = db.query(Target).count()
        total_scope_rules = db.query(ProgramScopeRule).count()
        total_snapshots = db.query(ProgramSnapshot).count()
        total_change_events = db.query(ProgramChangeEvent).count()

        duration = time.time() - start_time
        summary = {
            "duration_seconds": round(duration, 2),
            "programs_processed": processed,
            "companies_created": companies_created,
            "programs_created": programs_created,
            "programs_updated": programs_updated,
            "initial_companies": initial_companies,
            "final_companies": final_companies,
            "initial_programs": initial_programs,
            "final_programs": final_programs,
            "authorized_targets": final_targets,
            "total_scope_rules": total_scope_rules,
            "total_snapshots": total_snapshots,
            "total_change_events": total_change_events,
        }

        logger.info("Sync finished successfully in %.2fs. Summary: %s", duration, summary)
        return summary
    finally:
        db.close()


if __name__ == "__main__":
    result = run_sync()
    print("\n--- SYNC RESULT SUMMARY ---")
    for k, v in result.items():
        print(f"  {k}: {v}")
