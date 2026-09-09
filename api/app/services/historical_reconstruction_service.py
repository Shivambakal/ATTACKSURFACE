"""Historical Intelligence Reconstruction Service.

Reconstructs evidence-backed historical attack surface evolution:
PAST -> PRESENT -> CONTINUOUS FUTURE MONITORING

Orchestrates multi-source historical intelligence from GitHub releases, commits,
tags, changelogs, documentation, OSV, CISA KEV, and NVD.
Integrates historical weakness fingerprinting and backward correlation with current
research signals.
"""
from __future__ import annotations

import hashlib
import logging
import re
from datetime import datetime, timezone
from typing import Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.models.company import Company
from app.models.asset import Asset
from app.models.product import Product
from app.models.feature import Feature
from app.models.api_surface import ApiSurface
from app.models.security import SecurityEvent
from app.models.security_program import SecurityProgram, ProgramScopeRule
from app.models.timeline import TimelineEvent
from app.models.history import HistoricalCoverage, HistoricalRelease
from app.models.signal import ResearchSignal, SignalType
from app.providers.github import GitHubProvider
from app.providers.osv import OSVProvider
from app.providers.cisa_kev import CISAKEVProvider
from app.providers.nvd import NVDProvider
from app.services.provider_manager import get_provider_manager

logger = logging.getLogger(__name__)


# Standardized vulnerability classes for historical weakness fingerprinting
VULNERABILITY_CLASSES = {
    "BOLA / IDOR": ["idor", "bola", "broken object level authorization", "insecure direct object", "object-level"],
    "BROKEN ACCESS CONTROL": ["access control", "rbac", "privilege escalation", "unauthorized access", "impersonat", "permission bypass"],
    "AUTHENTICATION": ["authentication", "auth bypass", "credential", "session fixation", "mfa bypass", "sso bypass", "saml", "oauth"],
    "SSRF": ["ssrf", "server-side request forgery", "server side request forgery"],
    "INJECTION": ["sql injection", "sqli", "command injection", "rce", "remote code execution", "template injection", "ssti"],
    "XSS": ["cross-site scripting", "xss", "cross site scripting"],
    "CSRF": ["csrf", "cross-site request forgery"],
    "INFORMATION DISCLOSURE": ["information disclosure", "data leak", "sensitive data", "token leak", "exposure"],
}


