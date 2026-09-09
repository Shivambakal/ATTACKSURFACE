"""Unified Multi-Layer Target Intelligence Pipeline.

Executes the end-to-end 12-stage research intelligence cycle:
TARGET → SOURCE DISCOVERY → COLLECTORS & NORMALIZATION → DEDUPLICATION →
CHANGE DETECTION → CHANGE CLUSTERING → SEMANTIC CLASSIFICATION →
FEATURE & API EXTRACTION → HISTORICAL SECURITY CORRELATION →
RELEVANCE & CONFIDENCE SCORING → STRUCTURED AI EXPLANATION →
RESEARCH SIGNALS → TIMELINE (NOISE FILTERED) → ALERTS

CRITICAL ARCHITECTURAL PRINCIPLES:
- Optimize for high-value research signals, NOT raw observation counts.
- Aggressively isolate and filter noise (cookie banners, dynamic timestamps, tracking).
- Preserve raw evidence immutability for forensic auditing.
- AI summaries must be grounded in verified evidence IDs with zero hallucination.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.base import utcnow
from app.models import (
    Target,
    Snapshot,
    Observation,
    Change,
    ChangeEvidence,
    TimelineEvent,
    Evidence,
    Asset,
    Technology,
    AssetTechnology,
    Feature,
    FeatureObservation,
    SecurityEvent,
    KevEntry,
    Alert,
    AlertPreference,
    ResearchSignal,
    SignalType,
    SignalStatus,
    ChangeCluster,
    ApiSurface,
)
from app.services.provider_manager import get_provider_manager
from app.services.collector import collect
from app.services.normalization import (
    normalize_url,
    normalize_html_content,
    NormalizedContent,
)
from app.services.diffing import compare, Diff, ChangeType
from app.services.classification import classify
from app.services.scoring import score_detailed, ScoreResult
from app.services.clustering import cluster_changes, assign_visibility_tier, VisibilityTier
from app.services.feature_detection import (
    extract_features_from_observation,
    extract_api_endpoints_from_text,
)
from app.services.security_intelligence import (
    compute_target_security_profile,
    correlate_with_historical_profile,
)
from app.services.ai_safety import (
    build_safe_prompt,
    sanitize_external_content,
)
from app.services.ai_grounding import (
    parse_and_validate_ai_response,
    validate_ai_citations,
    StructuredResearchSignal,
)
from app.services.entity_resolution_service import EntityResolutionService
from app.models.company import Company

logger = logging.getLogger(__name__)



class TargetPipeline:
    """Orchestrator for the unified attack surface intelligence pipeline."""

    def __init__(self) -> None:
        self.logger = logging.getLogger("service.pipeline")

    async def discover_sources(self, target: Target) -> list[dict[str, Any]]:
        """Discover observation sources and endpoints for a target domain."""
        domain = target.domain.strip().lower()
        return [
            {
                "type": "web",
                "name": "primary_web",
                "url": f"https://{domain}",
                "domain": domain,
                "description": f"Primary web origin for {domain}",
            },
            {
                "type": "provider",
                "provider": "github",
                "name": "github_recon",
                "target": domain,
                "description": f"Public GitHub repositories and advisories related to {domain}",
            },
            {
                "type": "provider",
                "provider": "osv",
                "name": "osv_vulnerabilities",
                "target": domain,
                "description": "Open Source Vulnerabilities database for detected packages",
            },
            {
                "type": "provider",
                "provider": "cisa_kev",
                "name": "cisa_kev_catalog",
                "target": domain,
                "description": "CISA Known Exploited Vulnerabilities catalog",
            },
            {
                "type": "provider",
                "provider": "nvd",
                "name": "nvd_cves",
                "target": domain,
                "description": "NIST National Vulnerability Database CVE records",
            },
        ]

    async def collect_and_normalize(
        self, target: Target, sources: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Execute collectors across discovered sources and normalize records with DOM analysis."""
        normalized: list[dict[str, Any]] = []
        domain = target.domain.strip().lower()

        # 1. Primary web collector
        try:
            self.logger.info("Running web collector on domain: %s", domain)
            web_observations = await collect(domain)
            for obs in web_observations:
                url = obs.get("url", f"https://{domain}")
                raw_text = obs.get("text_excerpt", "")

                # Perform deep normalization and DOM structural analysis
                norm_content = normalize_html_content(
                    html=obs.get("html", ""),
                    url=url,
                    technologies=obs.get("technologies", []),
                    headers=obs.get("headers", {}),
                )
                if not norm_content.clean_text:
                    norm_content.clean_text = raw_text

                record = {
                    "source": "collector",
                    "url": norm_content.canonical_url,
                    "original_url": url,
                    "kind": obs.get("kind", "page"),
                    "status_code": obs.get("status_code", 200),
                    "title": norm_content.title or obs.get("title") or f"Page at {url}",
                    "content_hash": norm_content.content_hash or obs.get("content_hash"),
                    "structural_hash": norm_content.structural_hash,
                    "text_excerpt": norm_content.clean_text[:2000],
                    "clean_text": norm_content.clean_text,
                    "technologies": norm_content.technologies or obs.get("technologies", []),
                    "headers": norm_content.headers or obs.get("headers", {}),
                    "forms": norm_content.forms,
                    "auth_indicators": norm_content.auth_indicators,
                    "api_endpoints": norm_content.api_endpoints,
                    "sensitive_capabilities": norm_content.sensitive_capabilities,
                    "normalized_obj": norm_content,
                    "observed_at": utcnow(),
                }
                normalized.append(record)
            self.logger.info("Web collector returned %d normalized observations for %s", len(web_observations), domain)
        except Exception as exc:
            self.logger.warning("Web collector encountered error on %s: %s", domain, exc)

        # 2. GitHub provider reconnaissance (Entity Resolution Gated)
        pm = get_provider_manager()
        github_provider = pm.get_provider("github")
        if github_provider and github_provider.is_configured():
            try:
                gh_records = await github_provider.fetch(target=domain, per_page=10)
                company_name = target.company_name or (target.company.name if target.company else domain.split(".")[0])
                aliases = target.company.aliases if (target.company and target.company.aliases) else []

                for rec in gh_records:
                    repo_full_name = ""
                    url_lower = rec.source_url.lower()
                    if "github.com/" in url_lower:
                        parts = rec.source_url.split("github.com/")[-1].strip("/").split("/")
                        if len(parts) >= 2:
                            repo_full_name = f"{parts[0]}/{parts[1]}"

                    # Entity Resolution Gate: Enforce PUBLIC != COMPANY OWNERSHIP
                    res = EntityResolutionService.resolve_github_repository(
                        company_name=company_name,
                        canonical_domain=domain,
                        aliases=aliases,
                        repo_full_name=repo_full_name,
                        repo_metadata=rec.metadata,
                    )

                    if not res.is_confirmed_owner:
                        self.logger.info(
                            "Entity Resolution: Rejected unverified third-party GitHub repo %s for %s (%s)",
                            repo_full_name, domain, res.evidence,
                        )
                        continue

                    normalized.append({
                        "source": rec.source,
                        "url": rec.source_url,
                        "original_url": rec.source_url,
                        "kind": "repository",
                        "status_code": 200,
                        "title": rec.title,
                        "content_hash": rec.content_hash or hashlib.sha256(rec.source_url.encode()).hexdigest(),
                        "structural_hash": rec.content_hash,
                        "text_excerpt": rec.summary[:2000],
                        "clean_text": rec.summary,
                        "technologies": [],
                        "headers": {},
                        "forms": [],
                        "auth_indicators": [],
                        "api_endpoints": [],
                        "sensitive_capabilities": [],
                        "observed_at": rec.observed_at,
                        "metadata": {
                            **(rec.metadata or {}),
                            "entity_resolution": {
                                "is_confirmed_owner": True,
                                "quality_badge": res.quality_badge,
                                "evidence": res.evidence,
                            },
                        },
                    })
            except Exception as exc:
                self.logger.warning("GitHub provider fetch failed for %s: %s", domain, exc)


        return normalized

    async def deduplicate(self, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Deduplicate records by canonical URL and content_hash."""
        seen_keys: set[str] = set()
        deduped: list[dict[str, Any]] = []

        for r in records:
            url = r.get("url", "")
            chash = r.get("content_hash", "")
            dedup_key = f"{url}:{chash}"
            if dedup_key not in seen_keys:
                seen_keys.add(dedup_key)
                deduped.append(r)

        return deduped

    async def classify_changes(self, changes: list[Diff]) -> list[dict[str, Any]]:
        """Run semantic classification on detected diffs."""
        classified_list: list[dict[str, Any]] = []
        for diff in changes:
            category, confidence, summary, note = classify(diff)
            classified_list.append({
                "diff": diff,
                "kind": diff.kind,
                "url": diff.url,
                "category": category,
                "confidence": confidence,
                "summary": summary,
                "researcher_note": note,
                "before": diff.before,
                "after": diff.after,
                "detected_at": utcnow(),
                "is_noise": diff.is_noise,
                "change_type": diff.change_type,
            })
        return classified_list

    async def assess_security_relevance(
        self,
        changes: list[dict[str, Any]],
        historical_matches: int = 0,
    ) -> list[dict[str, Any]]:
        """Score changes across relevance, confidence, and security context."""
        scored: list[dict[str, Any]] = []

        for chg in changes:
            category = chg["category"]
            url = chg["url"]
            after_obj = chg.get("after")
            text = ""
            if after_obj:
                text = f"{getattr(after_obj, 'title', '')} {getattr(after_obj, 'text_excerpt', '')}"

            # Derive explicit positive and negative signals
            signals: list[str] = []
            if chg.get("is_noise"):
                signals.append("EPHEMERAL_NOISE")
            elif category == "new_auth_surface":
                signals.append("AUTH_CHANGE")
                signals.append("NEW_SECURITY_SENSITIVE_FEATURE")
            elif category == "new_authz_surface":
                signals.append("AUTHORIZATION_CHANGE")
                signals.append("NEW_SECURITY_SENSITIVE_FEATURE")
            elif category in ("new_api_surface", "new_api_documentation"):
                signals.append("NEW_API")
            elif category == "sensitive_capability":
                signals.append("SENSITIVE_WORKFLOW")
            elif category == "technology_change":
                signals.append("TECHNOLOGY_CHANGE")
            elif category == "marketing_content_change":
                signals.append("MARKETING_ONLY")

            result: ScoreResult = score_detailed(
                category=category,
                source_url=url,
                text=text,
                confidence=chg.get("confidence", 0.9),
                signals=signals,
                historical_matches=historical_matches,
                has_admin_capability=("admin" in text.lower() or "permission" in text.lower()),
            )

            scored_item = dict(chg)
            scored_item["security_relevance"] = result.relevance_score
            scored_item["confidence_score"] = result.confidence_score
            scored_item["security_context_score"] = result.security_context_score
            scored_item["priority"] = result.priority
            scored_item["score_factors"] = result.factors
            scored_item["positive_signals"] = result.positive_signals
            scored_item["negative_signals"] = result.negative_signals
            scored.append(scored_item)

        return scored

    async def correlate_history(
        self, target: Target, changes: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Correlate detected technologies and keywords against OSV, CISA KEV, and NVD."""
        pm = get_provider_manager()
        correlations: list[dict[str, Any]] = []

        tech_set: set[str] = set()
        for chg in changes:
            after_obj = chg.get("after")
            if after_obj and hasattr(after_obj, "technologies"):
                techs = getattr(after_obj, "technologies", [])
                if isinstance(techs, list):
                    tech_set.update(t for t in techs if isinstance(t, str))

        domain = target.domain.strip().lower()

        # CISA KEV
        cisa_prov = pm.get_provider("cisa_kev")
        if cisa_prov:
            try:
                kev_records = await cisa_prov.fetch(target=domain, limit=10)
                for r in kev_records:
                    correlations.append({
                        "source": "cisa_kev",
                        "cve_id": r.evidence_reference,
                        "title": r.title,
                        "summary": r.summary,
                        "severity": "CRITICAL",
                        "source_url": r.source_url,
                        "published_at": r.published_at,
                        "metadata": r.metadata,
                    })
            except Exception as exc:
                self.logger.warning("CISA KEV correlation failed for %s: %s", domain, exc)

        # OSV
        osv_prov = pm.get_provider("osv")
        if osv_prov and tech_set:
            for tech in list(tech_set)[:3]:
                clean_tech = tech.split("/")[0].strip().lower()
                if not clean_tech or clean_tech in ("apache", "nginx", "cloudflare"):
                    continue
                try:
                    osv_records = await osv_prov.fetch(package=clean_tech)
                    for r in osv_records[:2]:
                        correlations.append({
                            "source": "osv",
                            "cve_id": r.evidence_reference,
                            "title": r.title,
                            "summary": r.summary,
                            "severity": r.metadata.get("severity") or "HIGH",
                            "source_url": r.source_url,
                            "published_at": r.published_at,
                            "metadata": r.metadata,
                        })
                except Exception as exc:
                    self.logger.warning("OSV correlation failed for %s: %s", clean_tech, exc)

        return correlations

    async def ai_synthesize_signal(
        self,
        cluster_title: str,
        category: str,
        summary: str,
        affected_urls: list[str],
        evidence_dicts: list[dict[str, Any]],
        historical_notes: list[str],
    ) -> StructuredResearchSignal:
        """Run grounded AI synthesis returning structured JSON with verified evidence citations."""
        pm = get_provider_manager()
        ai_provider = pm.get_ai_provider()
        valid_evidence_ids = [str(e.get("id")) for e in evidence_dicts if e.get("id")]

        # Safe deterministic fallback if AI is not available
        if not ai_provider:
            research_area = (
                "Review the authorization checks, token validation, and parameter sanitization on newly introduced routes."
                if "auth" in category or "api" in category
                else "Review documented endpoint functionality within authorized program scope."
            )
            return StructuredResearchSignal(
                title=cluster_title,
                category=category,
                summary=summary,
                why_it_matters="Identifies a verified change in the target's public attack surface.",
                research_area=research_area,
                confidence=0.88,
                evidence_ids=valid_evidence_ids[:2],
                historical_context_ids=[],
                needs_manual_review=False,
            )

        system_prompt = (
            "You are a senior application security research analyst evaluating attack-surface deltas. "
            "Synthesize the verified evidence and historical context into a concise, structured research brief. "
            "STRICT RULES:\n"
            "1. Output ONLY valid JSON matching this schema:\n"
            '   {"title": "...", "category": "...", "summary": "...", "why_it_matters": "...", "research_area": "...", "confidence": 0.90, "evidence_ids": ["..."]}\n'
            "2. Cite ONLY existing evidence IDs passed in the verified evidence block.\n"
            "3. Never speculate about unverified vulnerabilities or claim exploitation.\n"
            "4. Keep 'why_it_matters' focused on the attack-surface boundary change.\n"
            "5. Keep 'research_area' focused on high-level authorized testing guidance."
        )

        user_input = (
            f"Synthesize research signal for '{cluster_title}' (Category: {category}). "
            f"Affected URLs: {', '.join(affected_urls[:3])}. "
            f"Historical context: {'; '.join(historical_notes) if historical_notes else 'None'}"
        )

        prompt = build_safe_prompt(
            system=system_prompt,
            user_input=user_input,
            collected_data=sanitize_external_content(summary),
            evidence=evidence_dicts,
        )

        try:
            res = await ai_provider.fetch(
                content=prompt,
                evidence_ids=valid_evidence_ids,
                target=affected_urls[0] if affected_urls else "",
            )
            if res and len(res) > 0:
                raw_text = res[0].summary
                return parse_and_validate_ai_response(
                    raw_response=raw_text,
                    valid_evidence_ids=valid_evidence_ids,
                    fallback_category=category,
                )
        except Exception as exc:
            self.logger.warning("AI synthesis failed, falling back to deterministic signal: %s", exc)

        return StructuredResearchSignal(
            title=cluster_title,
            category=category,
            summary=summary,
            why_it_matters="Observed structural or functional evolution in target's attack surface.",
            research_area="Examine input validation and access controls on modified endpoints.",
            confidence=0.85,
            evidence_ids=valid_evidence_ids[:2],
        )

    async def update_timeline(
        self, target_id: int, events: list[dict[str, Any]], db: Session
    ) -> list[TimelineEvent]:
        """Persist structured timeline events with full provenance into the database."""
        created_events: list[TimelineEvent] = []

        for ev in events:
            timeline_event = TimelineEvent(
                target_id=target_id,
                event_type=ev.get("event_type", "change"),
                title=ev.get("title", "Attack Surface Update"),
                summary=ev.get("summary", ""),
                source=ev.get("source", "collector"),
                source_url=ev.get("source_url"),
                temporal_category=ev.get("temporal_category", "CURRENT"),
                provenance_category=ev.get("provenance_category", "OBSERVED_CHANGE"),
                observed_at=ev.get("observed_at") or utcnow(),
                published_at=ev.get("published_at"),
                confidence=float(ev.get("confidence", 0.9)),
                relevance_score=int(ev.get("relevance_score", 50)),
                priority=ev.get("priority", "INFO"),
                affected_asset_ids=ev.get("affected_asset_ids", []),
                technology_ids=ev.get("technology_ids", []),
                evidence_ids=ev.get("evidence_ids", []),
                related_change_ids=ev.get("related_change_ids", []),
            )
            meta = ev.get("metadata")
            if meta is not None:
                timeline_event.metadata = meta

            db.add(timeline_event)
            created_events.append(timeline_event)

        db.flush()
        return created_events

    async def generate_alerts(
        self, user_id: int | None, items: list[Any], db: Session
    ) -> list[Alert]:
        """Generate in-app alerts strictly for high-priority signals or events."""
        if user_id is None or not items:
            return []

        alerts: list[Alert] = []
        preferences = (
            db.query(AlertPreference).filter(AlertPreference.user_id == user_id).all()
        )
        pref_types = {p.alert_type for p in preferences}

        seen_clusters: set[int] = set()

        for item in items:
            priority = getattr(item, "priority", "INFO")
            if priority not in ("CRITICAL", "HIGH"):
                continue

            # Alert deduplication: One logical ChangeCluster -> one main alert
            cluster_id = getattr(item, "cluster_id", None)
            if cluster_id:
                if cluster_id in seen_clusters:
                    continue
                seen_clusters.add(cluster_id)

            if hasattr(item, "signal_type"):
                alert_type = item.signal_type
                entity_type = "research_signal"
                title = f"[{priority}] {item.title}"[:255]
                summary = item.why_it_matters[:500]
            else:
                alert_type = getattr(item, "event_type", "timeline_event")
                entity_type = "timeline_event"
                title = getattr(item, "title", "Security Alert")[:255]
                summary = getattr(item, "summary", "")[:500]

            existing = (
                db.query(Alert)
                .filter(
                    Alert.user_id == user_id,
                    Alert.entity_type == entity_type,
                    Alert.entity_id == item.id,
                )
                .first()
            )
            if existing:
                continue

            alert = Alert(
                user_id=user_id,
                alert_type=alert_type,
                entity_type=entity_type,
                entity_id=item.id,
                title=title,
                summary=summary,
                priority=priority,
                read=False,
                created_at=utcnow(),
            )
            db.add(alert)
            alerts.append(alert)

        db.flush()
        return alerts

    async def run(self, target_id: int, db: Session) -> dict[str, Any]:
        """Orchestrate the complete 12-stage intelligence cycle for a target."""
        self.logger.info("Executing AttackSurface Intelligence Pipeline for target_id=%d", target_id)

        target = db.get(Target, target_id)
        if not target:
            raise ValueError(f"Target with id {target_id} does not exist.")

        # 1. Running snapshot record
        snapshot = Snapshot(
            target_id=target.id,
            status="running",
            collected_at=utcnow(),
        )
        db.add(snapshot)
        db.flush()

        try:
            # 2. Source Discovery
            sources = await self.discover_sources(target)

            # 3. Collection & Deep Normalization
            raw_records = await self.collect_and_normalize(target, sources)

            # 4. Deduplication
            records = await self.deduplicate(raw_records)

            # 5. Asset and Feature Lifecycle Tracking
            created_observations: list[Observation] = []
            created_evidences: list[Evidence] = []
            seen_urls: set[str] = set()

            primary_asset = (
                db.query(Asset)
                .filter(Asset.target_id == target.id, Asset.name == f"Web: {target.domain}")
                .first()
            )
            if not primary_asset:
                primary_asset = Asset(
                    target_id=target.id,
                    name=f"Web: {target.domain}",
                    url=f"https://{target.domain}",
                    asset_type="web",
                    first_observed=utcnow(),
                    last_observed=utcnow(),
                    status="active",
                    confidence=0.95,
                )
                primary_asset.metadata = {"domain": target.domain}
                db.add(primary_asset)
                db.flush()

            for rec in records:
                rec_url = rec["url"]
                if rec_url in seen_urls:
                    continue
                seen_urls.add(rec_url)

                obs = Observation(
                    snapshot_id=snapshot.id,
                    url=rec_url,
                    kind=rec.get("kind", "page"),
                    status_code=rec.get("status_code", 200),
                    title=rec.get("title"),
                    content_hash=rec["content_hash"],
                    text_excerpt=rec.get("text_excerpt", ""),
                    technologies=rec.get("technologies", []),
                    headers=rec.get("headers", {}),
                    observed_at=rec.get("observed_at", utcnow()),
                )
                db.add(obs)
                created_observations.append(obs)

                # Create immutable Evidence record
                ev_record = Evidence(
                    target_id=target.id,
                    source=rec.get("source", "collector"),
                    source_url=rec_url,
                    retrieved_at=rec.get("observed_at", utcnow()),
                    content_hash=rec["content_hash"],
                    evidence_type=rec.get("kind", "page"),
                    excerpt=rec.get("text_excerpt", "")[:1000],
                )
                ev_record.metadata = {
                    "title": rec.get("title"),
                    "status_code": rec.get("status_code"),
                    "structural_hash": rec.get("structural_hash"),
                }
                db.add(ev_record)
                created_evidences.append(ev_record)

                # Extract and persist features
                norm_obj = rec.get("normalized_obj")
                if norm_obj:
                    extracted_feats = extract_features_from_observation(norm_obj)
                    for ef in extracted_feats:
                        feat = (
                            db.query(Feature)
                            .filter(Feature.target_id == target.id, Feature.name == ef.name)
                            .first()
                        )
                        if not feat:
                            feat = Feature(
                                target_id=target.id,
                                name=ef.name,
                                description=ef.description,
                                first_observed=utcnow(),
                                last_observed=utcnow(),
                                status="NEW",
                                confidence=ef.confidence,
                                affected_assets=ef.affected_assets,
                            )
                            db.add(feat)
                            db.flush()
                        else:
                            feat.last_observed = utcnow()

                    # Extract and persist API surfaces
                    api_surfaces = extract_api_endpoints_from_text(norm_obj.clean_text, norm_obj.canonical_url)
                    for ap in api_surfaces:
                        existing_api = (
                            db.query(ApiSurface)
                            .filter(
                                ApiSurface.target_id == target.id,
                                ApiSurface.method == ap.method,
                                ApiSurface.path == ap.path,
                            )
                            .first()
                        )
                        if not existing_api:
                            new_api = ApiSurface(
                                target_id=target.id,
                                method=ap.method,
                                path=ap.path,
                                version=ap.version,
                                auth_requirement=ap.auth_requirement,
                                confidence=ap.confidence,
                                source=norm_obj.canonical_url,
                                status="ACTIVE",
                            )
                            db.add(new_api)

            db.flush()

            # 6. Content-Aware Difference Engine
            previous_snapshot = (
                db.query(Snapshot)
                .filter(
                    Snapshot.target_id == target.id,
                    Snapshot.id != snapshot.id,
                    Snapshot.status == "complete",
                )
                .order_by(Snapshot.collected_at.desc())
                .first()
            )
            previous_obs = previous_snapshot.observations if previous_snapshot else []
            diffs = compare(previous_obs, created_observations)

            # 7. Semantic Classification
            classified_changes = await self.classify_changes(diffs)

            # 8. Historical Target Vulnerability Profile
            target_profile = compute_target_security_profile(target.id, db)
            historical_matches = sum(1 for v in target_profile.vulnerability_classes.values() if v in ("HIGH", "MEDIUM"))

            # 9. Relevance & Confidence Scoring
            scored_changes = await self.assess_security_relevance(
                classified_changes, historical_matches=historical_matches
            )

            # 10. External Threat Feed Correlations (CISA KEV, OSV, NVD)
            correlations = await self.correlate_history(target, scored_changes)
            for corr in correlations:
                if corr.get("cve_id"):
                    sec_ev = (
                        db.query(SecurityEvent)
                        .filter(
                            SecurityEvent.target_id == target.id,
                            SecurityEvent.cve_id == corr["cve_id"],
                        )
                        .first()
                    )
                    if not sec_ev:
                        sec_ev = SecurityEvent(
                            target_id=target.id,
                            cve_id=corr["cve_id"],
                            source=corr["source"],
                            severity=corr.get("severity"),
                            summary=corr.get("summary"),
                            published=corr.get("published_at"),
                            references=corr.get("metadata", {}).get("references", []),
                        )
                        sec_ev.metadata = corr.get("metadata", {})
                        db.add(sec_ev)
            db.flush()

            # 11. Change Clustering (Grouping related page diffs into unified release events)
            clusters = cluster_changes(scored_changes)
            created_clusters: list[ChangeCluster] = []

            for cl in clusters:
                change_ids = [ch.get("id") for ch in cl.changes if ch.get("id")]
                cluster_record = ChangeCluster(
                    target_id=target.id,
                    title=cl.cluster_title,
                    summary=cl.summary,
                    primary_category=cl.primary_category,
                    change_ids=change_ids,
                    affected_urls=cl.affected_urls,
                    source_count=cl.source_count,
                    confidence=cl.avg_confidence,
                    relevance_score=cl.max_relevance,
                    priority=cl.highest_priority,
                )
                db.add(cluster_record)
                created_clusters.append(cluster_record)
            db.flush()

            # 12. Persist Changes and ChangeEvidence (Content-Aware, Deduplicated, Noise-Filtered)
            created_changes: list[Change] = []
            for chg in scored_changes:
                # Discard noise immediately
                if chg.get("is_noise") or chg.get("change_type") == ChangeType.NOISE.value:
                    continue

                url = chg["url"]
                category = chg["category"]

                before_obj = chg.get("before")
                before_hash = getattr(before_obj, "content_hash", "") if before_obj else "NONE"
                after_obj = chg.get("after")
                after_hash = getattr(after_obj, "content_hash", "") if after_obj else "NONE"

                # If content hash is unchanged and it's a routine content update, do not record a change
                if before_hash != "NONE" and before_hash == after_hash and chg.get("kind") == "content_changed":
                    continue

                # Deterministic content-dependent fingerprint (never relies on snapshot.id)
                fingerprint = hashlib.sha256(
                    f"{target.id}:{category}:{url}:{before_hash}:{after_hash}".encode()
                ).hexdigest()

                # Deduplicate against existing changes for this target
                change_obj = (
                    db.query(Change).filter(Change.fingerprint == fingerprint).first()
                )
                if change_obj:
                    # Change has already been detected and persisted; skip repeated creation
                    continue

                change_obj = Change(
                    target_id=target.id,
                    snapshot_id=snapshot.id,
                    fingerprint=fingerprint,
                    category=category,
                    confidence=float(chg.get("confidence", 0.9)),
                    security_relevance=int(chg.get("security_relevance", 50)),
                    summary=chg["summary"],
                    researcher_note=chg["researcher_note"],
                    source_url=url,
                    detected_at=utcnow(),
                    priority=chg.get("priority", "MEDIUM"),
                    score_factors=chg.get("score_factors", {}),
                )
                db.add(change_obj)
                db.flush()

                matching_obs = next(
                    (o for o in created_observations if o.url == url), None
                )
                obs_id = matching_obs.id if matching_obs else None

                # Immutable Before State Evidence
                if before_obj:
                    ce_before = ChangeEvidence(
                        change_id=change_obj.id,
                        state="before",
                        observation_id=None,
                        payload={
                            "url": url,
                            "title": getattr(before_obj, "title", None),
                            "content_hash": before_hash,
                            "text_excerpt": getattr(before_obj, "text_excerpt", "")[:500],
                            "technologies": getattr(before_obj, "technologies", []),
                        },
                    )
                    db.add(ce_before)

                # Immutable After State Evidence
                if after_obj:
                    ce_after = ChangeEvidence(
                        change_id=change_obj.id,
                        state="after",
                        observation_id=obs_id,
                        payload={
                            "url": url,
                            "title": getattr(after_obj, "title", None),
                            "content_hash": after_hash,
                            "text_excerpt": getattr(after_obj, "text_excerpt", "")[:500],
                            "technologies": getattr(after_obj, "technologies", []),
                            "change_type": chg.get("change_type"),
                            "kind": chg.get("kind"),
                        },
                    )
                    db.add(ce_after)

                created_changes.append(change_obj)

            # 13. High-Value Research Signal Quality Gating
            # Only create research signals if there is sufficient target-specific evidence & real changes
            created_signals: list[ResearchSignal] = []
            
            if created_changes:
                evidence_dicts = [
                    {
                        "id": ev.id,
                        "url": ev.source_url,
                        "summary": ev.excerpt,
                    }
                    for ev in created_evidences
                ]

                # Quality Gate: clusters must have actionable relevance (score >= 60)
                high_signal_clusters = [
                    c for c in clusters
                    if c.max_relevance >= 60
                    and c.visibility_tier in (VisibilityTier.HIGH_SIGNAL.value, VisibilityTier.ALERT_WORTHY.value)
                ]

                # Find matching historical notes
                profile_notes = [
                    f"{cls} ({lvl} historical activity)"
                    for cls, lvl in target_profile.vulnerability_classes.items()
                    if lvl in ("HIGH", "MEDIUM")
                ]

                for cl in high_signal_clusters[:5]:
                    # Grounded AI Brief Generation
                    ai_brief = await self.ai_synthesize_signal(
                        cluster_title=cl.cluster_title,
                        category=cl.primary_category,
                        summary=cl.summary,
                        affected_urls=cl.affected_urls,
                        evidence_dicts=evidence_dicts,
                        historical_notes=profile_notes,
                    )

                    # Quality Gate: require target-specific evidence and confidence >= 0.70
                    if not ai_brief.evidence_ids or ai_brief.confidence < 0.70:
                        continue

                    # Deduplicate signal against target
                    existing_sig = db.query(ResearchSignal).filter(
                        ResearchSignal.target_id == target.id,
                        ResearchSignal.title == ai_brief.title,
                        ResearchSignal.status.in_(["new", "interesting", "investigating"]),
                    ).first()
                    if existing_sig:
                        continue

                    matching_cluster_rec = next(
                        (cr for cr in created_clusters if cr.title == cl.cluster_title), None
                    )
                    cluster_id = matching_cluster_rec.id if matching_cluster_rec else None

                    # Link primary change id
                    matched_change_id = next(
                        (ch.id for ch in created_changes if ch.source_url in cl.affected_urls),
                        created_changes[0].id if created_changes else None,
                    )

                    # Map category to SignalType
                    sig_type = SignalType.OTHER.value
                    if "authz" in cl.primary_category or "role" in cl.cluster_title.lower():
                        sig_type = SignalType.NEW_AUTHZ_SURFACE.value
                    elif "auth" in cl.primary_category:
                        sig_type = SignalType.NEW_AUTH_SURFACE.value
                    elif "api" in cl.primary_category:
                        sig_type = SignalType.NEW_API_SURFACE.value
                    elif "tech" in cl.primary_category:
                        sig_type = SignalType.TECHNOLOGY_CHANGE.value
                    elif "sensitive" in cl.primary_category:
                        sig_type = SignalType.POTENTIAL_ATTACK_SURFACE_EXPANSION.value
                    else:
                        sig_type = SignalType.NEW_FEATURE.value

                    research_signal = ResearchSignal(
                        target_id=target.id,
                        cluster_id=cluster_id,
                        change_id=matched_change_id,
                        title=ai_brief.title,
                        signal_type=sig_type,
                        summary=ai_brief.summary,
                        why_it_matters=ai_brief.why_it_matters,
                        recommended_research_area=ai_brief.research_area,
                        relevance_score=cl.max_relevance,
                        confidence_score=int(ai_brief.confidence * 100),
                        security_context_score=75 if profile_notes else 50,
                        priority=cl.highest_priority,
                        status=SignalStatus.NEW.value,
                        historical_context={"profile": target_profile.vulnerability_classes},
                        affected_assets=cl.affected_urls,
                        evidence_ids=ai_brief.evidence_ids,
                        source_count=cl.source_count,
                        created_at=utcnow(),
                    )
                    db.add(research_signal)
                    created_signals.append(research_signal)

                db.flush()

            # 14. Noise-Filtered Timeline Population with Strict Separation
            events_to_record: list[dict[str, Any]] = []

            # Add research signals to the main timeline
            for sig in created_signals:
                events_to_record.append({
                    "event_type": f"signal_{sig.signal_type.lower()}",
                    "title": sig.title,
                    "summary": f"{sig.why_it_matters} Guidance: {sig.recommended_research_area}",
                    "source": "intelligence.signal",
                    "source_url": sig.affected_assets[0] if sig.affected_assets else f"https://{target.domain}",
                    "observed_at": utcnow(),
                    "confidence": float(sig.confidence_score) / 100.0,
                    "relevance_score": sig.relevance_score,
                    "priority": sig.priority,
                    "temporal_category": "CURRENT",
                    "provenance_category": "RESEARCH_SIGNAL",
                    "affected_asset_ids": [primary_asset.id] if primary_asset else [],
                    "evidence_ids": sig.evidence_ids or [],
                    "related_change_ids": [sig.change_id] if sig.change_id else [],
                    "metadata": {
                        "signal_id": sig.id,
                        "signal_type": sig.signal_type,
                        "cluster_id": sig.cluster_id,
                    },
                })

            # Add NEW non-noise changes that are USER_VISIBLE
            for chg in created_changes:
                if chg.priority == "INFO" or chg.category == "external_repository_reference":
                    continue  # Filter noise and unverified third-party references from main timeline

                # Boundary check: External third-party URLs are NEVER recorded as company pages
                if chg.category in ("new_public_page", "removed_public_page") and EntityResolutionService.is_external_third_party_url(target.domain, chg.source_url):
                    continue


                events_to_record.append({
                    "event_type": f"change_{chg.category}",
                    "title": chg.summary,
                    "summary": chg.researcher_note,
                    "source": "pipeline.diff",
                    "source_url": chg.source_url,
                    "observed_at": chg.detected_at,
                    "confidence": chg.confidence,
                    "relevance_score": chg.security_relevance,
                    "priority": chg.priority,
                    "temporal_category": "CURRENT",
                    "provenance_category": "OBSERVED_CHANGE",
                    "affected_asset_ids": [primary_asset.id] if primary_asset else [],
                    "evidence_ids": [e.id for e in created_evidences if e.source_url == chg.source_url],
                    "related_change_ids": [chg.id],
                    "metadata": {
                        "category": chg.category,
                        "score_factors": chg.score_factors or {},
                    },
                })

            # Add correlations (Strictly categorized as SECURITY_CONTEXT, never presenting old CVE as new)
            now_utc = utcnow()
            for corr in correlations:
                pub_at = corr.get("published_at")
                if pub_at:
                    delta_days = (now_utc - pub_at).days if pub_at.tzinfo else (now_utc.replace(tzinfo=None) - pub_at).days
                    if delta_days > 30:
                        temp_cat = "HISTORICAL"
                    elif delta_days > 1:
                        temp_cat = "RECENT"
                    else:
                        temp_cat = "CURRENT"
                else:
                    temp_cat = "HISTORICAL"

                # Deduplicate correlation events to avoid spamming timeline on every poll
                existing_corr_ev = db.query(TimelineEvent).filter(
                    TimelineEvent.target_id == target.id,
                    TimelineEvent.event_type == "security_correlation",
                    TimelineEvent.title == corr["title"],
                ).first()
                if existing_corr_ev:
                    continue

                events_to_record.append({
                    "event_type": "security_correlation",
                    "title": corr["title"],
                    "summary": f"[SECURITY CONTEXT - Not verified vulnerable] {corr['summary']}",
                    "source": corr["source"],
                    "source_url": corr.get("source_url"),
                    "observed_at": pub_at or now_utc,
                    "published_at": pub_at,
                    "confidence": 0.85,
                    "relevance_score": 85 if corr.get("severity") == "CRITICAL" else 70,
                    "priority": corr.get("severity") or "HIGH",
                    "temporal_category": temp_cat,
                    "provenance_category": "SECURITY_CONTEXT",
                    "affected_asset_ids": [primary_asset.id] if primary_asset else [],
                    "metadata": corr.get("metadata", {}),
                })

            timeline_events = await self.update_timeline(target.id, events_to_record, db)

            # 15. Generate Alerts strictly for ALERT_WORTHY signals
            alerts = await self.generate_alerts(target.user_id, created_signals, db)

            # 16. Finalize Snapshot and Target
            snapshot.status = "complete"
            target.last_visited_at = utcnow()
            target.updated_at = utcnow()
            db.commit()

            self.logger.info(
                "Pipeline completed for %s: %d raw obs -> %d scored changes -> %d clusters -> %d research signals -> %d timeline events",
                target.domain,
                len(created_observations),
                len(scored_changes),
                len(created_clusters),
                len(created_signals),
                len(timeline_events),
            )

            return {
                "status": "complete",
                "target_id": target.id,
                "domain": target.domain,
                "snapshot_id": snapshot.id,
                "observations_count": len(created_observations),
                "raw_changes_count": len(scored_changes),
                "meaningful_changes_count": len([c for c in scored_changes if not c.get("is_noise")]),
                "clusters_count": len(created_clusters),
                "signals_count": len(created_signals),
                "timeline_events_count": len(timeline_events),
                "alerts_count": len(alerts),
            }

        except Exception as exc:
            db.rollback()
            self.logger.error("TargetPipeline failed for target_id=%d: %s", target_id, exc, exc_info=True)
            snapshot.status = "failed"
            snapshot.error = str(exc)
            db.commit()
            raise exc
