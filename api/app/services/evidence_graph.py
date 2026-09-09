"""Evidence Graph & Multi-Source Fusion Engine.

Constructs a unified, traceable evidence graph:
    SOURCE -> EVIDENCE -> ENTITY -> OBSERVATION -> CHANGE -> SECURITY CONTEXT -> RESEARCH SIGNAL

Enforces evidence strength hierarchy, independent multi-source convergence,
and explicit handling of conflicting or unverified observations (e.g. DOCUMENTED_NOT_OBSERVED).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional, Sequence


class EvidenceSourceType(str, Enum):
    """Supported canonical source types for all intelligence evidence."""
    GITHUB = "GITHUB"
    CISA_KEV = "CISA_KEV"
    NVD = "NVD"
    OSV = "OSV"
    GHSA = "GHSA"
    VENDOR_ADVISORY = "VENDOR_ADVISORY"
    DOCUMENTATION = "DOCUMENTATION"
    CHANGELOG = "CHANGELOG"
    RELEASE = "RELEASE"
    OPENAPI = "OPENAPI"
    WEB_ARCHIVE = "WEB_ARCHIVE"
    BROWSER_OBSERVATION = "BROWSER_OBSERVATION"
    AST_ANALYSIS = "AST_ANALYSIS"
    PUBLIC_DISCLOSURE = "PUBLIC_DISCLOSURE"


class EvidenceStrength(str, Enum):
    """Evidence confidence hierarchy.

    Weak sources cannot override strong sources.
    """
    DIRECT_PRODUCTION_OBSERVATION = "DIRECT_PRODUCTION_OBSERVATION"
    OFFICIAL_SECURITY_ADVISORY = "OFFICIAL_SECURITY_ADVISORY"
    OFFICIAL_RELEASE = "OFFICIAL_RELEASE"
    OFFICIAL_DOCUMENTATION = "OFFICIAL_DOCUMENTATION"
    OFFICIAL_GITHUB = "OFFICIAL_GITHUB"
    RECOGNIZED_SECURITY_DATABASE = "RECOGNIZED_SECURITY_DATABASE"
    PUBLIC_DISCLOSURE = "PUBLIC_DISCLOSURE"
    THIRD_PARTY_REFERENCE = "THIRD_PARTY_REFERENCE"
    HEURISTIC = "HEURISTIC"


# Priority ranking (higher number = stronger evidence)
STRENGTH_WEIGHTS: dict[EvidenceStrength, float] = {
    EvidenceStrength.DIRECT_PRODUCTION_OBSERVATION: 1.0,
    EvidenceStrength.OFFICIAL_SECURITY_ADVISORY: 0.95,
    EvidenceStrength.OFFICIAL_RELEASE: 0.90,
    EvidenceStrength.OFFICIAL_DOCUMENTATION: 0.85,
    EvidenceStrength.OFFICIAL_GITHUB: 0.80,
    EvidenceStrength.RECOGNIZED_SECURITY_DATABASE: 0.75,
    EvidenceStrength.PUBLIC_DISCLOSURE: 0.70,
    EvidenceStrength.THIRD_PARTY_REFERENCE: 0.50,
    EvidenceStrength.HEURISTIC: 0.30,
}


class ObservationState(str, Enum):
    """Researcher-visible observation status badge."""
    CONFIRMED = "CONFIRMED"
    OBSERVED = "OBSERVED"
    DOCUMENTED = "DOCUMENTED"
    DOCUMENTED_NOT_OBSERVED = "DOCUMENTED_NOT_OBSERVED"
    HISTORICAL = "HISTORICAL"
    DEVELOPMENT_EVIDENCE = "DEVELOPMENT_EVIDENCE"
    INFERRED = "INFERRED"


# Default mapping from source type to default evidence strength
SOURCE_TO_DEFAULT_STRENGTH: dict[EvidenceSourceType, EvidenceStrength] = {
    EvidenceSourceType.BROWSER_OBSERVATION: EvidenceStrength.DIRECT_PRODUCTION_OBSERVATION,
    EvidenceSourceType.AST_ANALYSIS: EvidenceStrength.DIRECT_PRODUCTION_OBSERVATION,
    EvidenceSourceType.VENDOR_ADVISORY: EvidenceStrength.OFFICIAL_SECURITY_ADVISORY,
    EvidenceSourceType.RELEASE: EvidenceStrength.OFFICIAL_RELEASE,
    EvidenceSourceType.CHANGELOG: EvidenceStrength.OFFICIAL_RELEASE,
    EvidenceSourceType.DOCUMENTATION: EvidenceStrength.OFFICIAL_DOCUMENTATION,
    EvidenceSourceType.OPENAPI: EvidenceStrength.OFFICIAL_DOCUMENTATION,
    EvidenceSourceType.GITHUB: EvidenceStrength.OFFICIAL_GITHUB,
    EvidenceSourceType.CISA_KEV: EvidenceStrength.RECOGNIZED_SECURITY_DATABASE,
    EvidenceSourceType.NVD: EvidenceStrength.RECOGNIZED_SECURITY_DATABASE,
    EvidenceSourceType.OSV: EvidenceStrength.RECOGNIZED_SECURITY_DATABASE,
    EvidenceSourceType.GHSA: EvidenceStrength.RECOGNIZED_SECURITY_DATABASE,
    EvidenceSourceType.PUBLIC_DISCLOSURE: EvidenceStrength.PUBLIC_DISCLOSURE,
    EvidenceSourceType.WEB_ARCHIVE: EvidenceStrength.THIRD_PARTY_REFERENCE,
}


@dataclass
class EvidenceNode:
    """A verified node in the evidence graph."""
    source_type: EvidenceSourceType
    strength: EvidenceStrength
    source_url: str
    evidence_text: str
    content_hash: str
    observed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    raw_metadata: dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.8

    def __post_init__(self):
        if not (0.0 <= self.confidence <= 1.0):
            self.confidence = max(0.0, min(1.0, self.confidence))


@dataclass
class FusedEvidence:
    """Consolidated fact synthesized across multiple independent evidence nodes."""
    canonical_id: str
    observation_state: ObservationState
    fused_confidence: float
    primary_strength: EvidenceStrength
    evidence_records: list[EvidenceNode] = field(default_factory=list)
    source_types: list[EvidenceSourceType] = field(default_factory=list)
    is_conflicting: bool = False
    conflict_note: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class EvidenceGraphService:
    """Orchestrates evidence evaluation, convergence calculation, and conflict resolution."""

    @classmethod
    def calculate_converged_confidence(cls, evidence_nodes: Sequence[EvidenceNode]) -> float:
        """Calculates multi-source confidence with diminishing returns.

        Multiple independent corroborating sources increase overall confidence,
        capped strictly at 0.98. A single weak source cannot elevate confidence
        beyond its bounded weight.
        """
        if not evidence_nodes:
            return 0.0

        # Find highest single evidence confidence as the foundational base
        max_base_conf = max(
            node.confidence * STRENGTH_WEIGHTS.get(node.strength, 0.5)
            for node in evidence_nodes
        )

        distinct_sources = {node.source_type for node in evidence_nodes}
        if len(distinct_sources) <= 1:
            return round(min(0.95, max_base_conf), 3)

        # Multi-source convergence boost: asymptotic approach toward 0.98 cap
        independent_count = len(distinct_sources)
        boost = 0.04 * (independent_count - 1)
        converged = max_base_conf + boost
        return round(min(0.98, converged), 3)

    @classmethod
    def fuse_evidence(
        cls,
        canonical_id: str,
        evidence_nodes: Sequence[EvidenceNode],
        observed_in_production: Optional[bool] = None,
    ) -> FusedEvidence:
        """Fuses multiple evidence nodes into a single authoritative observation state.

        Detects conflicts (e.g. Documentation declares presence, but Browser does not observe it).
        """
        if not evidence_nodes:
            return FusedEvidence(
                canonical_id=canonical_id,
                observation_state=ObservationState.INFERRED,
                fused_confidence=0.2,
                primary_strength=EvidenceStrength.HEURISTIC,
            )

        # Sort by strength (strongest first)
        sorted_nodes = sorted(
            evidence_nodes,
            key=lambda n: STRENGTH_WEIGHTS.get(n.strength, 0.0),
            reverse=True,
        )
        primary_node = sorted_nodes[0]
        sources = list({n.source_type for n in evidence_nodes})

        has_production = any(
            n.strength == EvidenceStrength.DIRECT_PRODUCTION_OBSERVATION
            for n in evidence_nodes
        ) or observed_in_production is True
        has_documentation = any(
            n.source_type in (EvidenceSourceType.DOCUMENTATION, EvidenceSourceType.OPENAPI)
            for n in evidence_nodes
        )
        has_github = any(
            n.source_type == EvidenceSourceType.GITHUB for n in evidence_nodes
        )
        has_historical = any(
            n.source_type == EvidenceSourceType.WEB_ARCHIVE for n in evidence_nodes
        )

        # Determine observation state and check for conflicts
        is_conflicting = False
        conflict_note = None

        if has_documentation and observed_in_production is False:
            state = ObservationState.DOCUMENTED_NOT_OBSERVED
            is_conflicting = True
            conflict_note = (
                "Entity is documented in public specifications but was not observed "
                "in direct production verification. It may be unreleased, internal-only, or deprecated."
            )
        elif has_production:
            state = ObservationState.OBSERVED
            if has_documentation or len(sources) >= 2:
                state = ObservationState.CONFIRMED
        elif has_documentation:
            state = ObservationState.DOCUMENTED
        elif has_github:
            state = ObservationState.DEVELOPMENT_EVIDENCE
        elif has_historical:
            state = ObservationState.HISTORICAL
        else:
            state = ObservationState.INFERRED

        fused_conf = cls.calculate_converged_confidence(evidence_nodes)

        # Reduce confidence slightly if conflicting
        if is_conflicting:
            fused_conf = round(max(0.3, fused_conf * 0.75), 3)

        return FusedEvidence(
            canonical_id=canonical_id,
            observation_state=state,
            fused_confidence=fused_conf,
            primary_strength=primary_node.strength,
            evidence_records=list(sorted_nodes),
            source_types=sources,
            is_conflicting=is_conflicting,
            conflict_note=conflict_note,
        )

    @classmethod
    def trace_claim(
        cls,
        signal_id: int,
        source_name: str,
        evidence_text: str,
        entity_name: str,
        change_summary: str,
        security_context_summary: str,
        observation_summary: str = "Normalized observation record",
    ) -> dict[str, Any]:
        """Constructs an unbroken audit trace for an intelligence claim:

        SOURCE -> EVIDENCE -> ENTITY -> OBSERVATION -> CHANGE -> SECURITY CONTEXT -> RESEARCH SIGNAL
        """
        return {
            "chain": [
                {"step": "SOURCE", "value": source_name},
                {"step": "EVIDENCE", "value": evidence_text},
                {"step": "ENTITY", "value": entity_name},
                {"step": "OBSERVATION", "value": observation_summary},
                {"step": "CHANGE", "value": change_summary},
                {"step": "SECURITY_CONTEXT", "value": security_context_summary},
                {"step": "RESEARCH_SIGNAL", "value": f"Signal #{signal_id}"},
            ],
            "traced_at": datetime.now(timezone.utc).isoformat(),
            "valid": True,
        }
