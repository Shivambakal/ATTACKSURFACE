"""CISA Known Exploited Vulnerabilities (KEV) Live Feed Service.

Fetches the official CISA KEV machine-readable JSON feed:
https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json

Implements:
- Strict SSRF protection and allowlisted hosts
- Max response size limits (50MB) and decompression bomb protection
- SHA-256 raw content verification
- Immutable raw snapshot persistence (CISAFeedSnapshot)
- Field-level delta detection (NEW, CHANGED, UNCHANGED, REMOVED)
- Exact source-faithful persistence with data_origin=SOURCE_VERIFIED
- Real connection and freshness health states (never fake 'Healthy')
"""
from __future__ import annotations

import hashlib
import json
import logging
import time
from datetime import datetime, timezone, timedelta
from typing import Any
from urllib.parse import urlparse

import httpx
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from ..config import settings
from ..models.base import utcnow
from ..models.cisa_kev import CISAFeedSnapshot, CISAKEVItem

logger = logging.getLogger(__name__)

# Constants & Safety Limits
OFFICIAL_CISA_FEED_URL = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"
ALLOWED_HOSTS = {"www.cisa.gov", "cisa.gov"}
MAX_RESPONSE_BYTES = 50 * 1024 * 1024  # 50 MB
REQUEST_TIMEOUT_SECONDS = 30.0
PARSER_VERSION = "2.0.0"


