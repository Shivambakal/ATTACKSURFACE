from __future__ import annotations

"""Strict CVE/company validation boundary.

Caller-supplied confidence is never treated as authority. Unknown severity,
CVSS, CWE and dates remain unknown instead of being synthesized.
"""

import json
import logging
import os
import re
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models.company import Company
from app.models.product import Product
from app.models.security import KevEntry, SecurityEvent
from app.models.signal import ResearchSignal

logger = logging.getLogger(__name__)
CVE_RE = re.compile(r"^CVE-\d{4}-\d{4,}$", re.IGNORECASE)
VALID_SEVERITIES = {"CRITICAL", "HIGH", "MEDIUM", "LOW", "NONE"}


class CVEValidationGate:
    _kev_cache: dict[str, dict[str, Any]] | None = None

    @classmethod
    def _load_kev_catalog(cls) -> dict[str, dict[str, Any]]:
        if cls._kev_cache is not None:
            return cls._kev_cache
        cache: dict[str, dict[str, Any]] = {}
        paths = [
            os.path.join(os.path.dirname(__file__), "..", "..", "..", "cisa_kev_catalog.json"),
            os.path.join(os.path.dirname(__file__), "..", "..", "cisa_kev_catalog.json"),
            "cisa_kev_catalog.json",
        ]
        for path in paths:
            if not os.path.exists(path):
                continue
            try:
                with open(path, "r", encoding="utf-8") as fh:
                    payload = json.load(fh)
                for item in payload.get("vulnerabilities", []):
                    cve_id = str(item.get("cveID", "")).strip().upper()
                    if cve_id:
                        cache[cve_id] = item
                break
            except Exception as exc:
                logger.warning("Unable to load CISA KEV catalog from %s: %s", path, exc)
        cls._kev_cache = cache
        return cache

    @staticmethod
    def _norm(value: Any) -> str:
        return str(value or "").strip().casefold()

    @classmethod
    def _company_identifiers(cls, company: Company) -> set[str]:
        values = {cls._norm(company.name), cls._norm(company.canonical_domain.split(".")[0])}
        values.update(cls._norm(alias) for alias in (company.aliases or []))
        return {v for v in values if v}

    @classmethod
    def _matches_company(cls, company: Company, vendor: str, product: str, db: Session) -> bool:
        identifiers = cls._company_identifiers(company)
        vendor_norm = cls._norm(vendor)
        if vendor_norm and any(
            ident == vendor_norm or ident in vendor_norm or vendor_norm in ident
            for ident in identifiers
        ):
            return True
        product_norm = cls._norm(product)
        if not product_norm:
            return False
        product_names = [
            cls._norm(p.name)
            for p in db.query(Product).filter(Product.company_id == company.id).all()
        ]
        return any(
            pname == product_norm or pname in product_norm or product_norm in pname
            for pname in product_names if pname
        )

    @classmethod
    def validate_cve(
        cls,
        db: Session,
        cve_id: str,
        company: Company,
        raw_metadata: dict[str, Any] | None = None,
    ) -> tuple[bool, str, dict[str, Any]]:
        raw_metadata = raw_metadata or {}
        cve_id_clean = str(cve_id or "").strip().upper()
        if not CVE_RE.fullmatch(cve_id_clean):
            return False, "Malformed CVE ID format", {}

        kev = cls._load_kev_catalog().get(cve_id_clean)
        db_kev = db.query(KevEntry).filter(KevEntry.cve_id == cve_id_clean).first()
        if not (kev or db_kev):
            return False, "No authoritative source record for CVE", {}

        if kev:
            description = str(kev.get("shortDescription") or kev.get("vulnerabilityName") or "").strip()
            vendor = str(kev.get("vendorProject") or "").strip()
            product = str(kev.get("product") or "").strip()
            published_at = kev.get("dateAdded")
            cwes = [str(v).strip() for v in (kev.get("cwes") or []) if str(v).strip()]
            notes = str(kev.get("notes") or "")
            match = re.search(r"https?://[^\s;]+", notes)
            source_url = match.group(0).rstrip(".,)") if match else None
            source_name = "CISA KEV"
        else:
            description = str(db_kev.vulnerability_name or "").strip()
            vendor = str(db_kev.vendor or "").strip()
            product = str(db_kev.product or "").strip()
            published_at = db_kev.date_added.isoformat() if getattr(db_kev, "date_added", None) else None
            cwes = [str(db_kev.cwe).strip()] if getattr(db_kev, "cwe", None) else []
            source_url = getattr(db_kev, "source_url", None)
            source_name = "CISA KEV database record"

        if len(description) < 10:
            return False, "Authoritative record lacks a usable description", {}
        if not cls._matches_company(company, vendor, product, db):
            return False, f"Vendor/product relationship does not match company {company.name}", {}

        severity = None
        cvss_score = None
        candidate_severity = str(raw_metadata.get("severity") or "").strip().upper()
        if candidate_severity in VALID_SEVERITIES:
            severity = candidate_severity
        if raw_metadata.get("cvss_score") is not None:
            try:
                score = float(raw_metadata["cvss_score"])
                if 0.0 <= score <= 10.0:
                    cvss_score = score
            except (TypeError, ValueError):
                pass

        return True, "Passed authoritative CVE validation", {
            "cve_id": cve_id_clean,
            "title": f"{cve_id_clean}: {description[:90]}",
            "summary": description,
            "severity": severity,
            "cvss_score": cvss_score,
            "affected_component": product or None,
            "cwe": cwes[0] if cwes else None,
            "status": "OPEN",
            "exploitability": "ACTIVELY_EXPLOITED",
            "source": source_name,
            "source_url": source_url or f"https://nvd.nist.gov/vuln/detail/{cve_id_clean}",
            "published_at": published_at,
            "validated_at": datetime.now(timezone.utc).isoformat(),
            "validation_gate_passed": True,
            "entity_relationship": "VERIFIED",
            "evidence": f"Authoritative {source_name} record matched to company vendor/product.",
        }

    @classmethod
    def get_classified_company_vulnerabilities(cls, db: Session, company_id: int) -> dict[str, Any]:
        company = db.query(Company).filter(Company.id == company_id).first()
        if not company:
            return {"total_confirmed": 0, "total_historical": 0, "total_signals": 0,
                    "severity_breakdown": {s: 0 for s in ("CRITICAL", "HIGH", "MEDIUM", "LOW")},
                    "confirmed_vulnerabilities": [], "historical_vulnerabilities": [], "research_signals": []}

        events = db.query(SecurityEvent).filter(SecurityEvent.company_id == company.id).order_by(SecurityEvent.published.desc().nullslast()).all()
        confirmed: list[dict[str, Any]] = []
        historical: list[dict[str, Any]] = []
        for event in events:
            if not event.cve_id:
                continue
            pub_dt = event.published
            item = {
                "id": f"cve_{event.id}", "cve_id": event.cve_id,
                "title": event.summary[:90] if event.summary else event.cve_id,
                "summary": event.summary, "severity": (event.severity or "UNKNOWN").upper(),
                "cvss_score": None, "affected_asset": company.canonical_domain,
                "affected_component": event.affected_component, "cwe": event.vulnerability_class,
                "status": "OPEN", "exploitability": "CONFIRMED_PUBLIC_DISCLOSURE",
                "source": event.source, "source_url": event.source_url,
                "published_at": pub_dt.isoformat() if pub_dt else None,
                "evidence": event.evidence, "entity_relationship": getattr(event, "relationship_type", None),
            }
            if pub_dt and pub_dt.year < 2024:
                item["status"] = "RESOLVED"
                historical.append(item)
            else:
                confirmed.append(item)

        signals = db.query(ResearchSignal).filter(ResearchSignal.company_id == company.id).order_by(ResearchSignal.created_at.desc()).limit(10).all()
        research_signals = [{
            "id": f"sig_{signal.id}", "signal_type": signal.signal_type, "title": signal.title,
            "summary": signal.summary, "observed_asset": signal.affected_asset or company.canonical_domain,
            "relevance_score": signal.relevance_score, "confidence": signal.confidence,
            "why_it_matters": signal.why_it_matters, "status": "REQUIRES_VERIFICATION",
            "is_vulnerability": False, "evidence": signal.evidence_payload or {},
            "created_at": signal.created_at.isoformat() if signal.created_at else None,
        } for signal in signals]

        severity_breakdown = {severity: sum(1 for item in confirmed if item["severity"] == severity)
                              for severity in ("CRITICAL", "HIGH", "MEDIUM", "LOW")}
        return {"total_confirmed": len(confirmed), "total_historical": len(historical),
                "total_signals": len(research_signals), "severity_breakdown": severity_breakdown,
                "confirmed_vulnerabilities": confirmed, "historical_vulnerabilities": historical,
                "research_signals": research_signals}
