"""Security Knowledge Base correlation service.

Provides cross-referencing between security advisories/CWEs and the
AttackSurface Timeline asset/technology graph.
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from sqlalchemy import func, or_, text
from sqlalchemy.orm import Session

from app.models import (
    SecurityAdvisory,
    CWEEntry,
    OWASPCategory,
    advisory_cwe_association,
    advisory_owasp_association,
)

logger = logging.getLogger(__name__)


class SecurityKnowledgeCorrelationService:
    """Service for correlating advisories with technology and asset data."""

    # ------------------------------------------------------------------
    # Advisory lookup helpers
    # ------------------------------------------------------------------

    @staticmethod
    def get_advisories_for_technology(
        db: Session,
        technology_name: str,
        limit: int = 10,
    ) -> list[SecurityAdvisory]:
        """Return advisories whose vendor or product matches *technology_name*.

        Performs a case-insensitive substring match against both the
        ``vendor`` and ``product`` fields of :class:`SecurityAdvisory`.

        Args:
            db: SQLAlchemy session.
            technology_name: Technology name to search for (e.g. "Log4j").
            limit: Maximum number of results to return.

        Returns:
            Ordered list of matching :class:`SecurityAdvisory` objects
            (most recently added first).
        """
        if not technology_name:
            return []
        pattern = f"%{technology_name}%"
        return (
            db.query(SecurityAdvisory)
            .filter(
                or_(
                    SecurityAdvisory.vendor.ilike(pattern),
                    SecurityAdvisory.product.ilike(pattern),
                    SecurityAdvisory.title.ilike(pattern),
                )
            )
            .order_by(SecurityAdvisory.date_added.desc().nullslast())
            .limit(limit)
            .all()
        )

    @staticmethod
    def get_advisories_for_vendor_product(
        db: Session,
        vendor: str,
        product: str,
        limit: int = 20,
    ) -> list[SecurityAdvisory]:
        """Return advisories matching a specific vendor **and** product pair.

        Args:
            db: SQLAlchemy session.
            vendor: Vendor/project name (case-insensitive substring).
            product: Product name (case-insensitive substring).
            limit: Maximum number of results.

        Returns:
            List of matching advisories ordered by ``date_added`` descending.
        """
        query = db.query(SecurityAdvisory)
        if vendor:
            query = query.filter(SecurityAdvisory.vendor.ilike(f"%{vendor}%"))
        if product:
            query = query.filter(SecurityAdvisory.product.ilike(f"%{product}%"))
        return (
            query.order_by(SecurityAdvisory.date_added.desc().nullslast())
            .limit(limit)
            .all()
        )

    # ------------------------------------------------------------------
    # Historical context
    # ------------------------------------------------------------------

    @staticmethod
    def get_historical_context_for_signal(
        db: Session,
        technology_name: str,
        change_type: str,
        confidence_threshold: float = 0.7,
    ) -> dict[str, Any]:
        """Build a historical context snapshot for a research signal.

        Combines advisory counts, top CWEs, and ransomware-associated
        advisories for a given technology to provide analyst context.

        Args:
            db: SQLAlchemy session.
            technology_name: Technology being assessed (e.g. "Spring").
            change_type: The type of change that triggered the signal
                (e.g. "API_ADDED", "DEPENDENCY_UPDATED").
            confidence_threshold: Minimum advisory ``confidence`` to include.

        Returns:
            A dict with keys:
            - ``technology``: echoed input.
            - ``change_type``: echoed input.
            - ``advisory_count``: total advisories found.
            - ``ransomware_count``: advisories with known ransomware use.
            - ``top_cwes``: list of (cwe_id, count) pairs.
            - ``advisories``: list of advisory dicts (id, title, cve_id, date_added).
        """
        if not technology_name:
            return {
                "technology": technology_name,
                "change_type": change_type,
                "advisory_count": 0,
                "ransomware_count": 0,
                "top_cwes": [],
                "advisories": [],
            }

        pattern = f"%{technology_name}%"
        base_q = (
            db.query(SecurityAdvisory)
            .filter(
                or_(
                    SecurityAdvisory.vendor.ilike(pattern),
                    SecurityAdvisory.product.ilike(pattern),
                    SecurityAdvisory.title.ilike(pattern),
                ),
                SecurityAdvisory.confidence >= confidence_threshold,
            )
        )

        all_advisories = base_q.order_by(SecurityAdvisory.date_added.desc()).all()
        advisory_count = len(all_advisories)

        ransomware_count = sum(
            1 for a in all_advisories
            if (a.known_ransomware_use or "").lower() == "known"
        )

        # Collect CWEs from the advisory IDs
        advisory_ids = [a.id for a in all_advisories]
        top_cwes: list[tuple[str, int]] = []
        if advisory_ids:
            cwe_counts = (
                db.query(CWEEntry.cwe_id, func.count(advisory_cwe_association.c.advisory_id).label("cnt"))
                .join(advisory_cwe_association, advisory_cwe_association.c.cwe_id == CWEEntry.id)
                .filter(advisory_cwe_association.c.advisory_id.in_(advisory_ids))
                .group_by(CWEEntry.cwe_id)
                .order_by(func.count(advisory_cwe_association.c.advisory_id).desc())
                .limit(5)
                .all()
            )
            top_cwes = [(row.cwe_id, row.cnt) for row in cwe_counts]

        advisories_out = [
            {
                "id": a.id,
                "title": a.title,
                "cve_id": a.cve_id,
                "date_added": a.date_added.isoformat() if a.date_added else None,
                "known_ransomware_use": a.known_ransomware_use,
                "confidence": a.confidence,
            }
            for a in all_advisories[:10]
        ]

        return {
            "technology": technology_name,
            "change_type": change_type,
            "advisory_count": advisory_count,
            "ransomware_count": ransomware_count,
            "top_cwes": top_cwes,
            "advisories": advisories_out,
        }

    # ------------------------------------------------------------------
    # Weakness fingerprint
    # ------------------------------------------------------------------

    @staticmethod
    def compute_weakness_fingerprint_with_advisories(
        db: Session,
        company_id: int,
    ) -> dict[str, Any]:
        """Compute a weakness fingerprint for a company based on its assets.

        Cross-references the company's technology stack (via the ``assets``
        and ``technologies`` tables) against the advisory knowledge base to
        produce an aggregated weakness profile.

        Args:
            db: SQLAlchemy session.
            company_id: ID of the company to fingerprint.

        Returns:
            Dict with:
            - ``company_id``: echoed.
            - ``total_advisories``: total matched advisories.
            - ``cwe_distribution``: {cwe_id: count} mapping.
            - ``owasp_distribution``: {category_id: count} mapping.
            - ``ransomware_exposed``: bool, True if any advisory has known ransomware.
            - ``top_advisories``: list of (canonical_id, title, cve_id) dicts.
        """
        # Attempt to pull technology names via company assets
        try:
            tech_rows = db.execute(
                text(
                    """
                    SELECT DISTINCT t.name
                    FROM technologies t
                    JOIN asset_technologies at2 ON at2.technology_id = t.id
                    JOIN assets a ON a.id = at2.asset_id
                    WHERE a.company_id = :cid
                    LIMIT 50
                    """
                ),
                {"cid": company_id},
            ).fetchall()
            tech_names = [row[0] for row in tech_rows if row[0]]
        except Exception:
            tech_names = []

        if not tech_names:
            return {
                "company_id": company_id,
                "total_advisories": 0,
                "cwe_distribution": {},
                "owasp_distribution": {},
                "ransomware_exposed": False,
                "top_advisories": [],
            }

        # Collect matching advisory IDs
        seen_ids: set[int] = set()
        for tech in tech_names:
            pattern = f"%{tech}%"
            rows = (
                db.query(SecurityAdvisory.id)
                .filter(
                    or_(
                        SecurityAdvisory.vendor.ilike(pattern),
                        SecurityAdvisory.product.ilike(pattern),
                    )
                )
                .all()
            )
            for row in rows:
                seen_ids.add(row[0])

        if not seen_ids:
            return {
                "company_id": company_id,
                "total_advisories": 0,
                "cwe_distribution": {},
                "owasp_distribution": {},
                "ransomware_exposed": False,
                "top_advisories": [],
            }

        advisory_ids = list(seen_ids)

        # CWE distribution
        cwe_dist: dict[str, int] = {}
        cwe_rows = (
            db.query(CWEEntry.cwe_id, func.count(advisory_cwe_association.c.advisory_id).label("cnt"))
            .join(advisory_cwe_association, advisory_cwe_association.c.cwe_id == CWEEntry.id)
            .filter(advisory_cwe_association.c.advisory_id.in_(advisory_ids))
            .group_by(CWEEntry.cwe_id)
            .all()
        )
        for row in cwe_rows:
            cwe_dist[row.cwe_id] = row.cnt

        # OWASP distribution
        owasp_dist: dict[str, int] = {}
        owasp_rows = (
            db.query(
                OWASPCategory.category_id,
                func.count(advisory_owasp_association.c.advisory_id).label("cnt"),
            )
            .join(advisory_owasp_association, advisory_owasp_association.c.owasp_category_id == OWASPCategory.id)
            .filter(advisory_owasp_association.c.advisory_id.in_(advisory_ids))
            .group_by(OWASPCategory.category_id)
            .all()
        )
        for row in owasp_rows:
            owasp_dist[row.category_id] = row.cnt

        # Top advisories + ransomware flag
        top_advisories_objs = (
            db.query(SecurityAdvisory)
            .filter(SecurityAdvisory.id.in_(advisory_ids))
            .order_by(SecurityAdvisory.date_added.desc().nullslast())
            .limit(10)
            .all()
        )
        ransomware_exposed = any(
            (a.known_ransomware_use or "").lower() == "known"
            for a in top_advisories_objs
        )

        return {
            "company_id": company_id,
            "total_advisories": len(advisory_ids),
            "cwe_distribution": cwe_dist,
            "owasp_distribution": owasp_dist,
            "ransomware_exposed": ransomware_exposed,
            "top_advisories": [
                {"canonical_id": a.canonical_id, "title": a.title, "cve_id": a.cve_id}
                for a in top_advisories_objs
            ],
        }
