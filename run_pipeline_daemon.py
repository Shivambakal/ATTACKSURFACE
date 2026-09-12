#!/usr/bin/env python3
"""AttackSurface Timeline - 10-Minute Continuous Pipeline Daemon.

Runs every 10 minutes (or on-demand with --once) to ensure the live database
and all main dashboard pages stay continuously populated and updated.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker
# ── Load Environment ─────────────────────────────────────────────────
ROOT_DIR = Path(__file__).resolve().parent
API_DIR = ROOT_DIR / "api"
sys.path.insert(0, str(API_DIR))

load_dotenv(ROOT_DIR / ".env.production.local")
load_dotenv(ROOT_DIR / ".env")
load_dotenv(API_DIR / ".env")

DATABASE_URL = (
    os.getenv("TARGET_DATABASE_URL")
    or os.getenv("DATABASE_URL")
    or "postgresql+psycop://postgres.lejxvdccfyecbtesmuzw:T1jK36MrZ8ofIeML@aws-0-ap-northeast-1.pooler.supabase.com:6543/postgres?sslmode=require"
)

if "postgresql" in DATABASE_URL and "sslmode=" not in DATABASE_URL:
    joiner = "&" if "?" in DATABASE_URL else "?"
    DATABASE_URL = f"{DATABASE_URL}{joiner}sslmode=require"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("PipelineDaemon")

from app.knowledge.taxonomy import (
    OWASP_2021,
    get_cwe_name,
    normalize_cve_id,
    normalize_cwe_id,
    get_owasp_2021_category_for_cwe,
)

CISA_KEV_FEED_URL = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"
LOCAL_CATALOG_FALLBACK = ROOT_DIR / "cisa_kev_catalog.json"


def get_engine():
    return create_engine(
        DATABASE_URL,
        connect_args={"prepare_threshold": None},
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
        pool_recycle=300,
    )


def sync_security_knowledge(engine) -> dict[str, Any]:
    logger.info("─━ Phase 1: Synchronizing Security Knowledge Base ──")
    catalog_data: dict[str, Any] | None = None
    source_origin = "local_cache"

    try:
        logger.info("Fetching latest live CISAKEV feed from %s...", CISA_KEV_FEED_URL)
        resp = requests.get(CISA_KEV_FEED_URL, timeout=15)
        if resp.status_code == 200:
            catalog_data = resp.json()
            source_origin = "cisa_official_api"
            logger.info("Successfully fetched live feed (%d vulnerabilities)", len(catalog_data.get("vulnerabilities", [])))
    except Exception as exc:
        logger.warning("Could not reach live CISAFEED (%s); falling back to local catalog file.", exc)


    if not catalog_data and LOCAL_CATALOG_FALLBACK.exists():
        with open(LOCAL_CATALOG_FALLBACK, "r", encoding="utf-8") as f:
            catalog_data = json.load(f)
        source_origin = "local_catalog_file"
        logger.info("Loaded local CISA catalog (%d vulnerabilities)", len(catalog_data.get("vulnerabilities", []))),


    if not catalog_data:
        raise RuntimeError("No CISA KEV catalog data available to synchronize.")


    vulns = catalog_data.get("vulnerabilities", [])
    version = catalog_data.get("catalogVersion") or "2026.09"
    content_hash = hashlib.sha256(json.dumps(catalog_data, sort_keys=True).encode()).hexdigest()


    with engine.begin() as conn:
        # 1. OWASP 2021
        for cat in OWASP_2021:
            existing = conn.execute(
                text("SELECT id FROM owasp_categories WHERE category_id = :cat_id"),
                {"cat_id": cat["category_id"]}
            ).scalar()
            if not existing:
                conn.execute(
                    text("""
                        INSERT INTO owasp_categories (taxonomy, taxonomy_version, category_id, category_name, description, source_url, created_at)
                        VALUES ('OWASP', '2021', :cat_id, :cat_name, :desc, :url, NOW())
                    """),
                    {
                        "cat_id": cat["category_id"],
                        "cat_name": cat["category_name"],
                        "desc": cat.get("description"),
                        "url": cat.get("source_url"),
                    },
                )

        owasp_rows = conn.execute(text("SELECT id, category_id FROM owasp_categories;")).fetchall()
        owasp_map = {r[1]: r[0] for r in owasp_rows}

        # 2. CWEs
        all_cwes: set[str] = set()
        for v in vulns:
            raw = v.get("cwes") or []
            if isinstance(raw, str):
                raw = [c.strip() for c in raw.split(",") if c.strip()]
            for c in raw:
                norm = normalize_cwe_id(c)
                if norm:
                    all_cwes.add(norm)

        existing_cwes = set(
            r[0] for r in conn.execute(text("SELECT cwe_id FROM cwe_entries;")).fetchall()
        )
        for cwe_id in all_cwes:
            if cwe_id not in existing_cwes:
                cwe_name = get_cwe_name(cwe_id)
                conn.execute(
                    text("""
                        INSERT INTO cwe_entries (cwe_id, name, source, source_version, created_at)
                        VALUES (:cwe_id, :name, 'MITRE', '4.x', NOW())
                        ON CONFLICT (cwe_id) DO NOTHING
                    """),
                    {"cwe_id": cwe_id, "name": cwe_name},
                )


        cwe_rows = conn.execute(text("SELECT id, cwe_id FROM cwe_entries;")).fetchall()
        cwe_map = {r[1]: r[0] for r in cwe_rows}

        # 3. CWE <-> OWASP
        for cwe_id, cwe_db_id in cwe_map.items():
            owasp_cat = get_owasp_2021_category_for_cwe(cwe_id)
            if owasp_cat and owasp_cat in owasp_map:
                conn.execute(
                    text("""
                        INSERT INTO cwe_owasp_association (cwe_id, owasp_category_id, mapping_type, confidence)
                        VALUES (:cwe_id, :owasp_category_id, 'OFFICIAL_OWASP', 1.0)
                        ON CONFLICT DO NOTHING
                    """),
                    {"cwe_id": cwe_db_id, "owasp_category_id": owasp_map[owasp_cat]},
                )

        # 4. Advisories
        adv_rows = conn.execute(text("SELECT id, cve_id FROM security_advisories;")).fetchall()
        adv_map = {r[1].upper(): r[0] for r in adv_rows if r[1]}

        new_advisories = 0
        for v in vulns:
            cve_raw = v.get("cveID") or ""
            norm_cve = normalize_cve_id(cve_raw) or cve_raw.strip().upper()
            if not norm_cve:
                continue

            if norm_cve not in adv_map:
                title = (v.get("vulnerabilityName") or norm_cve).strip()
                summary = (v.get("shortDescription") or "").strip() or None
                vendor = (v.get("vendorProject") or "").strip() or None
                product = (v.get("product") or "").strip() or None
                date_added = v.get("dateAdded")
                due_date = v.get("dueDate")
                ransomware = (v.get("knownRansomwareCampaignUse") or "Unknown").strip()
                triage = (v.get("forensicTriage") or "").strip() or None
                notes = (v.get("notes") or "").strip()
                source_url = notes if notes.startswith("http") else None

                res = conn.execute(
                    text("""
                        INSERT INTO security_advisories (
                            canonical_id, provider, provider_record_id, cve_id, title,
                            summary, vendor, product, date_added, due_date,
                            known_ransomware_use, forensic_triage, source_url, confidence, raw_hash,
                            created_at, updated_at
                        ) VALUES (
                            :canonical_id, 'CISA_KEV', :cve_id, :cve_id, :title,
                            :summary, :vendor, :product, CAST(:date_added AS TIMESTAMP), CAST(:due_date AS TIMESTAMP),
                            :ransomware, :triage, :source_url, 0.98, :raw_hash,
                            NOW(), NOW()
                        ) RETURNING id;
                    """),
                    {
                        "canonical_id": f"CISA_KEV:{norm_cve}",
                        "cve_id": norm_cve,
                        "title": title,
                        "summary": summary,
                        "vendor": vendor,
                        "product": product,
                        "date_added": date_added,
                        "due_date": due_date,
                        "ransomware": ransomware,
                        "triage": triage,
                        "source_url": source_url,
                        "raw_hash": content_hash,
                    },
                ).scalar()
                adv_map[norm_cve] = res
                new_advisories += 1

        # 5. Link Advisories <-> CWE & OWASP (Chunked batch execution for high performance)
        adv_cwe_batch = []
        adv_owasp_batch = []
        for v in vulns:
            cve_raw = v.get("cveID") or ""
            norm_cve = normalize_cve_id(cve_raw) or cve_raw.strip().upper()
            adv_id = adv_map.get(norm_cve)
            if not adv_id:
                continue

            raw_cwes = v.get("cwes") or []
            if isinstance(raw_cwes, str):
                raw_cwes = [c.strip() for c in raw_cwes.split(",") if c.strip()]

            for c in raw_cwes:
                norm_cwe = normalize_cwe_id(c)
                if norm_cwe and norm_cwe in cwe_map:
                    cwe_db_id = cwe_map[norm_cwe]
                    adv_cwe_batch.append({"adv_id": adv_id, "cwe_id": cwe_db_id})
                    owasp_cat = get_owasp_2021_category_for_cwe(norm_cwe)
                    if owasp_cat and owasp_cat in owasp_map:
                        adv_owasp_batch.append({"adv_id": adv_id, "owasp_id": owasp_map[owasp_cat]})

        # Sort and deduplicate to guarantee deadlock-free PostgreSQL execution
        seen_cwe: set[tuple[int, int]] = set()
        dedup_cwe = []
        for x in sorted(adv_cwe_batch, key=lambda i: (i["adv_id"], i["cwe_id"])):
            pair = (x["adv_id"], x["cwe_id"])
            if pair not in seen_cwe:
                seen_cwe.add(pair)
                dedup_cwe.append(x)

        seen_owasp: set[tuple[int, int]] = set()
        dedup_owasp = []
        for x in sorted(adv_owasp_batch, key=lambda i: (i["adv_id"], i["owasp_id"])):
            pair = (x["adv_id"], x["owasp_id"])
            if pair not in seen_owasp:
                seen_owasp.add(pair)
                dedup_owasp.append(x)

        CHUNK_SIZE = 500
        for i in range(0, len(dedup_cwe), CHUNK_SIZE):
            chunk = dedup_cwe[i:i + CHUNK_SIZE]
            conn.execute(
                text("INSERT INTO advisory_cwe_association (advisory_id, cwe_id) VALUES (:adv_id, :cwe_id) ON CONFLICT DO NOTHING"),
                chunk
            )
        for i in range(0, len(dedup_owasp), CHUNK_SIZE):
            chunk = dedup_owasp[i:i + CHUNK_SIZE]
            conn.execute(
                text("INSERT INTO advisory_owasp_association (advisory_id, owasp_category_id) VALUES (:adv_id, :owasp_id) ON CONFLICT DO NOTHING"),
                chunk
            )


        # 6. KnowledgeSource Telemetry
        ks_id = conn.execute(
            text("SELECT id FROM knowledge_sources WHERE source_type = 'CISA_KEV';")
        ).scalar()
        if not ks_id:
            conn.execute(
                text("""
                    INSERT INTO knowledge_sources (
                        source_type, name, version, source_url, record_count, status, content_hash, retrieved_at, created_at, updated_at
                    ) VALUES (
                        'CISA_KEV', 'CISA Known Exploited Vulnerabilities Catalog', :ver, :url, :cnt, 'HEALTHY', :chash, NOW(), NOW(), NOW()
                    )
                """),
                {
                    "ver": version,
                    "url": CISA_KEV_FEED_URL,
                    "cnt": len(vulns),
                    "chash": content_hash,
                },
            )
            ks_id = conn.execute(
                text("SELECT id FROM knowledge_sources WHERE source_type = 'CISA_KEV';")
            ).scalar()
        else:
            conn.execute(
                text("""
                    UPDATE knowledge_sources SET
                        record_count = :cnt,
                        version = :ver,
                        content_hash = :chash,
                        status = 'HEALTHY',
                        retrieved_at = NOW(),
                        updated_at = NOW()
                    WHERE id = :id
                """),
                {
                    "id": ks_id,
                    "ver": version,
                    "cnt": len(vulns),
                    "chash": content_hash,
                },
            )
        source_id = ks_id

        # 7. Record Ingestion Sync Run
        conn.execute(
            text("""
                INSERT INTO knowledge_sync_runs (
                    source_id, started_at, completed_at, status, records_seen,
                    records_created, records_updated, records_skipped, records_failed, error_count, content_hash
                ) VALUES (
                    :sid, NOW() - INTERVAL '5 seconds', NOW(), 'COMPLETED', :seen,
                    :created, :seen, 0, 0, 0, :chash
                )
            """),
            {
                "sid": source_id,
                "seen": len(vulns),
                "created": new_advisories,
                "chash": content_hash,
            },
        )


    result = {
        "status": "COMPLETED",
        "origin": source_origin,
        "total_vulns": len(vulns),
        "new_advisories": new_advisories,
        "distinct_cwes": len(all_cwes),
        "owasp_categories": len(OWASP_2021),
    }
    logger.info(
        "Knowledge base synced: %d advisories ++%d new), %d distinct CWEs, %d OWASP categories",
        len(vulns),
        new_advisories,
        len(all_cwes),
        len(OWASP_2021),
    )
    return result


def collect_threat_intelligence(engine) -> dict[str, Any]:
    logger.info("─━ Phase 2: Collecting Live Threat Intelligence & News ──")
    try:
        from app.services.security_intelligence_collector import SecurityIntelligenceCollector

        SessionLocal = sessionmaker(bind=engine)
        db: Session = SessionLocal()
        try:
            collector = SecurityIntelligenceCollector()
            if not collector.is_configured():
                logger.warning("Gemini API key is not configured; skipping AI search collection phase.")
                return {"status": "skipped", "reason": "No Gemini API key"}

            events = collector.collect_sync(db, max_items=15)
            logger.info("Collected and persisted %d security intelligence events", len(events))
            return {
                "status": "COMPLETED",
                "events_collected": len(events),
            }
        finally:
            db.close()
    except Exception as exc:
        return {"status": "failed", "error": str(exc)}


async def poll_corporate_sources(engine) -> dict[str, Any]:
    logger.info("─━ Phase 3: Polling Corporate Sources ──")
    try:
        from app.services.corporate_scheduler import CorporateScheduler

        SessionLocal = sessionmaker(bind=engine)
        db: Session = SessionLocal()
        try:
            scheduler = CorporateScheduler()
            stats = await scheduler.run_due_sources(db, max_sources=10, force=False)
            logger.info("Corporate sources poll: %d due, %d dispatched, %d items changed", stats["due_count"], stats["dispatched"], stats["items_changed"])
            return stats
        finally:
            db.close()
    except Exception as exc:
        logger.exception("Corporate sources poll encountered an error (isolated): %s", exc)
        return {"status": "failed", "error": str(exc)}


def verify_system_health(engine) -> dict[str, int]:
    logger.info("─━ Phase 4: Health & Freshness Verification ──")
    tables = [
        "companies",
        "targets",
        "products",
        "timeline_events",
        "security_programs",
        "security_advisories",
        "cwe_entries",
        "owasp_categories",
        "knowledge_sources",
        "knowledge_sync_runs",
        "security_intelligence_events",
        "change_clusters",
        "research_signals",
    ]
    counts = {}
    with engine.connect() as conn:
        for t in tables:
            try:
                cnt = conn.execute(text(f'SELECT count(*) FROM "{t}";')).scalar()
                counts[t] = cnt or 0
            except Exception:
                counts[t] = -1


    logger.info("Live Database Record Snapshot:")
    logger.info("  K Organizations (companies):           %d", counts.get("companies", 0))
    logger.info("  K Monitored Targets:                   %d", counts.get("targets", 0))
    logger.info("  K Products & Subsystems:              %d", counts.get("products", 0))
    logger.info("  K Attack Surface Timeline Events:      %d", counts.get("timeline_events", 0))
    logger.info("  K Bug Bounty Security Programs:        %d", counts.get("security_programs", 0))
    logger.info("  K Security Advisories (CISA KEV):      %d", counts.get("security_advisories", 0))
    logger.info("  K MITRE CWE Weaknesses:                %d", counts.get("cwe_entries", 0))
    logger.info("  K OWASO Top 10 Categories:            %d", counts.get("owasp_categories", 0))
    logger.info("  K Knowledge Sources:                   %d", counts.get("knowledge_sources", 0))
    logger.info("  K Sync Run Telemetry:                  %d", counts.get("knowledge_sync_runs", 0))
    logger.info("  K Security Intelligence Events:       %d", counts.get("security_intelligence_events", 0))
    logger.info("  K Change Clusters:                    %d", counts.get("change_clusters", 0))
    logger.info("  K Research Signals:                   %d", counts.get("research_signals", 0))
    return counts


def run_singlecycle(engine):
    start_time = time.time()
    logger.info("================================================================================")
    logger.info("STARTING LIVE INTELLIGENCE PIPELINE CUCLE at %s UTC", datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S'))
    logger.info("===============================================================================")

    try:
        sync_security_knowledge(engine)
    except Exception as exc:
        logger.exception("Knowledge Base sync error: %s", exc)


    try:
        collect_threat_intelligence(engine)
    except Exception as exc:
        logger.exception("Threat Intelligence error: %s", exc)


    try:
        asyncio.run(poll_corporate_sources(engine))
    except Exception as exc:
        logger.exception("Corporate sources error: %s", exc)


    try:
        verify_system_health(engine)
    except Exception as exc:
        logger.exception("Health verification error: %s", exc)

    duration = time.time() - start_time
    logger.info("================================================================================")
    logger.info("PIPELINE CUCLE COMPLETED in %.2f seconds", duration)
    logger.info("=================================================================================")


def main():
    parser = argparse.ArgumentParser(description="AttackSurface Timeline - 10-Minute Pipeline Daemon")
    parser.add_argument("--once", action="store_true", help="Run a single update cycle and exit immediately")
    parser.add_argument("--interval", type=int, default=10, help="Loop interval in minutes (default: 10)")
    args = parser.parse_args()

    engine = get_engine()

    if args.once:
        logger.info("Executing one-time update cycle...")
        run_singlecycle(engine)
        sys.exit(0)

    interval_seconds = args.interval * 60
    logger.info("Starting AttackSurface 10-Minute Continuous Pipeline Daemon (Interval: %d minutes)", args.interval)
    logger.info("Press Ctrl+C to stop the daemon gracefully.")

    while True:
        try:
            run_singlecycle(engine)
        except Exception as exc:
            logger.exception("Unhandled error in pipeline cycle: %s", exc)

        logger.info("Next cycle scheduled in %d minutes (%d seconds). Waiting...", args.interval, interval_seconds)
        try:
            time.sleep(interval_seconds)
        except KeyboardInterrupt:
            logger.info("Received shutdown signal. Exiting daemon safely.")
            break

if __name__ == '__main__':
    main()
