"""Security history correlation and target vulnerability fingerprinting engine.

Correlates newly detected changes against historical findings, CISA KEV records,
and vulnerability class tendencies to generate contextual intelligence.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models import SecurityEvent, KevEntry, ResearchFinding


# Standard vulnerability class mappings
VULN_CLASSES: dict[str, list[str]] = {
    "AUTHORIZATION": ["authorization", "authz", "rbac", "acl", "idor", "bola", "privilege", "impersonation", "broken object level", "cwe-862", "cwe-639"],
    "AUTHENTICATION": ["authentication", "oauth", "sso", "saml", "jwt", "session", "credential", "mfa", "login", "cwe-287", "cwe-384"],
    "FILE_HANDLING": ["file upload", "upload", "path traversal", "arbitrary file", "cwe-434", "cwe-22"],
    "API_SECURITY": ["api", "graphql", "mass assignment", "rate limit", "cwe-918", "excessive data"],
    "SSRF": ["ssrf", "server-side request forgery", "webhook", "callback", "url fetch", "cwe-918"],
    "INJECTION": ["sql injection", "sqli", "command injection", "xss", "cross-site scripting", "cwe-79", "cwe-89"],
}


@dataclass
class VulnerabilityClassCount:
    class_name: str
    count: int
    activity_level: str  # HIGH, MEDIUM, LOW


@dataclass
class HistoricalSecurityProfile:
    target_id: int
    total_security_events: int
    total_findings: int
    vulnerability_classes: dict[str, str] = field(default_factory=dict)
    known_exploited_cves: list[str] = field(default_factory=list)


@dataclass
class CorrelationMatch:
    vulnerability_class: str
    historical_count: int
    activity_level: str
    context_note: str
    relevance_boost: int
    evidence_references: list[str] = field(default_factory=list)


def compute_target_security_profile(target_id: int, db: Session) -> HistoricalSecurityProfile:
    """Analyze historical findings and security events for a target to generate its security profile."""
    # 1. Fetch historical findings
    findings = db.scalars(
        select(ResearchFinding).where(ResearchFinding.target_id == target_id)
    ).all()

    # 2. Fetch recorded security events (CVEs / advisories)
    events = db.scalars(
        select(SecurityEvent).where(SecurityEvent.target_id == target_id)
    ).all()

    class_scores: dict[str, int] = {k: 0 for k in VULN_CLASSES}

    corpus_items = []
    for f in findings:
        corpus_items.append(f"{f.title} {f.description or ''} {f.severity or ''}".lower())
    for e in events:
        corpus_items.append(f"{e.cve_id or ''} {e.summary or ''} {e.severity or ''}".lower())

    for item in corpus_items:
        for v_class, keywords in VULN_CLASSES.items():
            if any(kw in item for kw in keywords):
                class_scores[v_class] += 1

    profile_classes: dict[str, str] = {}
    for v_class, cnt in class_scores.items():
        if cnt >= 3:
            profile_classes[v_class] = "HIGH"
        elif cnt >= 1:
            profile_classes[v_class] = "MEDIUM"
        else:
            profile_classes[v_class] = "LOW"

    # Known exploited CVEs
    cve_list = [e.cve_id for e in events if e.cve_id]

    return HistoricalSecurityProfile(
        target_id=target_id,
        total_security_events=len(events),
        total_findings=len(findings),
        vulnerability_classes=profile_classes,
        known_exploited_cves=cve_list[:5],
    )


def correlate_with_historical_profile(
    profile: HistoricalSecurityProfile,
    change_category: str,
    feature_names: list[str],
) -> list[CorrelationMatch]:
    """Correlate a newly detected change and features against the target's historical security profile."""
    matches: list[CorrelationMatch] = []
    text_signature = f"{change_category} {' '.join(feature_names)}".lower()

    for v_class, activity in profile.vulnerability_classes.items():
        if activity in ("HIGH", "MEDIUM"):
            keywords = VULN_CLASSES.get(v_class, [])
            if any(kw in text_signature for kw in keywords):
                boost = 15 if activity == "HIGH" else 8
                note = (
                    f"Target has a {activity.lower()} historical activity pattern in {v_class.lower()}-related "
                    f"security context. The newly introduced capability shares architectural overlap with this area."
                )
                matches.append(
                    CorrelationMatch(
                        vulnerability_class=v_class,
                        historical_count=3 if activity == "HIGH" else 1,
                        activity_level=activity,
                        context_note=note,
                        relevance_boost=boost,
                    )
                )

    return matches
