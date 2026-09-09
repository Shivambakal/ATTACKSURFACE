"""Change clustering and visibility tiering engine.

Clusters multiple related page-level diffs into unified release events,
corroborates multi-source evidence, and triages items into visibility tiers:
INTERNAL_RAW, USER_VISIBLE, HIGH_SIGNAL, ALERT_WORTHY.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from urllib.parse import urlparse


class VisibilityTier(str, Enum):
    INTERNAL_RAW = "INTERNAL_RAW"      # Stored for forensics/retraining, hidden from timeline
    USER_VISIBLE = "USER_VISIBLE"      # Informational changes in change logs
    HIGH_SIGNAL = "HIGH_SIGNAL"        # Promoted to main security timeline & research signals
    ALERT_WORTHY = "ALERT_WORTHY"      # High priority, high confidence notification candidate


@dataclass
class ClusteredChange:
    cluster_title: str
    primary_category: str
    changes: list[dict[str, Any]]
    affected_urls: list[str]
    source_count: int
    highest_priority: str
    max_relevance: int
    avg_confidence: float
    visibility_tier: str
    summary: str


def assign_visibility_tier(
    category: str,
    priority: str,
    relevance_score: int,
    confidence_score: int,
    is_noise: bool,
) -> VisibilityTier:
    """Determine the visibility tier for an event based on relevance, confidence, and noise state."""
    if is_noise or category == "noise" or relevance_score < 20:
        return VisibilityTier.INTERNAL_RAW

    if priority in ("CRITICAL", "HIGH") and confidence_score >= 70:
        if category in ("new_auth_surface", "new_authz_surface", "new_api_surface", "sensitive_capability", "security_sensitive_change"):
            return VisibilityTier.ALERT_WORTHY
        return VisibilityTier.HIGH_SIGNAL

    if priority == "HIGH" or (priority == "MEDIUM" and relevance_score >= 50):
        return VisibilityTier.HIGH_SIGNAL

    return VisibilityTier.USER_VISIBLE


def cluster_changes(
    changes: list[dict[str, Any]],
    external_records: list[dict[str, Any]] | None = None,
) -> list[ClusteredChange]:
    """Group individual page diffs into unified release clusters to eliminate card explosion."""
    if not changes:
        return []

    # 1. Group changes by primary category and path root
    buckets: dict[str, list[dict[str, Any]]] = {}

    for chg in changes:
        cat = chg.get("category", "public_content_change")
        url = chg.get("url", "")
        parsed = urlparse(url)
        path_segments = [p for p in parsed.path.split("/") if p]
        root_path = f"/{path_segments[0]}" if path_segments else "/"

        # High-security categories form their own high-priority clusters
        if cat in ("new_auth_surface", "new_authz_surface"):
            bucket_key = f"auth:{parsed.netloc}"
        elif cat in ("new_api_surface", "new_api_documentation"):
            bucket_key = f"api:{parsed.netloc}"
        elif cat == "technology_change":
            bucket_key = f"tech:{parsed.netloc}"
        elif cat == "noise" or chg.get("is_noise"):
            bucket_key = f"noise:{parsed.netloc}"
        else:
            bucket_key = f"{cat}:{parsed.netloc}:{root_path}"

        if bucket_key not in buckets:
            buckets[bucket_key] = []
        buckets[bucket_key].append(chg)

    clusters: list[ClusteredChange] = []

    # 2. Synthesize each bucket into a cohesive cluster
    for bucket_key, items in buckets.items():
        primary_cat = items[0].get("category", "public_content_change")
        urls = sorted(list({i.get("url", "") for i in items if i.get("url")}))

        relevances = [i.get("security_relevance", 50) for i in items]
        max_rel = max(relevances) if relevances else 50
        confidences = [i.get("confidence_score", 70) for i in items]
        avg_conf = (sum(confidences) / len(confidences)) if confidences else 70.0

        # Determine highest priority
        priorities = [i.get("priority", "INFO") for i in items]
        if "CRITICAL" in priorities:
            highest_pri = "CRITICAL"
        elif "HIGH" in priorities:
            highest_pri = "HIGH"
        elif "MEDIUM" in priorities:
            highest_pri = "MEDIUM"
        elif "LOW" in priorities:
            highest_pri = "LOW"
        else:
            highest_pri = "INFO"

        all_noise = all(i.get("diff") and getattr(i.get("diff"), "is_noise", False) for i in items)
        vis_tier = assign_visibility_tier(
            category=primary_cat,
            priority=highest_pri,
            relevance_score=max_rel,
            confidence_score=int(avg_conf),
            is_noise=all_noise,
        )

        # Build readable, researcher-friendly cluster titles
        if primary_cat == "new_auth_surface":
            title = f"Authentication Surface Evolution ({len(urls)} endpoints affected)"
            summary = f"Detected new authentication mechanisms or login workflows across {len(urls)} location(s)."
        elif primary_cat == "new_authz_surface":
            title = f"Authorization & Access Control Changes ({len(urls)} paths)"
            summary = f"Detected newly introduced role models, permissions, or invitation controls across {len(urls)} path(s)."
        elif primary_cat in ("new_api_surface", "new_api_documentation"):
            title = f"API Attack Surface Expansion ({len(urls)} endpoints)"
            summary = f"Identified newly documented or updated API routes across {len(urls)} documentation and service endpoints."
        elif primary_cat == "technology_change":
            title = f"Technology Stack Update ({len(urls)} assets)"
            summary = f"Observed infrastructure or framework changes across {len(urls)} target location(s)."
        elif len(urls) > 1:
            title = f"Coordinated Content Release ({len(urls)} pages)"
            summary = f"Observed synchronized content updates across {len(urls)} pages under {bucket_key.split(':')[-1]}."
        else:
            title = items[0].get("summary", "Attack Surface Change")
            summary = items[0].get("summary", "Observed attack surface modification.")

        clusters.append(
            ClusteredChange(
                cluster_title=title,
                primary_category=primary_cat,
                changes=items,
                affected_urls=urls,
                source_count=len(urls),
                highest_priority=highest_pri,
                max_relevance=max_rel,
                avg_confidence=avg_conf,
                visibility_tier=vis_tier.value,
                summary=summary,
            )
        )

    # Sort clusters by priority and relevance desc
    priority_order = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1, "INFO": 0}
    clusters.sort(
        key=lambda c: (priority_order.get(c.highest_priority, 0), c.max_relevance),
        reverse=True,
    )
    return clusters
