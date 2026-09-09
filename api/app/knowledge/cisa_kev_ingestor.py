"""CISA Known Exploited Vulnerabilities (KEV) catalog ingestor.

Downloads, validates, normalizes, and upserts CISA KEV entries into the
Security Knowledge Base.  Designed to be idempotent: re-running with the
same catalog produces no net change (except updating the ``updated_at``
timestamp).
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import text, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import (
    SecurityAdvisory,
    CWEEntry,
    OWASPCategory,
    KnowledgeSource,
    KnowledgeSyncRun,
    VulnerabilityReference,
    advisory_cwe_association,
    advisory_owasp_association,
    cwe_owasp_association,
)
from app.knowledge.taxonomy import (
    OWASP_2021,
    CWE_NAMES,
    get_cwe_name,
    normalize_cwe_id,
    normalize_cve_id,
    get_owasp_2021_category_for_cwe,
    get_vuln_class_for_cwe,
)

logger = logging.getLogger(__name__)

PROVIDER = "CISA_KEV"
BATCH_SIZE = 100


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class CISAKEVIngestor:
    """Ingestor for the CISA Known Exploited Vulnerabilities catalog."""

    # ------------------------------------------------------------------
    # Public static helpers
    # ------------------------------------------------------------------

    @staticmethod
    def load_catalog(path: str) -> dict:
        """Read and parse a CISA KEV JSON catalog file.

        Handles files that begin with markdown code-fence markers
        (e.g., ````` ```json `````) by stripping them before parsing.

        Args:
            path: Absolute or relative path to the JSON catalog file.

        Returns:
            Parsed catalog as a dict.

        Raises:
            FileNotFoundError: If the file does not exist.
            json.JSONDecodeError: If the content is not valid JSON after
                stripping code fences.
        """
        with open(path, "r", encoding="utf-8") as fh:
            raw = fh.read()

        # Strip optional markdown code fences (``` or ```json at start/end)
        raw = raw.strip()
        if raw.startswith("```"):
            # Remove opening fence line (e.g. ```json\n or ```\n)
            raw = re.sub(r"^```[a-z]*\n?", "", raw, count=1)
            # Remove closing fence
            raw = re.sub(r"\n?```\s*$", "", raw)
            raw = raw.strip()

        return json.loads(raw)

    @staticmethod
    def validate_catalog(data: Any) -> tuple[bool, str]:
        """Validate that *data* has the expected CISA KEV catalog structure.

        Returns:
            (True, "") on success, or (False, reason) on failure.
        """
        if not isinstance(data, dict):
            return False, f"Expected dict, got {type(data).__name__}"

        required_keys = {"title", "catalogVersion", "dateReleased", "vulnerabilities"}
        missing = required_keys - set(data.keys())
        if missing:
            return False, f"Missing required catalog keys: {missing}"

        if not isinstance(data.get("vulnerabilities"), list):
            return False, "'vulnerabilities' must be a list"

        if len(data["vulnerabilities"]) == 0:
            return False, "Catalog contains zero vulnerability entries"

        # Spot-check first entry
        first = data["vulnerabilities"][0]
        entry_required = {"cveID", "vendorProject", "product", "vulnerabilityName"}
        entry_missing = entry_required - set(first.keys())
        if entry_missing:
            return False, f"First entry missing keys: {entry_missing}"

        return True, ""

    @staticmethod
    def compute_content_hash(data: dict) -> str:
        """Compute a stable SHA-256 content hash of the catalog.

        Uses sorted-key JSON serialization to ensure determinism regardless
        of insertion order.
        """
        canonical = json.dumps(data, sort_keys=True, ensure_ascii=True)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    # ------------------------------------------------------------------
    # Internal normalization
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_date(value: Optional[str]) -> Optional[datetime]:
        """Parse a date string 'YYYY-MM-DD' or ISO-8601 to a UTC datetime."""
        if not value:
            return None
        # Try ISO-8601 with timezone
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            pass
        # Try plain date YYYY-MM-DD
        try:
            return datetime.strptime(value[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _normalize_record(entry: dict) -> dict:
        """Transform a raw CISA KEV entry into a canonical advisory dict.

        Args:
            entry: Raw dict from the CISA KEV ``vulnerabilities`` list.

        Returns:
            Normalized dict with canonical field names and typed values.
        """
        cve_raw = entry.get("cveID") or ""
        cve_id = normalize_cve_id(cve_raw) or cve_raw.strip().upper()

        # CWE normalization
        raw_cwes = entry.get("cwes") or []
        if isinstance(raw_cwes, str):
            raw_cwes = [c.strip() for c in raw_cwes.split(",") if c.strip()]
        normalized_cwes = [normalize_cwe_id(c) for c in raw_cwes if c]

        vendor = (entry.get("vendorProject") or "").strip() or None
        product = (entry.get("product") or "").strip() or None

        notes_raw = entry.get("notes") or ""
        source_url: Optional[str] = None
        if notes_raw.startswith("http"):
            source_url = notes_raw.strip()

        return {
            "canonical_id": f"{PROVIDER}:{cve_id}",
            "provider": PROVIDER,
            "provider_record_id": cve_id,
            "cve_id": cve_id,
            "title": (entry.get("vulnerabilityName") or cve_id).strip(),
            "summary": (entry.get("shortDescription") or "").strip() or None,
            "vendor": vendor,
            "product": product,
            "date_added": CISAKEVIngestor._parse_date(entry.get("dateAdded")),
            "due_date": CISAKEVIngestor._parse_date(entry.get("dueDate")),
            "known_ransomware_use": (entry.get("knownRansomwareCampaignUse") or "Unknown").strip(),
            "forensic_triage": (entry.get("forensicTriage") or "").strip() or None,
            "source_url": source_url,
            "confidence": 0.98,
            "cwes": normalized_cwes,
            "required_action": (entry.get("requiredAction") or "").strip() or None,
        }

    # ------------------------------------------------------------------
    # OWASP seeding helper
    # ------------------------------------------------------------------

    @staticmethod
    def _seed_owasp_categories(db: Session, source_version: Optional[str] = None) -> dict[str, OWASPCategory]:
        """Ensure all OWASP 2021 categories exist in DB.

        Returns:
            Mapping of category_id -> OWASPCategory ORM object.
        """
        mapping: dict[str, OWASPCategory] = {}
        for cat in OWASP_2021:
            existing = (
                db.query(OWASPCategory)
                .filter_by(taxonomy_version="2021", category_id=cat["category_id"])
                .first()
            )
            if not existing:
                existing = OWASPCategory(
                    taxonomy="OWASP",
                    taxonomy_version="2021",
                    category_id=cat["category_id"],
                    category_name=cat["category_name"],
                    description=cat.get("description"),
                    source_url=cat.get("source_url"),
                )
                db.add(existing)
                db.flush()
            mapping[cat["category_id"]] = existing
        return mapping

    # ------------------------------------------------------------------
    # Association helpers (robust for both PostgreSQL and SQLite)
    # ------------------------------------------------------------------

    @staticmethod
    def _insert_advisory_cwe(db: Session, advisory_id: int, cwe_db_id: int) -> None:
        """Insert advisory-CWE association, ignoring duplicate key errors."""
        exists = db.execute(
            select(advisory_cwe_association.c.advisory_id).where(
                advisory_cwe_association.c.advisory_id == advisory_id,
                advisory_cwe_association.c.cwe_id == cwe_db_id,
            )
        ).first()
        if not exists:
            db.execute(
                advisory_cwe_association.insert().values(
                    advisory_id=advisory_id, cwe_id=cwe_db_id
                )
            )

    @staticmethod
    def _insert_advisory_owasp(db: Session, advisory_id: int, owasp_id: int) -> None:
        """Insert advisory-OWASP association, ignoring duplicate key errors."""
        exists = db.execute(
            select(advisory_owasp_association.c.advisory_id).where(
                advisory_owasp_association.c.advisory_id == advisory_id,
                advisory_owasp_association.c.owasp_category_id == owasp_id,
            )
        ).first()
        if not exists:
            db.execute(
                advisory_owasp_association.insert().values(
                    advisory_id=advisory_id, owasp_category_id=owasp_id
                )
            )

    @staticmethod
    def _insert_cwe_owasp(db: Session, cwe_db_id: int, owasp_id: int) -> None:
        """Insert CWE-OWASP association, ignoring duplicate key errors."""
        exists = db.execute(
            select(cwe_owasp_association.c.cwe_id).where(
                cwe_owasp_association.c.cwe_id == cwe_db_id,
                cwe_owasp_association.c.owasp_category_id == owasp_id,
            )
        ).first()
        if not exists:
            db.execute(
                cwe_owasp_association.insert().values(
                    cwe_id=cwe_db_id,
                    owasp_category_id=owasp_id,
                    mapping_type="OFFICIAL_OWASP",
                    confidence=1.0,
                )
            )


    # ------------------------------------------------------------------
    # Main ingestion method
    # ------------------------------------------------------------------

    def ingest(
        self,
        db: Session,
        catalog_path: Optional[str] = None,
        catalog_data: Optional[dict] = None,
        limit: Optional[int] = None,
        dry_run: bool = False,
        source_version: Optional[str] = None,
    ) -> KnowledgeSyncRun:
        """Ingest the CISA KEV catalog into the security knowledge base.

        Args:
            db: SQLAlchemy session.
            catalog_path: Path to the JSON catalog file (mutually exclusive
                with *catalog_data*).
            catalog_data: Pre-loaded catalog dict (for testing without file I/O).
            limit: Optional cap on the number of entries to process.
            dry_run: If True, validate and normalize but do not commit.
            source_version: Override the catalog version string.

        Returns:
            A :class:`KnowledgeSyncRun` ORM object with ingestion telemetry.

        Raises:
            ValueError: If neither *catalog_path* nor *catalog_data* is provided,
                or if validation fails.
        """
        if catalog_data is None and catalog_path is None:
            raise ValueError("Either catalog_path or catalog_data must be provided.")

        # ── Load ──────────────────────────────────────────────────────
        if catalog_data is None:
            logger.info("Loading CISA KEV catalog from %s", catalog_path)
            catalog_data = self.load_catalog(catalog_path)

        # ── Validate ──────────────────────────────────────────────────
        is_valid, reason = self.validate_catalog(catalog_data)
        if not is_valid:
            raise ValueError(f"Catalog validation failed: {reason}")

        content_hash = self.compute_content_hash(catalog_data)
        version = source_version or catalog_data.get("catalogVersion") or "unknown"
        date_released_raw = catalog_data.get("dateReleased")
        date_released = self._parse_date(date_released_raw)
        entries = catalog_data["vulnerabilities"]
        if limit:
            entries = entries[:limit]

        # ── Upsert KnowledgeSource ────────────────────────────────────
        ks = db.query(KnowledgeSource).filter_by(source_type=PROVIDER).first()
        if not ks:
            ks = KnowledgeSource(
                source_type=PROVIDER,
                name="CISA Known Exploited Vulnerabilities Catalog",
                source_url="https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json",
            )
            db.add(ks)
            db.flush()

        ks.version = version
        ks.content_hash = content_hash
        ks.published_at = date_released
        ks.retrieved_at = _utcnow()
        ks.record_count = len(entries)

        # ── Create KnowledgeSyncRun ───────────────────────────────────
        sync_run = KnowledgeSyncRun(
            source_id=ks.id,
            started_at=_utcnow(),
            status="RUNNING",
            content_hash=content_hash,
            details={"version": version, "dry_run": dry_run, "limit": limit},
        )
        db.add(sync_run)
        db.flush()

        if dry_run:
            sync_run.status = "COMPLETED"
            sync_run.completed_at = _utcnow()
            sync_run.records_seen = len(entries)
            db.commit()
            return sync_run

        # ── Seed OWASP categories ─────────────────────────────────────
        owasp_map = self._seed_owasp_categories(db, source_version=version)
        db.flush()

        # ── Process entries ───────────────────────────────────────────
        created = updated = skipped = failed = 0
        batch_count = 0

        for entry in entries:
            try:
                record = self._normalize_record(entry)
            except Exception as exc:
                logger.warning("Normalization error for entry %s: %s", entry.get("cveID"), exc)
                failed += 1
                continue

            sync_run.records_seen += 1
            canonical_id = record["canonical_id"]
            cve_id = record["cve_id"]

            try:
                # ── Upsert SecurityAdvisory ───────────────────────────
                advisory = (
                    db.query(SecurityAdvisory)
                    .filter_by(canonical_id=canonical_id)
                    .first()
                )
                if advisory is None:
                    advisory = SecurityAdvisory(
                        canonical_id=canonical_id,
                        provider=PROVIDER,
                        provider_record_id=cve_id,
                        cve_id=cve_id,
                        title=record["title"],
                        summary=record["summary"],
                        vendor=record["vendor"],
                        product=record["product"],
                        date_added=record["date_added"],
                        due_date=record["due_date"],
                        known_ransomware_use=record["known_ransomware_use"],
                        forensic_triage=record["forensic_triage"],
                        source_url=record["source_url"],
                        confidence=record["confidence"],
                        raw_hash=content_hash,
                    )
                    db.add(advisory)
                    db.flush()
                    created += 1
                else:
                    # Update mutable fields
                    advisory.title = record["title"]
                    advisory.summary = record["summary"]
                    advisory.vendor = record["vendor"]
                    advisory.product = record["product"]
                    advisory.known_ransomware_use = record["known_ransomware_use"]
                    advisory.forensic_triage = record["forensic_triage"]
                    advisory.source_url = record["source_url"]
                    advisory.raw_hash = content_hash
                    db.flush()
                    updated += 1

                # ── Upsert CWEs and link associations ──────────────────
                for cwe_str in record.get("cwes", []):
                    if not cwe_str:
                        continue
                    cwe_entry = db.query(CWEEntry).filter_by(cwe_id=cwe_str).first()
                    if not cwe_entry:
                        cwe_name = get_cwe_name(cwe_str)
                        cwe_entry = CWEEntry(
                            cwe_id=cwe_str,
                            name=cwe_name,
                            source="MITRE",
                            source_version="4.x",
                        )
                        db.add(cwe_entry)
                        db.flush()

                    # advisory <-> CWE
                    self._insert_advisory_cwe(db, advisory.id, cwe_entry.id)

                    # CWE <-> OWASP
                    owasp_cat_id = get_owasp_2021_category_for_cwe(cwe_str)
                    if owasp_cat_id and owasp_cat_id in owasp_map:
                        owasp_obj = owasp_map[owasp_cat_id]
                        self._insert_cwe_owasp(db, cwe_entry.id, owasp_obj.id)
                        # advisory <-> OWASP
                        self._insert_advisory_owasp(db, advisory.id, owasp_obj.id)

                # ── Upsert CVE VulnerabilityReference ─────────────────
                existing_ref = (
                    db.query(VulnerabilityReference)
                    .filter_by(advisory_id=advisory.id, reference_type="CVE", reference_value=cve_id)
                    .first()
                )
                if not existing_ref:
                    ref = VulnerabilityReference(
                        advisory_id=advisory.id,
                        reference_type="CVE",
                        reference_value=cve_id,
                        source=PROVIDER,
                    )
                    db.add(ref)

                batch_count += 1
                if batch_count % BATCH_SIZE == 0:
                    db.commit()
                    logger.info(
                        "Batch committed: %d processed so far (created=%d, updated=%d)",
                        batch_count, created, updated,
                    )

            except Exception as exc:
                logger.warning("Failed to process entry %s: %s", cve_id, exc)
                db.rollback()
                failed += 1

        # ── Final commit ──────────────────────────────────────────────
        sync_run.records_created = created
        sync_run.records_updated = updated
        sync_run.records_skipped = skipped
        sync_run.records_failed = failed
        sync_run.error_count = failed
        sync_run.status = "COMPLETED" if failed == 0 else "PARTIAL"
        sync_run.completed_at = _utcnow()

        ks.status = "ACTIVE"
        db.commit()

        logger.info(
            "CISA KEV ingestion complete: seen=%d created=%d updated=%d skipped=%d failed=%d",
            sync_run.records_seen, created, updated, skipped, failed,
        )
        return sync_run
