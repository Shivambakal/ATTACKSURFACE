"""Historical Replay & Coverage Regression Engine.

Provides:
1. Multi-epoch historical replay: Reconstructs state at distinct epochs (e.g. 2024, 2025, 2026)
   and evaluates delta evolution (2024 -> 2025, 2025 -> 2026).
2. Measurable coverage metrics: source_count, date_span, confirmed_events, likely_events,
   weak_events, unverified_periods, coverage_confidence. Never claims 'Complete history'.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Sequence


@dataclass
class EpochState:
    """The reconstructed state of an organization's attack surface at a specific epoch."""
    epoch_name: str
    timestamp: datetime
    active_endpoints: set[str] = field(default_factory=set)
    active_features: set[str] = field(default_factory=set)
    active_technologies: set[str] = field(default_factory=set)
    recorded_security_events: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class ReplayDelta:
    """Evolutionary comparison between two historical epochs."""
    from_epoch: str
    to_epoch: str
    added_endpoints: list[str] = field(default_factory=list)
    removed_endpoints: list[str] = field(default_factory=list)
    added_features: list[str] = field(default_factory=list)
    removed_features: list[str] = field(default_factory=list)
    technology_changes: list[str] = field(default_factory=list)
    new_security_events: list[str] = field(default_factory=list)


@dataclass
class CoverageQualityReport:
    """Measurable coverage metrics for reconstructed historical intelligence."""
    company_id: int
    date_span: str
    source_count: int
    confirmed_events: int
    likely_events: int
    weak_events: int
    unverified_periods: list[str]
    coverage_confidence: float
    transparency_disclaimer: str = (
        "Historical intelligence reconstructed from publicly available evidence. "
        "Coverage represents verifiable public signals and may be partial. "
        "Absence of evidence is not evidence of absence."
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "company_id": self.company_id,
            "date_span": self.date_span,
            "source_count": self.source_count,
            "confirmed_events": self.confirmed_events,
            "likely_events": self.likely_events,
            "weak_events": self.weak_events,
            "unverified_periods": self.unverified_periods,
            "coverage_confidence": round(self.coverage_confidence, 2),
            "transparency_disclaimer": self.transparency_disclaimer,
        }


class HistoricalReplayService:
    """Executes sequential replay comparisons and calculates coverage quality."""

    @classmethod
    def compare_epochs(cls, from_state: EpochState, to_state: EpochState) -> ReplayDelta:
        """Computes differences between two reconstructed historical snapshots."""
        added_ep = sorted(list(to_state.active_endpoints - from_state.active_endpoints))
        removed_ep = sorted(list(from_state.active_endpoints - to_state.active_endpoints))

        added_feat = sorted(list(to_state.active_features - from_state.active_features))
        removed_feat = sorted(list(from_state.active_features - to_state.active_features))

        tech_diff = sorted(list(
            (to_state.active_technologies - from_state.active_technologies)
            | (from_state.active_technologies - to_state.active_technologies)
        ))

        from_cves = {e.get("cve_id") for e in from_state.recorded_security_events if e.get("cve_id")}
        to_cves = {e.get("cve_id") for e in to_state.recorded_security_events if e.get("cve_id")}
        new_cves = sorted(list(to_cves - from_cves))

        return ReplayDelta(
            from_epoch=from_state.epoch_name,
            to_epoch=to_state.epoch_name,
            added_endpoints=added_ep,
            removed_endpoints=removed_ep,
            added_features=added_feat,
            removed_features=removed_feat,
            technology_changes=tech_diff,
            new_security_events=new_cves,
        )

    @classmethod
    def replay_sequence(cls, epoch_states: Sequence[EpochState]) -> list[ReplayDelta]:
        """Runs sequential diff evaluation across an ordered timeline of epochs."""
        if len(epoch_states) < 2:
            return []

        deltas = []
        for i in range(len(epoch_states) - 1):
            delta = cls.compare_epochs(epoch_states[i], epoch_states[i + 1])
            deltas.append(delta)
        return deltas

    @classmethod
    def compute_coverage_quality(
        cls,
        company_id: int,
        start_year: int,
        end_year: int,
        sources: Sequence[str],
        events: Sequence[dict[str, Any]],
        known_gaps: Optional[Sequence[str]] = None,
    ) -> CoverageQualityReport:
        """Calculates measurable historical coverage metrics with strict disclaimer."""
        confirmed = sum(1 for e in events if e.get("quality_badge") == "CONFIRMED_HISTORY" or e.get("confidence", 0) >= 0.85)
        likely = sum(1 for e in events if e.get("quality_badge") == "LIKELY_HISTORY" or (0.6 <= e.get("confidence", 0) < 0.85))
        weak = sum(1 for e in events if e.get("quality_badge") == "WEAK_HISTORY" or e.get("confidence", 0) < 0.6)

        total = len(events)
        source_count = len(set(sources))

        # Confidence calculation based on multi-source density and continuity
        base_score = 0.5
        if source_count >= 3:
            base_score += 0.2
        if total >= 20:
            base_score += 0.15
        if known_gaps:
            base_score -= 0.1 * len(known_gaps)

        coverage_confidence = max(0.2, min(0.92, base_score))

        return CoverageQualityReport(
            company_id=company_id,
            date_span=f"{start_year} -> {end_year}",
            source_count=source_count,
            confirmed_events=confirmed,
            likely_events=likely,
            weak_events=weak,
            unverified_periods=list(known_gaps or []),
            coverage_confidence=coverage_confidence,
        )