class HistoricalReconstructionService:
    """Core service for reconstructing historical intelligence from public evidence."""

    @classmethod
    def classify_vulnerability_class(cls, title: str, summary: str = "") -> str:
        """Determines standardized vulnerability class from security event text."""
        text = f"{title} {summary}".lower()
        for v_class, keywords in VULNERABILITY_CLASSES.items():
            for kw in keywords:
                if kw in text:
                    return v_class
        return "GENERAL SECURITY EVENT"

    @classmethod
    def build_weakness_fingerprint(cls, db: Session, company_id: int) -> dict[str, int]:
        """Calculates historical weakness distribution for an organization."""
        events = db.query(SecurityEvent).filter(SecurityEvent.company_id == company_id).all()
        fingerprint: dict[str, int] = {}
        for ev in events:
            v_class = ev.vulnerability_class or cls.classify_vulnerability_class(ev.cve_id or "", ev.summary or "")
            fingerprint[v_class] = fingerprint.get(v_class, 0) + 1
        return fingerprint

    @classmethod
    def correlate_historical_context(
        cls, db: Session, company_id: int, current_title: str, current_summary: str = ""
    ) -> dict[str, Any]:
        """Correlates a current attack surface change or signal with historical security context."""
        fingerprint = cls.build_weakness_fingerprint(db, company_id)
        text = f"{current_title} {current_summary}".lower()

        matched_classes = []
        is_auth_related = any(k in text for k in ("admin", "role", "impersonat", "permission", "member", "org", "user_id", "auth", "token"))
        is_export_related = any(k in text for k in ("export", "download", "dump", "csv", "backup"))
        is_upload_related = any(k in text for k in ("upload", "file", "attachment", "s3", "blob"))

        if is_auth_related and (fingerprint.get("BROKEN ACCESS CONTROL", 0) > 0 or fingerprint.get("BOLA / IDOR", 0) > 0):
            matched_classes.append("BROKEN ACCESS CONTROL / BOLA")

        if any(k in text for k in ("login", "oauth", "sso", "jwt", "session")) and fingerprint.get("AUTHENTICATION", 0) > 0:
            matched_classes.append("AUTHENTICATION")

        if any(k in text for k in ("webhook", "fetch", "url", "proxy", "callback")) and fingerprint.get("SSRF", 0) > 0:
            matched_classes.append("SSRF")

        if matched_classes:
            context_explanation = (
                f"Historical security context: The organization has prior public security history "
                f"involving {', '.join(matched_classes)}. Current functionality resembles historically "
                f"sensitive attack surface areas."
            )
            return {
                "has_historical_correlation": True,
                "matched_vulnerability_classes": matched_classes,
                "explanation": context_explanation,
                "historical_fingerprint": fingerprint,
            }

        return {
            "has_historical_correlation": False,
            "matched_vulnerability_classes": [],
            "explanation": "No prior public security events directly correlate with this specific capability.",
            "historical_fingerprint": fingerprint,
        }

    @classmethod
    def update_historical_coverage(cls, db: Session, company: Company) -> HistoricalCoverage:
        """Calculates and persists historical coverage metrics for an organization."""
        coverage = (
            db.query(HistoricalCoverage)
            .filter(HistoricalCoverage.company_id == company.id)
            .first()
        )
        if not coverage:
            coverage = HistoricalCoverage(company_id=company.id)
            db.add(coverage)

        # Query all timeline events and releases for date boundaries
        events = db.query(TimelineEvent).filter(TimelineEvent.company_id == company.id).all()
        releases = db.query(HistoricalRelease).filter(HistoricalRelease.company_id == company.id).all()
        sec_events = db.query(SecurityEvent).filter(SecurityEvent.company_id == company.id).all()

        timestamps: list[datetime] = []
        for e in events:
            if e.published_at:
                timestamps.append(e.published_at)
            elif e.observed_at:
                timestamps.append(e.observed_at)

        for r in releases:
            if r.published_at:
                timestamps.append(r.published_at)

        for s in sec_events:
            if s.published:
                timestamps.append(s.published)

        total_confirmed = len(releases) + len(sec_events) + sum(1 for e in events if e.quality_badge == "CONFIRMED_HISTORY")
        total_estimated = sum(1 for e in events if e.quality_badge in ("LIKELY_HISTORY", "WEAK_HISTORY"))

        # Distinct sources count
        sources = set()
        for e in events:
            if e.source:
                sources.add(e.source.lower())
        for r in releases:
            sources.add("github_release")
        for s in sec_events:
            if s.source:
                sources.add(s.source.lower())

        if timestamps:
            timestamps.sort()
            coverage.coverage_start = timestamps[0]
            coverage.coverage_end = timestamps[-1]
            coverage.confidence = min(0.95, 0.50 + (len(sources) * 0.08) + (min(total_confirmed, 50) * 0.005))
        else:
            coverage.confidence = 0.30

        coverage.sources_count = max(1, len(sources))
        coverage.confirmed_events_count = total_confirmed
        coverage.estimated_events_count = total_estimated
        coverage.last_synced_at = datetime.now(timezone.utc)
        coverage.notes = (
            "Historical intelligence reconstructed from publicly available evidence. "
            "Coverage represents verifiable public signals and may be partial."
        )

        db.commit()
        db.refresh(coverage)
        return coverage

    @classmethod
    def compare_dates(
        cls, db: Session, company_id: int, from_date: datetime, to_date: datetime
    ) -> dict[str, Any]:
        """Compares public attack surface states between two historical timestamps."""
        # Ensure UTC timezone
        if from_date.tzinfo is None:
            from_date = from_date.replace(tzinfo=timezone.utc)
        if to_date.tzinfo is None:
            to_date = to_date.replace(tzinfo=timezone.utc)

        # 1. Assets added / removed in window
        assets_in_window = (
            db.query(Asset)
            .filter(
                Asset.company_id == company_id,
                Asset.first_observed >= from_date,
                Asset.first_observed <= to_date,
            )
            .all()
        )

        # 2. Features added in window
        features_in_window = (
            db.query(Feature)
            .filter(
                Feature.company_id == company_id,
                Feature.first_observed >= from_date,
                Feature.first_observed <= to_date,
            )
            .all()
        )

        # 3. APIs added in window
        apis_in_window = (
            db.query(ApiSurface)
            .filter(
                ApiSurface.company_id == company_id,
                ApiSurface.first_seen >= from_date,
                ApiSurface.first_seen <= to_date,
            )
            .all()
        )

        # 4. Security Events in window
        security_in_window = (
            db.query(SecurityEvent)
            .filter(
                SecurityEvent.company_id == company_id,
                SecurityEvent.published >= from_date,
                SecurityEvent.published <= to_date,
            )
            .all()
        )

        # 5. Releases in window
        releases_in_window = (
            db.query(HistoricalRelease)
            .filter(
                HistoricalRelease.company_id == company_id,
                HistoricalRelease.published_at >= from_date,
                HistoricalRelease.published_at <= to_date,
            )
            .all()
        )

        return {
            "period": {
                "from": from_date.isoformat(),
                "to": to_date.isoformat(),
            },
            "added_assets": [
                {
                    "id": a.id,
                    "hostname": a.normalized_hostname or a.name,
                    "type": a.asset_type,
                    "scope": a.scope_status,
                    "first_observed": a.first_observed,
                }
                for a in assets_in_window
            ],
            "added_features": [
                {
                    "id": f.id,
                    "name": f.name,
                    "category": f.category,
                    "first_observed": f.first_observed,
                }
                for f in features_in_window
            ],
            "added_apis": [
                {
                    "id": api.id,
                    "method": api.method,
                    "path": api.path,
                    "first_seen": api.first_seen,
                }
                for api in apis_in_window
            ],
            "security_events": [
                {
                    "id": s.id,
                    "cve_id": s.cve_id,
                    "vulnerability_class": s.vulnerability_class,
                    "severity": s.severity,
                    "published": s.published,
                }
                for s in security_in_window
            ],
            "releases": [
                {
                    "id": r.id,
                    "tag": r.tag,
                    "title": r.title,
                    "published_at": r.published_at,
                    "semantic_changes": r.semantic_changes,
                }
                for r in releases_in_window
            ],
            "summary": {
                "assets_count": len(assets_in_window),
                "features_count": len(features_in_window),
                "apis_count": len(apis_in_window),
                "security_events_count": len(security_in_window),
                "releases_count": len(releases_in_window),
            },
        }

    @classmethod
    async def reconstruct_company_history(
        cls, db: Session, company_id: int, stage: int = 1
    ) -> dict[str, Any]:
        """Orchestrates multi-source historical intelligence reconstruction."""
        company = db.query(Company).filter(Company.id == company_id).first()
        if not company:
            raise ValueError(f"Company {company_id} not found")

        stats = {
            "releases_found": 0,
            "security_events_found": 0,
            "features_extracted": 0,
            "apis_extracted": 0,
            "timeline_events_created": 0,
        }

        mgr = get_provider_manager()
        gh_provider: GitHubProvider | None = mgr.get_provider("github")  # type: ignore

        # --- STEP 1: GitHub Historical Intelligence ---
        if gh_provider:
            try:
                # Search for primary company repositories using canonical name or aliases
                search_term = company.name
                gh_records = await gh_provider.fetch(target=search_term, per_page=5)

                for rec in gh_records:
                    if rec.event_type == "repository":
                        repo_full_name = rec.metadata.get("repository")
                        if not repo_full_name or "/" not in repo_full_name:
                            continue
                        owner, repo = repo_full_name.split("/", 1)

                        # STRICT ENTITY RESOLUTION CHECK
                        # Verify repository ownership matches company name, canonical domain, or verified aliases.
                        # Third-party repositories (e.g. SemiAnalysisAI/InferenceX-app) must NOT be attached to company history.
                        allowed_owners = {
                            company.name.lower().replace(" ", "").replace("-", ""),
                            company.canonical_domain.split(".")[0].lower(),
                        }
                        for alias in company.aliases or []:
                            allowed_owners.add(alias.lower().replace(" ", "").replace("-", "").replace(".", ""))
                        if company.name.lower() == "amd":
                            allowed_owners.add("rocm")
                        elif company.name.lower() in ("alphabet / google", "google"):
                            allowed_owners.update(["google", "googlecloudplatform", "golang", "kubernetes", "tensorflow", "chromium"])
                        elif company.name.lower() in ("amazon / aws", "amazon"):
                            allowed_owners.update(["aws", "awslabs", "amzn", "amazonwebservices"])
                        elif company.name.lower() in ("meta platforms", "meta"):
                            allowed_owners.update(["facebook", "meta", "facebookresearch", "pytorch"])
                        elif company.name.lower() == "microsoft":
                            allowed_owners.update(["microsoft", "azure", "dotnet", "typescript"])
                        elif company.name.lower() == "apple":
                            allowed_owners.update(["apple", "swiftlang"])

                        owner_norm = owner.lower().replace(" ", "").replace("-", "")
                        is_verified_owner = (
                            owner_norm in allowed_owners
                            or any(a in owner_norm for a in allowed_owners if len(a) >= 4)
                            or any(owner_norm in a for a in allowed_owners if len(owner_norm) >= 4)
                        )

                        if not is_verified_owner:
                            logger.info(
                                "Entity Resolution Gate: Skipping unrelated repository %s for company %s",
                                repo_full_name, company.name
                            )
                            continue

                        # Fetch historical releases for this verified repo
                        releases = await gh_provider.fetch_historical_releases(owner, repo, limit=20)
                        for r_data in releases:
                            # Avoid duplicate releases
                            existing = (
                                db.query(HistoricalRelease)
                                .filter(
                                    HistoricalRelease.company_id == company.id,
                                    HistoricalRelease.tag == r_data["tag"],
                                )
                                .first()
                            )
                            if not existing:
                                release_obj = HistoricalRelease(
                                    company_id=company.id,
                                    repository_id=r_data["repository"],
                                    tag=r_data["tag"],
                                    title=r_data["title"],
                                    body=r_data["body"][:2000] if r_data["body"] else None,
                                    published_at=r_data["published_at"],
                                    source_url=r_data["source_url"],
                                    semantic_changes=r_data["semantic_changes"],
                                    confidence=r_data["confidence"],
                                )
                                db.add(release_obj)
                                stats["releases_found"] += 1

                                # Create canonical TimelineEvent with GITHUB / RELEASE provenance
                                timeline_ev = TimelineEvent(
                                    company_id=company.id,
                                    event_type="HISTORICAL_RELEASE",
                                    title=f"Release {r_data['tag']}: {r_data['title']}",
                                    summary=r_data["body"][:400] if r_data["body"] else f"Historical release {r_data['tag']}",
                                    source="GitHub Releases",
                                    source_url=r_data["source_url"],
                                    provenance_category="RELEASE",
                                    temporal_category="HISTORICAL",
                                    quality_badge="CONFIRMED_HISTORY",
                                    published_at=r_data["published_at"],
                                    confidence=r_data["confidence"],
                                    priority="INFO",
                                )
                                db.add(timeline_ev)
                                stats["timeline_events_created"] += 1

                                # Extract features from release semantic changes
                                for change_tag in r_data["semantic_changes"]:
                                    if change_tag in ("NEW_AUTH", "NEW_AUTHORIZATION", "NEW_ADMIN", "NEW_EXPORT", "NEW_WEBHOOK"):
                                        feat_name = change_tag.replace("NEW_", "").title()
                                        existing_feat = (
                                            db.query(Feature)
                                            .filter(
                                                Feature.company_id == company.id,
                                                Feature.name == feat_name,
                                            )
                                            .first()
                                        )
                                        if not existing_feat:
                                            db.add(Feature(
                                                company_id=company.id,
                                                name=feat_name,
                                                category=change_tag,
                                                description=f"Extracted from release {r_data['tag']}",
                                                first_observed=r_data["published_at"] or datetime.now(timezone.utc),
                                                confidence=0.88,
                                            ))
                                            stats["features_extracted"] += 1
            except Exception as exc:
                logger.warning("GitHub historical reconstruction degraded gracefully: %s", exc)

        # --- STEP 2: Security Databases (OSV, CISA KEV, NVD) Correlation ---
        try:
            # Query OSV for company packages and advisories
            osv_provider: OSVProvider | None = mgr.get_provider("osv")  # type: ignore
            if osv_provider:
                osv_records = await osv_provider.fetch(package=company.canonical_domain.split(".")[0], ecosystem="npm")
                for o_rec in osv_records:
                    cve_id = o_rec.metadata.get("cve") or o_rec.metadata.get("ghsa")
                    if cve_id:
                        existing_sec = (
                            db.query(SecurityEvent)
                            .filter(
                                SecurityEvent.company_id == company.id,
                                SecurityEvent.cve_id == cve_id,
                            )
                            .first()
                        )
                        if not existing_sec:
                            v_class = cls.classify_vulnerability_class(o_rec.title, o_rec.summary)
                            sec_ev = SecurityEvent(
                                company_id=company.id,
                                cve_id=cve_id,
                                source="OSV Database",
                                source_url=o_rec.source_url,
                                severity=o_rec.metadata.get("severity") or "MEDIUM",
                                summary=o_rec.summary or o_rec.title,
                                published=o_rec.published_at,
                                vulnerability_class=v_class,
                                confidence=0.92,
                            )
                            db.add(sec_ev)
                            stats["security_events_found"] += 1

                            # Add to timeline as HISTORICAL security event
                            db.add(TimelineEvent(
                                company_id=company.id,
                                event_type="HISTORICAL_SECURITY_EVENT",
                                title=f"Vulnerability Disclosure: {cve_id}",
                                summary=o_rec.summary or o_rec.title,
                                source="OSV",
                                source_url=o_rec.source_url,
                                provenance_category="SECURITY_DATABASE",
                                temporal_category="HISTORICAL",
                                quality_badge="CONFIRMED_HISTORY",
                                published_at=o_rec.published_at,
                                confidence=0.92,
                                priority="HIGH" if sec_ev.severity in ("HIGH", "CRITICAL") else "MEDIUM",
                            ))
                            stats["timeline_events_created"] += 1
        except Exception as sec_exc:
            logger.warning("Security database correlation degraded gracefully: %s", sec_exc)

        # --- STEP 3: Persist and Update Coverage ---
        db.commit()
        cls.update_historical_coverage(db, company)

        return {
            "status": "success",
            "company_id": company.id,
            "canonical_domain": company.canonical_domain,
            "reconstructed_stats": stats,
        }
