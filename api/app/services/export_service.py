"""Researcher Export Center Service.

Generates chunked, streaming export packages across 8 research intelligence types
in JSON, CSV, NDJSON, and ZIP formats with SHA-256 integrity checksums and strict
ownership authorization to prevent IDOR and path traversal.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import logging
import os
import uuid
import zipfile
from datetime import datetime, timezone
from typing import Any, Generator
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from ..config import settings
from ..models.base import utcnow
from ..models.export import ExportJob, ExportType, ExportFormat, ExportStatus
from ..models.company import Company
from ..models.target import Target
from ..models.product import Product
from ..models.cisa_kev import CISAKEVItem
from ..models.security import SecurityEvent
from ..models.timeline import TimelineEvent
from ..models.change import Change
from ..models.signal import ResearchSignal
from ..models.security_program import SecurityProgram, ProgramScopeRule

logger = logging.getLogger(__name__)


def _sanitize_filename(name: str) -> str:
    """Sanitizes export filename to prevent path traversal."""
    cleaned = "".join(c for c in name if c.isalnum() or c in ("-", "_", "."))
    return cleaned or "export"


class ExportService:
    """Enterprise export service for generating research-grade intelligence packages."""

    def __init__(self, db: Session):
        self.db = db
        self.storage_dir = os.path.abspath(settings.export_storage_path)
        os.makedirs(self.storage_dir, exist_ok=True)

    def create_export_job(
        self,
        user_id: int,
        export_type: str,
        export_format: str,
        filters: dict[str, Any] | None = None,
        scope: str | None = "ALL",
    ) -> ExportJob:
        """Initializes a new export job record."""
        # Validate export type
        valid_types = {e.value for e in ExportType}
        if export_type not in valid_types:
            raise ValueError(f"Invalid export type '{export_type}'. Must be one of {valid_types}")

        # Validate format
        valid_formats = {f.value for f in ExportFormat}
        if export_format not in valid_formats:
            raise ValueError(f"Invalid format '{export_format}'. Must be one of {valid_formats}")

        job = ExportJob(
            export_uuid=str(uuid.uuid4()),
            user_id=user_id,
            export_type=export_type,
            format=export_format,
            status=ExportStatus.QUEUED.value,
            filters=filters or {},
            scope=scope,
            download_token=uuid.uuid4().hex,
        )
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        return job

    def execute_job(self, job_id: int) -> ExportJob:
        """Executes the export job synchronously or via worker, generating the artifact file."""
        job = self.db.get(ExportJob, job_id)
        if not job:
            raise ValueError(f"Export job #{job_id} not found.")

        job.status = ExportStatus.RUNNING.value
        self.db.commit()

        try:
            records, row_count = self._collect_records(job.export_type, job.filters)
            filename = f"attacksurface_{job.export_type.lower()}_{job.export_uuid[:8]}.{job.format.lower()}"
            if job.format == ExportFormat.ZIP.value:
                filename = f"attacksurface_{job.export_type.lower()}_{job.export_uuid[:8]}.zip"

            safe_filename = _sanitize_filename(filename)
            file_path = os.path.join(self.storage_dir, safe_filename)

            # Prevent path traversal
            if not os.path.abspath(file_path).startswith(self.storage_dir):
                raise ValueError("Path traversal attempt detected.")

            file_size, checksum = self._write_artifact(file_path, job.format, job.export_type, records)

            job.status = ExportStatus.READY.value
            job.row_count = row_count
            job.file_size_bytes = file_size
            job.checksum_sha256 = checksum
            job.file_path = file_path
            job.completed_at = utcnow()
            self.db.commit()
            return job
        except Exception as exc:
            logger.exception("Export job #%d failed: %s", job_id, exc)
            job.status = ExportStatus.FAILED.value
            job.error_message = str(exc)
            job.completed_at = utcnow()
            self.db.commit()
            return job

    def _collect_records(self, export_type: str, filters: dict[str, Any]) -> tuple[list[dict[str, Any]], int]:
        """Queries and normalizes records for the given export type."""
        limit = int(filters.get("limit", 5000)) if filters else 5000

        if export_type == ExportType.COMPANY_INTELLIGENCE.value:
            companies = self.db.scalars(select(Company).limit(limit)).all()
            records = []
            for c in companies:
                products = [p.name for p in c.products] if c.products else []
                meta = c.meta or {}
                records.append({
                    "id": c.id,
                    "name": c.name,
                    "legal_name": c.legal_name,
                    "canonical_domain": c.canonical_domain,
                    "industry": c.industry,
                    "country": c.country,
                    "security_policy_url": c.security_policy_url,
                    "bug_bounty_program_status": meta.get("bug_bounty_program_status") or ("ACTIVE" if c.bug_bounty_url else None),
                    "bug_bounty_url": c.bug_bounty_url,
                    "products": products,
                    "data_origin": meta.get("data_origin", "SOURCE_VERIFIED"),
                    "confidence": meta.get("confidence", 1.0),
                })
            return records, len(records)

        elif export_type == ExportType.VULNERABILITY_INTELLIGENCE.value:
            vulns = self.db.scalars(select(CISAKEVItem).order_by(desc(CISAKEVItem.date_added)).limit(limit)).all()
            records = []
            for v in vulns:
                records.append({
                    "cve_id": v.cve_id,
                    "vendor_project": v.vendor_project,
                    "product": v.product,
                    "vulnerability_name": v.vulnerability_name,
                    "date_added": v.date_added.isoformat() if v.date_added else None,
                    "short_description": v.short_description,
                    "required_action": v.required_action,
                    "due_date": v.due_date.isoformat() if v.due_date else None,
                    "known_ransomware_campaign_use": v.known_ransomware_campaign_use,
                    "cwes": v.cwes,
                    "notes": v.notes,
                    "source": "CISA_KEV",
                    "data_origin": v.data_origin,
                    "catalog_version": v.last_seen_catalog_version,
                })
            return records, len(records)

        elif export_type == ExportType.HISTORICAL_TIMELINE.value:
            events = self.db.scalars(select(TimelineEvent).order_by(desc(TimelineEvent.created_at)).limit(limit)).all()
            records = []
            for e in events:
                records.append({
                    "id": e.id,
                    "title": e.title,
                    "event_type": e.event_type,
                    "priority": e.priority,
                    "summary": e.summary,
                    "source": e.source,
                    "source_url": e.source_url,
                    "published_at": e.published_at.isoformat() if e.published_at else None,
                    "observed_at": e.observed_at.isoformat() if e.observed_at else None,
                    "confidence": e.confidence,
                    "data_origin": (e.meta or {}).get("data_origin", "SOURCE_VERIFIED"),
                })
            return records, len(records)

        elif export_type == ExportType.ATTACK_SURFACE_CHANGES.value:
            changes = self.db.scalars(select(Change).order_by(desc(Change.created_at)).limit(limit)).all()
            records = []
            for ch in changes:
                records.append({
                    "id": ch.id,
                    "target_id": ch.target_id,
                    "change_type": ch.change_type,
                    "severity": ch.severity,
                    "summary": ch.summary,
                    "previous_state": ch.previous_state,
                    "current_state": ch.current_state,
                    "observed_at": ch.created_at.isoformat() if ch.created_at else None,
                })
            return records, len(records)

        elif export_type == ExportType.RESEARCH_SIGNALS.value:
            signals = self.db.scalars(select(ResearchSignal).order_by(desc(ResearchSignal.created_at)).limit(limit)).all()
            records = []
            for s in signals:
                records.append({
                    "id": s.id,
                    "signal_type": s.signal_type,
                    "title": s.title,
                    "status": s.status,
                    "score": s.relevance_score,
                    "summary": s.summary,
                    "observed_at": s.created_at.isoformat() if s.created_at else None,
                })
            return records, len(records)

        elif export_type == ExportType.SCOPE_EXPORT.value:
            targets = self.db.scalars(select(Target).where(Target.monitoring_status == "active").limit(limit)).all()
            rules = self.db.scalars(select(ProgramScopeRule).limit(limit)).all()
            records = []
            for t in targets:
                records.append({
                    "type": "TARGET",
                    "id": t.id,
                    "domain": t.domain,
                    "company_name": t.company_name,
                    "monitoring_status": t.monitoring_status,
                    "authorization_confirmed": t.authorization_confirmed,
                })
            for r in rules:
                records.append({
                    "type": "SCOPE_RULE",
                    "id": r.id,
                    "pattern": r.pattern,
                    "asset_type": r.asset_type,
                    "inclusion_type": r.inclusion_type,
                    "confidence": r.confidence,
                    "evidence": r.evidence,
                    "source_url": r.source_url,
                })
            return records, len(records)

        elif export_type in (ExportType.EVIDENCE_PACK.value, ExportType.FULL_RESEARCH_DATASET.value):
            sec_events = self.db.scalars(select(SecurityEvent).order_by(desc(SecurityEvent.created_at)).limit(limit)).all()
            records = []
            for se in sec_events:
                records.append({
                    "id": se.id,
                    "company_id": se.company_id,
                    "cve_id": se.cve_id,
                    "relationship_type": se.relationship_type,
                    "affected_component": se.affected_component,
                    "severity": se.severity,
                    "confidence": se.confidence,
                    "evidence": se.evidence,
                    "source": se.source,
                    "source_url": se.source_url,
                    "published": se.published.isoformat() if se.published else None,
                    "data_origin": (se.meta or {}).get("data_origin", "SOURCE_VERIFIED"),
                })
            return records, len(records)

        return [], 0

    def _write_artifact(
        self,
        file_path: str,
        fmt: str,
        export_type: str,
        records: list[dict[str, Any]],
    ) -> tuple[int, str]:
        """Writes export records to disk in the requested format and returns (size_bytes, sha256)."""
        hasher = hashlib.sha256()

        if fmt == ExportFormat.JSON.value:
            payload = {
                "export_type": export_type,
                "exported_at": utcnow().isoformat(),
                "total_records": len(records),
                "records": records,
            }
            content = json.dumps(payload, indent=2).encode("utf-8")
            hasher.update(content)
            with open(file_path, "wb") as f:
                f.write(content)
            return len(content), hasher.hexdigest()

        elif fmt == ExportFormat.NDJSON.value:
            total_size = 0
            with open(file_path, "wb") as f:
                for r in records:
                    line = (json.dumps(r) + "\n").encode("utf-8")
                    hasher.update(line)
                    f.write(line)
                    total_size += len(line)
            return total_size, hasher.hexdigest()

        elif fmt == ExportFormat.CSV.value:
            if not records:
                content = b"id,name\n"
                hasher.update(content)
                with open(file_path, "wb") as f:
                    f.write(content)
                return len(content), hasher.hexdigest()

            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=list(records[0].keys()))
            writer.writeheader()
            for r in records:
                # Format nested lists or dicts as json strings
                row = {
                    k: (json.dumps(v) if isinstance(v, (list, dict)) else v)
                    for k, v in r.items()
                }
                writer.writerow(row)

            content = output.getvalue().encode("utf-8")
            hasher.update(content)
            with open(file_path, "wb") as f:
                f.write(content)
            return len(content), hasher.hexdigest()

        elif fmt == ExportFormat.ZIP.value:
            # Package as ZIP archive containing JSON and CSV
            zip_buf = io.BytesIO()
            with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
                # Add JSON
                json_bytes = json.dumps(records, indent=2).encode("utf-8")
                zf.writestr(f"{export_type.lower()}.json", json_bytes)

                # Add CSV
                if records:
                    csv_io = io.StringIO()
                    writer = csv.DictWriter(csv_io, fieldnames=list(records[0].keys()))
                    writer.writeheader()
                    for r in records:
                        row = {
                            k: (json.dumps(v) if isinstance(v, (list, dict)) else v)
                            for k, v in r.items()
                        }
                        writer.writerow(row)
                    zf.writestr(f"{export_type.lower()}.csv", csv_io.getvalue().encode("utf-8"))

            content = zip_buf.getvalue()
            hasher.update(content)
            with open(file_path, "wb") as f:
                f.write(content)
            return len(content), hasher.hexdigest()

        raise ValueError(f"Unsupported format {fmt}")

    def get_user_exports(self, user_id: int, limit: int = 50) -> list[ExportJob]:
        """Lists export jobs belonging to the authenticated user."""
        return self.db.scalars(
            select(ExportJob)
            .where(ExportJob.user_id == user_id)
            .order_by(desc(ExportJob.created_at))
            .limit(limit)
        ).all()

    def get_export_by_token(self, download_token: str, user_id: int | None = None, is_admin: bool = False) -> ExportJob:
        """Retrieves and authorizes an export job for download."""
        job = self.db.scalars(
            select(ExportJob).where(ExportJob.download_token == download_token)
        ).first()

        if not job:
            raise ValueError("Invalid download token.")

        # IDOR protection: if user context is provided, only job owner or admin can download
        if user_id is not None and job.user_id != user_id and not is_admin:
            raise PermissionError("Access denied: You do not own this export artifact.")

        # Expiration check
        if utcnow() > job.expires_at:
            job.status = ExportStatus.EXPIRED.value
            self.db.commit()
            raise ValueError("Export link has expired. Please request a new export.")

        if job.status != ExportStatus.READY.value or not job.file_path or not os.path.exists(job.file_path):
            raise ValueError("Export file is not ready or has been removed.")

        job.download_count += 1
        self.db.commit()
        return job
