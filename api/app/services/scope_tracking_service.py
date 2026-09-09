"""Continuous Program Scope Tracking and Multi-Source Precedence Service.

Tracks bug bounty program scopes from:
- OFFICIAL_SCOPE (Company security.txt, bug bounty policy pages)
- PUBLIC_SCOPE_MIRROR (HackerOne, Bugcrowd, Intigriti public program pages)
- THIRD_PARTY_SCOPE_DATA (Community repositories, project archives)

PRECEDENCE RULES:
1. OFFICIAL_SCOPE outranks PUBLIC_SCOPE_MIRROR.
2. PUBLIC_SCOPE_MIRROR outranks THIRD_PARTY_SCOPE_DATA.
3. EXCLUDE always beats INCLUDE (Defensive Boundary Priority).
4. No asset is declared in-scope solely because a TLS cert or DNS entry exists.
"""
from __future__ import annotations

import fnmatch
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class ScopeAuthority(str, Enum):
    OFFICIAL_SCOPE = "OFFICIAL_SCOPE"
    PUBLIC_SCOPE_MIRROR = "PUBLIC_SCOPE_MIRROR"
    THIRD_PARTY_SCOPE_DATA = "THIRD_PARTY_SCOPE_DATA"


class ScopeStatus(str, Enum):
    IN_SCOPE = "IN_SCOPE"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"
    CONDITIONAL = "CONDITIONAL"
    UNKNOWN = "UNKNOWN"


@dataclass
class ScopeTargetRule:
    pattern: str  # e.g. "*.example.com", "api.example.com"
    status: ScopeStatus
    authority: ScopeAuthority
    source_url: str
    effective_date: datetime | None = None
    bounty_eligible: bool = True
    instruction_notes: str = ""


class ScopeTrackingService:
    """Manages multi-source scope tracking with strict precedence resolution."""

    def __init__(self, rules: list[ScopeTargetRule] | None = None) -> None:
        self.rules = rules or []

    def add_rule(self, rule: ScopeTargetRule) -> None:
        self.rules.append(rule)

    def resolve_scope(self, hostname: str) -> tuple[ScopeStatus, str]:
        """Resolves whether a hostname is currently in-scope based on precedence hierarchy.

        Returns:
            (ScopeStatus, explanation_of_precedence)
        """
        host_clean = hostname.strip().lower().rstrip(".")

        # 1. Check EXCLUDE rules first across all authorities (Exclude beats Include)
        for authority in [ScopeAuthority.OFFICIAL_SCOPE, ScopeAuthority.PUBLIC_SCOPE_MIRROR, ScopeAuthority.THIRD_PARTY_SCOPE_DATA]:
            for r in self.rules:
                if r.authority == authority and r.status == ScopeStatus.OUT_OF_SCOPE:
                    if self._matches(host_clean, r.pattern):
                        return (
                            ScopeStatus.OUT_OF_SCOPE,
                            f"Excluded by {authority.value} rule: '{r.pattern}' from {r.source_url}",
                        )

        # 2. Check INCLUDE rules in order of authority
        for authority in [ScopeAuthority.OFFICIAL_SCOPE, ScopeAuthority.PUBLIC_SCOPE_MIRROR, ScopeAuthority.THIRD_PARTY_SCOPE_DATA]:
            for r in self.rules:
                if r.authority == authority and r.status == ScopeStatus.IN_SCOPE:
                    if self._matches(host_clean, r.pattern):
                        return (
                            ScopeStatus.IN_SCOPE,
                            f"Included by {authority.value} rule: '{r.pattern}' from {r.source_url}",
                        )

        return (ScopeStatus.UNKNOWN, "No scope rule matches target hostname.")

    def _matches(self, host: str, pattern: str) -> bool:
        pat = pattern.strip().lower().rstrip(".")
        if pat == host:
            return True
        if pat.startswith("*."):
            root = pat[2:]
            return host == root or host.endswith(f".{root}")
        return fnmatch.fnmatch(host, pat)