def _parse_iso_date(val: str | None) -> datetime | None:
    if not val:
        return None
    val = val.strip()
    try:
        # Check standard ISO or YYYY-MM-DD
        if "T" in val:
            return datetime.fromisoformat(val.replace("Z", "+00:00"))
        return datetime.strptime(val, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except Exception:
        return None


class CISAFeedService:
    """Enterprise service for ingesting, validating, diffing, and maintaining the CISA KEV catalog."""

    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def validate_feed_url(url: str) -> None:
        """Enforce SSRF protection by verifying schema and allowlisted host."""
        parsed = urlparse(url)
        if parsed.scheme != "https":
            raise ValueError(f"Insecure scheme '{parsed.scheme}'; only HTTPS is permitted.")
        if parsed.hostname not in ALLOWED_HOSTS:
            raise ValueError(f"Host '{parsed.hostname}' is not in allowlisted CISA feed hosts.")

    def fetch_live_feed(self, feed_url: str = OFFICIAL_CISA_FEED_URL) -> tuple[dict[str, Any], str, int, int]:
        """Performs a secure, streamed GET request to the official CISA KEV feed.

        Returns:
            (parsed_json, raw_text, status_code, duration_ms)
        """
        self.validate_feed_url(feed_url)
        start_time = time.time()

        headers = {
            "User-Agent": settings.collector_user_agent,
            "Accept": "application/json",
        }

        with httpx.Client(timeout=REQUEST_TIMEOUT_SECONDS, follow_redirects=True) as client:
            with client.stream("GET", feed_url, headers=headers) as resp:
                status_code = resp.status_code
                if status_code != 200:
                    duration_ms = int((time.time() - start_time) * 1000)
                    raise RuntimeError(f"CISA feed returned HTTP status {status_code}")

                # Stream and enforce maximum response size limit
                chunks = []
                total_bytes = 0
                for chunk in resp.iter_bytes():
                    total_bytes += len(chunk)
                    if total_bytes > MAX_RESPONSE_BYTES:
                        raise ValueError(f"Response size exceeded safety limit of {MAX_RESPONSE_BYTES} bytes")
                    chunks.append(chunk)

                raw_bytes = b"".join(chunks)
                duration_ms = int((time.time() - start_time) * 1000)

        raw_text = raw_bytes.decode("utf-8")
        try:
            parsed = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Malformed JSON in CISA feed: {exc}") from exc

        return parsed, raw_text, status_code, duration_ms

    @staticmethod
    def validate_schema(data: dict[str, Any]) -> tuple[bool, str]:
        """Validates standard CISA KEV JSON schema."""
        if not isinstance(data, dict):
            return False, "Root element must be a JSON object."

        required_keys = {"title", "catalogVersion", "dateReleased", "count", "vulnerabilities"}
        missing = required_keys - set(data.keys())
        if missing:
            return False, f"Missing required top-level keys: {sorted(missing)}"

        vulns = data.get("vulnerabilities")
        if not isinstance(vulns, list):
            return False, "'vulnerabilities' must be a JSON array."

        if not vulns:
            return False, "Feed contains empty vulnerabilities array."

        # Validate sample entry structure
        first = vulns[0]
        entry_required = {"cveID", "vendorProject", "product", "vulnerabilityName", "dateAdded", "shortDescription"}
        entry_missing = entry_required - set(first.keys())
        if entry_missing:
            return False, f"Vulnerability item missing required keys: {sorted(entry_missing)}"

        return True, ""

    def get_latest_snapshot(self) -> CISAFeedSnapshot | None:
        """Retrieves the most recent successfully ingested feed snapshot."""
        return self.db.scalars(
            select(CISAFeedSnapshot)
            .where(CISAFeedSnapshot.success == True)  # noqa: E712
            .order_by(desc(CISAFeedSnapshot.fetched_at))
            .limit(1)
        ).first()

    def sync_catalog(self, feed_url: str = OFFICIAL_CISA_FEED_URL, force: bool = False) -> dict[str, Any]:
        """Performs full end-to-end synchronization:

        1. Fetches feed with SSRF and size safeguards.
        2. Calculates content SHA-256 hash.
        3. Saves immutable raw CISAFeedSnapshot.
        4. Detects field-level deltas (NEW, CHANGED, UNCHANGED, REMOVED).
        5. Upserts CISAKEVItem records with exact fidelity.
        6. Updates source metrics.
        """
        fetched_at = utcnow()
        error_message = None
        http_status = 200
        duration_ms = 0
        raw_text = ""
        parsed = {}

        try:
            parsed, raw_text, http_status, duration_ms = self.fetch_live_feed(feed_url)
            is_valid, validation_err = self.validate_schema(parsed)
            if not is_valid:
                raise ValueError(f"Schema validation failed: {validation_err}")
        except Exception as exc:
            error_message = str(exc)
            logger.error("CISA KEV fetch failed: %s", error_message)
            # Create failed snapshot record for auditability
            fail_snapshot = CISAFeedSnapshot(
                source_url=feed_url,
                fetched_at=fetched_at,
                http_status=http_status if http_status != 200 else 500,
                content_sha256=hashlib.sha256(raw_text.encode("utf-8")).hexdigest() if raw_text else "",
                catalog_version="UNKNOWN",
                declared_count=0,
                raw_payload=raw_text[:1000] if raw_text else "FETCH_FAILED",
                parser_version=PARSER_VERSION,
                fetch_duration_ms=duration_ms,
                success=False,
                error=error_message,
            )
            self.db.add(fail_snapshot)
            self.db.commit()
            return {
                "success": False,
                "error": error_message,
                "http_status": http_status,
                "duration_ms": duration_ms,
                "records_received": 0,
                "new": 0,
                "changed": 0,
                "unchanged": 0,
                "removed": 0,
            }

        # Calculate raw SHA-256 hash
        content_hash = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()
        catalog_version = str(parsed.get("catalogVersion", "UNKNOWN"))
        date_released = _parse_iso_date(parsed.get("dateReleased"))
        declared_count = int(parsed.get("count", len(parsed.get("vulnerabilities", []))))
        vulns = parsed.get("vulnerabilities", [])

        # Check if hash identical to latest snapshot
        latest = self.get_latest_snapshot()
        if latest and latest.content_sha256 == content_hash and not force:
            logger.info("CISA KEV feed hash %s unchanged from snapshot %d", content_hash, latest.id)
            return {
                "success": True,
                "status": "UNCHANGED",
                "snapshot_id": latest.id,
                "catalog_version": catalog_version,
                "date_released": date_released.isoformat() if date_released else None,
                "content_sha256": content_hash,
                "records_received": len(vulns),
                "new": 0,
                "changed": 0,
                "unchanged": len(vulns),
                "removed": 0,
                "duration_ms": duration_ms,
            }

        # Save immutable raw snapshot
        snapshot = CISAFeedSnapshot(
            source_url=feed_url,
            fetched_at=fetched_at,
            http_status=http_status,
            content_sha256=content_hash,
            catalog_version=catalog_version,
            date_released=date_released,
            declared_count=declared_count,
            raw_payload=raw_text,  # Full immutable raw response
            parser_version=PARSER_VERSION,
            fetch_duration_ms=duration_ms,
            success=True,
            error=None,
        )
        self.db.add(snapshot)
        self.db.flush()

        # Load existing CISAKEVItems into lookup
        existing_items = {
            item.cve_id: item
            for item in self.db.scalars(select(CISAKEVItem)).all()
        }

        seen_cves = set()
        new_count = 0
        changed_count = 0
        unchanged_count = 0
        changed_details: list[dict[str, Any]] = []

        for v in vulns:
            cve_id = str(v.get("cveID", "")).strip().upper()
            if not cve_id:
                continue
            seen_cves.add(cve_id)

            vendor = str(v.get("vendorProject", "")).strip()
            product = str(v.get("product", "")).strip()
            vuln_name = str(v.get("vulnerabilityName", "")).strip()
            date_added = _parse_iso_date(v.get("dateAdded"))
            short_desc = str(v.get("shortDescription", "")).strip()
            required_act = v.get("requiredAction")
            if required_act:
                required_act = str(required_act).strip()
            due_dt = _parse_iso_date(v.get("dueDate"))
            ransomware_use = str(v.get("knownRansomwareCampaignUse", "Unknown")).strip()
            notes = v.get("notes")
            if notes:
                notes = str(notes).strip()
            cwes = v.get("cwes", [])
            if not isinstance(cwes, list):
                cwes = [str(cwes)]

            raw_item_str = json.dumps(v, sort_keys=True)
            item_hash = hashlib.sha256(raw_item_str.encode("utf-8")).hexdigest()

            if cve_id not in existing_items:
                # NEW record
                new_item = CISAKEVItem(
                    cve_id=cve_id,
                    vendor_project=vendor,
                    product=product,
                    vulnerability_name=vuln_name,
                    date_added=date_added,
                    short_description=short_desc,
                    required_action=required_act,
                    due_date=due_dt,
                    known_ransomware_campaign_use=ransomware_use,
                    notes=notes,
                    cwes=cwes,
                    first_seen_catalog_version=catalog_version,
                    last_seen_catalog_version=catalog_version,
                    first_seen_at=fetched_at,
                    last_seen_at=fetched_at,
                    source_snapshot_id=snapshot.id,
                    raw_source_hash=item_hash,
                    data_origin="SOURCE_VERIFIED",
                    is_active=True,
                )
                self.db.add(new_item)
                new_count += 1
            else:
                existing = existing_items[cve_id]
                # Compare fields for delta
                field_diffs = {}
                if existing.vendor_project != vendor:
                    field_diffs["vendor_project"] = {"old": existing.vendor_project, "new": vendor}
                if existing.product != product:
                    field_diffs["product"] = {"old": existing.product, "new": product}
                if existing.vulnerability_name != vuln_name:
                    field_diffs["vulnerability_name"] = {"old": existing.vulnerability_name, "new": vuln_name}
                if existing.short_description != short_desc:
                    field_diffs["short_description"] = {"old": existing.short_description, "new": short_desc}
                if existing.required_action != required_act:
                    field_diffs["required_action"] = {"old": existing.required_action, "new": required_act}
                if existing.known_ransomware_campaign_use != ransomware_use:
                    field_diffs["known_ransomware_campaign_use"] = {"old": existing.known_ransomware_campaign_use, "new": ransomware_use}
                if existing.notes != notes:
                    field_diffs["notes"] = {"old": existing.notes, "new": notes}
                if (existing.due_date and due_dt and existing.due_date.date() != due_dt.date()) or (bool(existing.due_date) != bool(due_dt)):
                    field_diffs["due_date"] = {
                        "old": existing.due_date.isoformat() if existing.due_date else None,
                        "new": due_dt.isoformat() if due_dt else None,
                    }

                if field_diffs:
                    changed_count += 1
                    if len(changed_details) < 50:
                        changed_details.append({"cve_id": cve_id, "diff": field_diffs})
                    # Update fields
                    existing.vendor_project = vendor
                    existing.product = product
                    existing.vulnerability_name = vuln_name
                    existing.short_description = short_desc
                    existing.required_action = required_act
                    existing.due_date = due_dt
                    existing.known_ransomware_campaign_use = ransomware_use
                    existing.notes = notes
                    existing.cwes = cwes
                    existing.last_seen_catalog_version = catalog_version
                    existing.last_seen_at = fetched_at
                    existing.source_snapshot_id = snapshot.id
                    existing.raw_source_hash = item_hash
                    existing.is_active = True
                else:
                    unchanged_count += 1
                    existing.last_seen_catalog_version = catalog_version
                    existing.last_seen_at = fetched_at
                    existing.is_active = True

        # Check for removed records
        removed_count = 0
        for cve_id, existing in existing_items.items():
            if cve_id not in seen_cves and existing.is_active:
                existing.is_active = False
                removed_count += 1

        self.db.commit()

        logger.info(
            "CISA KEV Sync completed: %d received, %d new, %d changed, %d unchanged, %d removed",
            len(vulns), new_count, changed_count, unchanged_count, removed_count
        )

        return {
            "success": True,
            "snapshot_id": snapshot.id,
            "catalog_version": catalog_version,
            "date_released": date_released.isoformat() if date_released else None,
            "content_sha256": content_hash,
            "records_received": len(vulns),
            "new": new_count,
            "changed": changed_count,
            "unchanged": unchanged_count,
            "removed": removed_count,
            "duration_ms": duration_ms,
            "recent_diffs": changed_details,
        }

    def get_source_health(self) -> dict[str, Any]:
        """Computes strict real connection and freshness health (no fake Healthy)."""
        latest_snapshot = self.get_latest_snapshot()
        total_items = self.db.query(CISAKEVItem).count()
        active_items = self.db.query(CISAKEVItem).filter(CISAKEVItem.is_active == True).count()  # noqa: E712

        if not latest_snapshot:
            return {
                "name": "CISA KEV",
                "feed_url": OFFICIAL_CISA_FEED_URL,
                "connection_state": "NEVER_CONNECTED",
                "freshness_state": "UNKNOWN",
                "last_successful_fetch": None,
                "last_attempt": None,
                "catalog_version": None,
                "date_released": None,
                "total_records": 0,
                "active_records": 0,
                "content_sha256": None,
                "latency_ms": 0,
                "error": None,
            }

        now = utcnow()
        age = (now - latest_snapshot.fetched_at).total_seconds()
        if age < 86400:
            freshness = "FRESH"
        elif age < 7 * 86400:
            freshness = "AGING"
        else:
            freshness = "STALE"

        conn_state = "CONNECTED" if latest_snapshot.success else "ERROR"
        if latest_snapshot.success and freshness == "STALE":
            conn_state = "STALE"

        return {
            "name": "CISA KEV",
            "feed_url": latest_snapshot.source_url,
            "connection_state": conn_state,
            "freshness_state": freshness,
            "last_successful_fetch": latest_snapshot.fetched_at.isoformat(),
            "last_attempt": latest_snapshot.created_at.isoformat(),
            "catalog_version": latest_snapshot.catalog_version,
            "date_released": latest_snapshot.date_released.isoformat() if latest_snapshot.date_released else None,
            "total_records": total_items,
            "active_records": active_items,
            "content_sha256": latest_snapshot.content_sha256,
            "latency_ms": latest_snapshot.fetch_duration_ms,
            "error": latest_snapshot.error,
        }
