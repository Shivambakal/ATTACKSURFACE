"""Conservative Scope Correlation Engine for Bug Bounty Research Intelligence.

Evaluates discovered domains and assets against verified security program rules.
Never silently promotes an unconfirmed domain into IN_SCOPE.
"""
from __future__ import annotations

import fnmatch
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Sequence

from sqlalchemy.orm import Session

from app.models.security_program import (
    InclusionType,
    ProgramScopeRule,
    ScopeStatus,
    SecurityProgram,
    VerificationStatus,
)
from app.models.asset import Asset
from app.models.company import Company


@dataclass
class ScopeDecision:
    """The authoritative result of a scope resolution decision."""
    status: ScopeStatus
    confidence: float
    reason: str
    matched_rule: str | None = None
    source_url: str | None = None
    temporal_valid: bool = True
    decided_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            "status": self.status.value,
            "confidence": round(self.confidence, 2),
            "reason": self.reason,
            "matched_rule": self.matched_rule,
            "source_url": self.source_url,
            "temporal_valid": self.temporal_valid,
            "decided_at": self.decided_at.isoformat(),
        }


class ScopeResolver:
    """Evaluates assets against security program scope rules with zero false-scope assumptions."""

    @staticmethod
    def match_pattern(pattern: str, hostname: str) -> bool:
        """Case-insensitive pattern matching supporting standard wildcard syntax."""
        pat = pattern.strip().lower()
        host = hostname.strip().lower()

        if pat == host:
            return True

        # Support *.domain.com wildcard matching
        if pat.startswith("*."):
            suffix = pat[1:]  # .domain.com
            base = pat[2:]    # domain.com
            return host.endswith(suffix) or host == base

        return fnmatch.fnmatch(host, pat)

    @classmethod
    def evaluate(
        cls,
        hostname: str,
        rules: Sequence[ProgramScopeRule],
        canonical_domain: str | None = None,
        at_time: datetime | None = None,
    ) -> ScopeDecision:
        """Evaluate a hostname against program scope rules with optional temporal filtering."""
        if not hostname:
            return ScopeDecision(
                status=ScopeStatus.UNKNOWN,
                confidence=0.1,
                reason="Scope could not be verified from available evidence (empty hostname).",
            )

        norm_host = hostname.strip().lower().rstrip(".")

        # Filter rules by temporal validity window if at_time is specified
        active_rules: list[ProgramScopeRule] = []
        for r in rules:
            if at_time:
                t = at_time
                rf = r.valid_from
                rt = r.valid_to
                if rf and rf.tzinfo is None and t.tzinfo is not None:
                    rf = rf.replace(tzinfo=timezone.utc)
                elif rf and rf.tzinfo is not None and t.tzinfo is None:
                    t = t.replace(tzinfo=timezone.utc)
                if rf and t < rf:
                    continue

                if rt and rt.tzinfo is None and t.tzinfo is not None:
                    rt = rt.replace(tzinfo=timezone.utc)
                elif rt and rt.tzinfo is not None and t.tzinfo is None:
                    t = t.replace(tzinfo=timezone.utc)
                if rt and t > rt:
                    continue
            active_rules.append(r)

        # Step 1: Check explicit EXCLUDE rules first
        for rule in active_rules:
            if rule.inclusion_type == InclusionType.EXCLUDE.value:
                if cls.match_pattern(rule.pattern, norm_host):
                    return ScopeDecision(
                        status=ScopeStatus.OUT_OF_SCOPE,
                        confidence=rule.confidence,
                        reason=f"Explicitly excluded by scope rule: '{rule.pattern}' (Source: {rule.source_url or 'Official Policy'})",
                        matched_rule=rule.pattern,
                        source_url=rule.source_url,
                        temporal_valid=True,
                    )

        # Step 2: Check explicit INCLUDE rules
        for rule in active_rules:
            if rule.inclusion_type == InclusionType.INCLUDE.value:
                if cls.match_pattern(rule.pattern, norm_host):
                    return ScopeDecision(
                        status=ScopeStatus.IN_SCOPE,
                        confidence=rule.confidence,
                        reason=f"Matched active in-scope program rule: '{rule.pattern}' (Source: {rule.source_url or 'Official Policy'})",
                        matched_rule=rule.pattern,
                        source_url=rule.source_url,
                        temporal_valid=True,
                    )

        # Step 3: Check CONDITIONAL rules
        for rule in active_rules:
            if rule.inclusion_type == InclusionType.CONDITIONAL.value:
                if cls.match_pattern(rule.pattern, norm_host):
                    return ScopeDecision(
                        status=ScopeStatus.RELATED,
                        confidence=rule.confidence * 0.8,
                        reason=f"Subject to conditional scope constraints: '{rule.pattern}'. Verification required.",
                        matched_rule=rule.pattern,
                        source_url=rule.source_url,
                        temporal_valid=True,
                    )

        # Step 4: Fallback based on organizational relationship
        if canonical_domain:
            norm_canonical = canonical_domain.strip().lower().rstrip(".")
            if norm_host == norm_canonical or norm_host.endswith("." + norm_canonical):
                if active_rules:
                    return ScopeDecision(
                        status=ScopeStatus.RELATED,
                        confidence=0.7,
                        reason="Organizational subdomain, but not explicitly enumerated in active program scope rules.",
                    )
                else:
                    return ScopeDecision(
                        status=ScopeStatus.PENDING_VERIFICATION,
                        confidence=0.5,
                        reason="Discovered under canonical root domain; security program scope rules pending verification.",
                    )

        # Step 5: Unrelated or unconfirmed domain
        return ScopeDecision(
            status=ScopeStatus.UNKNOWN,
            confidence=0.3,
            reason="Scope could not be verified from available evidence.",
        )

    @classmethod
    def resolve_asset(cls, db: Session, asset: Asset, company: Company) -> ScopeDecision:
        """Resolves scope for an asset using company's programs and updates the asset record."""
        # Gather all rules across active security programs of the company
        rules: list[ProgramScopeRule] = []
        for program in company.security_programs:
            if program.status == "ACTIVE":
                rules.extend(program.rules)

        hostname = asset.normalized_hostname or asset.hostname or asset.name
        decision = cls.evaluate(hostname, rules, canonical_domain=company.canonical_domain)

        # Update asset fields
        asset.scope_status = decision.status.value
        if decision.status == ScopeStatus.IN_SCOPE:
            asset.verification_status = VerificationStatus.VERIFIED.value
        elif decision.status == ScopeStatus.OUT_OF_SCOPE:
            asset.verification_status = VerificationStatus.VERIFIED.value
        elif decision.status == ScopeStatus.RELATED:
            asset.verification_status = VerificationStatus.PARTIALLY_VERIFIED.value
        else:
            asset.verification_status = VerificationStatus.UNVERIFIED.value

        asset.last_verified_at = datetime.now(timezone.utc)
        db.add(asset)
        return decision
