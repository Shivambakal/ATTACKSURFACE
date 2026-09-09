"""Corporate Change Clustering, Fingerprinting, and Evidence Graph Fusion.

Implements:
- Canonical change fingerprinting: SHA-256(company + product + change_type + normalized_object)
- Multi-source convergence: release notes + blog + GitHub + docs -> 1 ChangeCluster
- Entity resolution and ambiguity defense (rejects auto-merging generic names)
- Separation of official documentation, live observation, and third-party correlation
"""
from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from typing import Any
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models.cluster import ChangeCluster
from ..models.company import Company
from ..models.product import Product
from ..models.signal import ResearchSignal, SignalType, SignalStatus
from ..models.timeline import TimelineEvent
from ..services.entity_resolution import EntityResolver
from ..services.evidence_graph import EvidenceGraphService, EvidenceSourceType, EvidenceStrength

logger = logging.getLogger(__name__)

AMBIGUOUS_GENERIC_TERMS = {"server", "web", "api", "cloud", "security", "platform", "workspace", "service"}


def compute_corporate_fingerprint(
    company_id: int,
    product_name: str | None,
    change_type: str,
    normalized_title: str,
    date_str: str = "",
) -> str:
    """Computes a deterministic SHA-256 fingerprint for a corporate change event."""
    norm_prod = (product_name or "").strip().lower()
    norm_title = " ".join(normalized_title.strip().lower().split())
    raw = f"{company_id}:{norm_prod}:{change_type.upper()}:{norm_title}:{date_str}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class CorporateClusteringService:
    """Clusters multi-source corporate changes and builds unified research signals."""

    def __init__(self, db: Session):
        self.db = db
        self.entity_resolver = EntityResolver()
        self.evidence_service = EvidenceGraphService()

    def cluster_extracted_items(
        self,
        company_id: int,
        source_id: int,
        items: list[dict[str, Any]],
        authority_level: str = "OFFICIAL_RELEASE",
    ) -> list[ChangeCluster]:
        """Clusters extracted items from a source document into unified change clusters."""
        company = self.db.get(Company, company_id)
        if not company:
            return []

        clusters: list[ChangeCluster] = []
        now = datetime.now(timezone.utc)

        # Preload existing company clusters into an in-memory fingerprint map for O(1) deduplication
        existing_clusters = self.db.scalars(
            select(ChangeCluster).where(ChangeCluster.company_id == company.id)
        ).all()
        cluster_by_fp: dict[str, ChangeCluster] = {
            (c.meta or {}).get("fingerprint"): c
            for c in existing_clusters
            if (c.meta or {}).get("fingerprint")
        }

        for item in items:
            quality_dec = item.get("quality_decision", "ACCEPTED")
            # Drop rejected low-quality or noise items
            if quality_dec == "REJECTED":
                continue

            raw_title = item.get("title", "")
            raw_product = item.get("product") or ""
            change_type = item.get("change_type", "PRODUCT_UPDATE")
            summary = item.get("summary", "")
            item_url = item.get("url", "")
            sec_relevance = item.get("security_relevance", "CONTEXT")
            freshness = item.get("freshness_category", "RECENT")
            relevance_score = int(item.get("relevance_score", 50))

            # Safely parse publication datetime
            raw_pub = item.get("published_at")
            pub_dt = None
            if isinstance(raw_pub, datetime):
                pub_dt = raw_pub
            elif isinstance(raw_pub, str) and raw_pub.strip():
                try:
                    pub_dt = datetime.fromisoformat(raw_pub.replace("Z", "+00:00"))
                    if pub_dt.tzinfo is None:
                        pub_dt = pub_dt.replace(tzinfo=timezone.utc)
                except Exception:
                    pub_dt = None

            # Guard against generic names
            if raw_product.strip().lower() in AMBIGUOUS_GENERIC_TERMS:
                raw_product = f"{company.name} {raw_product}"

            # Canonical fingerprint
            fp = compute_corporate_fingerprint(
                company_id=company.id,
                product_name=raw_product,
                change_type=change_type,
                normalized_title=raw_title,
            )

            # Check for existing cluster with same fingerprint
            existing_cluster = cluster_by_fp.get(fp)

            if existing_cluster:
                # Merge into existing cluster without duplicating timeline events or signals
                current_urls = list(existing_cluster.affected_urls or [])
                if item_url and item_url not in current_urls:
                    current_urls.append(item_url)
                    existing_cluster.affected_urls = current_urls

                existing_cluster.source_count = (existing_cluster.source_count or 1) + 1
                existing_meta = dict(existing_cluster.meta or {})
                sources = list(existing_meta.get("sources", []))
                if source_id not in sources:
                    sources.append(source_id)
                existing_meta["sources"] = sources
                if existing_cluster.source_count >= 2:
                    existing_meta["cluster_state"] = "CORROBORATED"
                existing_cluster.meta = existing_meta

                clusters.append(existing_cluster)
            else:
                # Create new cluster
                new_cluster = ChangeCluster(
                    company_id=company.id,
                    title=raw_title,
                    summary=summary[:500],
                    primary_category=change_type,
                    affected_urls=[item_url] if item_url else [],
                    source_count=1,
                    meta={
                        "fingerprint": fp,
                        "product": raw_product,
                        "sources": [source_id],
                        "authority_level": authority_level,
                        "cluster_state": "SINGLE_SOURCE",
                        "evidence_state": "DOCUMENTED_NOT_OBSERVED" if "OFFICIAL" in authority_level else "SINGLE_SOURCE",
                        "quality_decision": quality_dec,
                        "security_relevance": sec_relevance,
                        "freshness": freshness,
                    },
                    created_at=now,
                )
                self.db.add(new_cluster)
                self.db.flush()
                cluster_by_fp[fp] = new_cluster

                # Strict Signal Gating:
                # Only create ResearchSignal if: ACCEPTED + ACTIONABLE + NEW/RECENT + score >= 70
                is_actionable = (
                    quality_dec == "ACCEPTED"
                    and sec_relevance == "ACTIONABLE"
                    and freshness in ("NEW", "RECENT")
                    and relevance_score >= 70
                )
                if is_actionable:
                    sig_type = SignalType.NEW_API_SURFACE.value if "API" in change_type else (
                        SignalType.SECURITY_CHANGE.value if "SECURITY" in change_type else SignalType.NEW_FEATURE.value
                    )
                    sig = ResearchSignal(
                        company_id=company.id,
                        cluster_id=new_cluster.id,
                        title=f"{company.name}: {raw_title}",
                        signal_type=sig_type,
                        summary=summary[:500],
                        why_it_matters=f"Actionable security or attack surface change from {authority_level}. Inspect boundary authorization requirements.",
                        relevance_score=relevance_score,
                        confidence_score=90 if "OFFICIAL" in authority_level else 60,
                        security_context_score=relevance_score,
                        priority="HIGH" if relevance_score >= 80 else "MEDIUM",
                        status=SignalStatus.NEW.value,
                        source_count=1,
                        created_at=now,
                    )
                    self.db.add(sig)

                # Generate TimelineEvent with full provenance and temporal classification
                timeline_event = TimelineEvent(
                    company_id=company.id,
                    event_type="CORPORATE_CHANGE",
                    title=f"{company.name}: {raw_title}",
                    summary=summary[:500],
                    source=authority_level,
                    source_url=item_url or None,
                    provenance_category=authority_level,
                    temporal_category=freshness,
                    quality_badge="ACCEPTED" if quality_dec == "ACCEPTED" else "CONTEXT_ONLY",
                    observed_at=now,
                    published_at=pub_dt,
                    confidence=0.9 if "OFFICIAL" in authority_level else 0.7,
                    relevance_score=relevance_score,
                    priority="HIGH" if relevance_score >= 80 else ("MEDIUM" if relevance_score >= 60 else "INFO"),
                    meta={
                        "cluster_id": new_cluster.id,
                        "source_id": source_id,
                        "change_type": change_type,
                        "fingerprint": fp,
                        "quality_decision": quality_dec,
                        "security_relevance": sec_relevance,
                        "freshness": freshness,
                    },
                )
                self.db.add(timeline_event)

                clusters.append(new_cluster)

        self.db.commit()
        return clusters
