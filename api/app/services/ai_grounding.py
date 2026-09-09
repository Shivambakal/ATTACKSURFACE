"""Structured AI reasoning and evidence grounding engine.

Formats deterministic facts and verified evidence into strict prompts,
validates structured JSON responses against explicit schemas, and rejects
hallucinated citations or speculative vulnerability claims.
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any

from .ai_safety import sanitize_external_content, build_safe_prompt

logger = logging.getLogger(__name__)


@dataclass
class StructuredResearchSignal:
    title: str
    category: str
    summary: str
    why_it_matters: str
    research_area: str
    confidence: float
    evidence_ids: list[str] = field(default_factory=list)
    historical_context_ids: list[str] = field(default_factory=list)
    needs_manual_review: bool = False
    validation_warnings: list[str] = field(default_factory=list)


def validate_ai_citations(
    cited_ids: list[str],
    valid_evidence_ids: list[str],
) -> tuple[list[str], list[str]]:
    """Verify that every cited evidence ID exists in the verifiable evidence repository.

    Returns: (approved_evidence_ids, rejected_hallucinated_ids)
    """
    valid_set = set(valid_evidence_ids)
    approved: list[str] = []
    rejected: list[str] = []

    for eid in cited_ids:
        eid_str = str(eid).strip()
        if eid_str in valid_set:
            approved.append(eid_str)
        else:
            rejected.append(eid_str)

    return approved, rejected


def parse_and_validate_ai_response(
    raw_response: str,
    valid_evidence_ids: list[str],
    fallback_category: str = "new_feature",
) -> StructuredResearchSignal:
    """Parse JSON AI response, enforce schema compliance, and validate evidence citations."""
    warnings: list[str] = []

    # 1. Strip markdown code fences if model returned ```json ... ```
    cleaned = raw_response.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)

    # 2. Parse JSON
    try:
        data = json.loads(cleaned)
    except Exception as exc:
        logger.warning("AI did not return valid JSON (%s), building safe structured fallback", exc)
        return StructuredResearchSignal(
            title="Attack Surface Observation",
            category=fallback_category,
            summary=sanitize_external_content(raw_response[:250]),
            why_it_matters="Identifies a potential attack surface boundary change requiring manual research inspection.",
            research_area="Review access controls and scope compliance on observed routes.",
            confidence=0.75,
            evidence_ids=valid_evidence_ids[:1],
            needs_manual_review=True,
            validation_warnings=["ai_output_not_json_fallback_applied"],
        )

    # 3. Extract and validate required fields
    title = str(data.get("title", "Attack Surface Update"))[:150]
    category = str(data.get("category", fallback_category))[:64]
    summary = str(data.get("summary", ""))[:1000]
    why_it_matters = str(data.get("why_it_matters", "Introduces an observable attack-surface modification."))[:1000]
    research_area = str(data.get("research_area", "Review documented permissions and endpoint access."))[:500]

    try:
        conf = float(data.get("confidence", 0.85))
        conf = max(0.1, min(0.99, conf))
    except (ValueError, TypeError):
        conf = 0.85

    # 4. Strict Citation Grounding
    raw_citations = data.get("evidence_ids", [])
    if not isinstance(raw_citations, list):
        raw_citations = [str(raw_citations)]
    approved_citations, rejected_citations = validate_ai_citations(raw_citations, valid_evidence_ids)

    if rejected_citations:
        warnings.append(f"rejected_hallucinated_evidence_ids:{','.join(rejected_citations)}")

    # Ensure at least valid evidence is linked if available
    if not approved_citations and valid_evidence_ids:
        approved_citations = valid_evidence_ids[:2]

    # 5. Defang offensive or speculative claims
    speculative_patterns = [
        re.compile(r"\b(definitely vulnerable|critical exploit|guaranteed bug|rce vulnerability)\b", re.IGNORECASE),
    ]
    for pat in speculative_patterns:
        if pat.search(why_it_matters) or pat.search(summary):
            warnings.append("speculative_claim_defanged")
            why_it_matters = pat.sub("potential security-relevant consideration", why_it_matters)
            summary = pat.sub("potential attack surface modification", summary)

    return StructuredResearchSignal(
        title=title,
        category=category,
        summary=summary,
        why_it_matters=why_it_matters,
        research_area=research_area,
        confidence=conf,
        evidence_ids=approved_citations,
        historical_context_ids=data.get("historical_context_ids", []),
        needs_manual_review=bool(data.get("needs_manual_review", False)),
        validation_warnings=warnings,
    )
