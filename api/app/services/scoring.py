"""Deterministic research priority, confidence, and security context scoring.

Every score is fully transparent and explainable — factors, positive_signals,
and negative_signals clearly communicate WHY a change received its priority.
Separates relevance from confidence and security context.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# ── Granular Signal Weights ───────────────────────────────────────────
POSITIVE_SIGNALS: dict[str, int] = {
    # High-impact security boundaries
    "NEW_SECURITY_SENSITIVE_FEATURE": 25,
    "AUTH_CHANGE": 25,
    "AUTHORIZATION_CHANGE": 25,
    "NEW_API": 20,
    "NEW_INTEGRATION": 20,
    "SENSITIVE_WORKFLOW": 15,
    "NEW_ASSET": 15,
    "TECHNOLOGY_CHANGE": 10,
    "HISTORICAL_SECURITY_CORRELATION": 15,
    "MULTIPLE_INDEPENDENT_SOURCES": 10,
    "FILE_UPLOAD_CAPABILITY": 15,
    "DATA_EXPORT_CAPABILITY": 15,
    "WEBHOOK_CAPABILITY": 15,
    "ADMIN_CAPABILITY": 20,
}

NEGATIVE_SIGNALS: dict[str, int] = {
    "COSMETIC": -30,
    "MARKETING_ONLY": -30,
    "TRACKING_ONLY": -25,
    "DUPLICATE": -25,
    "LOW_CONFIDENCE": -20,
    "NAVIGATION_ONLY": -20,
    "LEGAL_FOOTER_ONLY": -20,
    "COOKIE_BANNER_ONLY": -20,
    "EPHEMERAL_NOISE": -35,
}

CATEGORY_BASE_WEIGHTS: dict[str, int] = {
    "new_auth_surface": 80,
    "new_authz_surface": 80,
    "new_api_surface": 80,
    "new_api_documentation": 80,
    "sensitive_capability": 70,
    "authentication_documentation_change": 75,
    "api_or_feature_change": 65,
    "security_sensitive_change": 75,
    "technology_change": 45,
    "new_public_page": 35,
    "removed_public_page": 25,
    "marketing_content_change": 15,
    "public_content_change": 25,
    "noise": 0,
}

AUTH_KEYWORDS = ("oauth", "sso", "auth", "admin", "webhook", "token", "session", "permission", "rbac", "acl", "jwt", "saml")
API_KEYWORDS = ("api", "endpoint", "graphql", "rest", "grpc", "websocket", "openapi", "swagger")
SECURITY_KEYWORDS = ("cve", "vulnerability", "security", "patch", "fix", "advisory", "exploit", "xss", "sqli", "csrf", "ssrf", "idor", "bola")


@dataclass
class ScoreResult:
    """Transparent scoring result with full factor breakdown."""
    relevance_score: int
    confidence_score: int
    security_context_score: int
    priority: str
    factors: dict[str, int] = field(default_factory=dict)
    positive_signals: list[str] = field(default_factory=list)
    negative_signals: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "relevance_score": self.relevance_score,
            "confidence_score": self.confidence_score,
            "security_context_score": self.security_context_score,
            "priority": self.priority,
            "factors": self.factors,
            "positive_signals": self.positive_signals,
            "negative_signals": self.negative_signals,
        }


def _priority_from_score(score: int) -> str:
    if score >= 85:
        return "CRITICAL"
    if score >= 70:
        return "HIGH"
    if score >= 45:
        return "MEDIUM"
    if score >= 20:
        return "LOW"
    return "INFO"


def score(category: str, source_url: str, text: str = "", confidence: float = 0.9) -> int:
    """Legacy scoring function — returns integer relevance score."""
    result = score_detailed(category, source_url, text, confidence)
    return result.relevance_score


def score_detailed(
    category: str,
    source_url: str,
    text: str = "",
    confidence: float = 0.9,
    signals: list[str] | None = None,
    source_count: int = 1,
    historical_matches: int = 0,
    has_admin_capability: bool = False,
    is_direct_observation: bool = True,
) -> ScoreResult:
    """Full deterministic scoring with transparent factor breakdown across relevance, confidence, and security context."""
    factors: dict[str, int] = {}
    pos_signals: list[str] = []
    neg_signals: list[str] = []

    # 1. Base category weight
    base = CATEGORY_BASE_WEIGHTS.get(category, 25)
    factors["category_base"] = base

    # 2. Keyword boosts from URL and text
    words = (source_url + " " + text).lower()

    if any(kw in words for kw in AUTH_KEYWORDS):
        factors["auth_keyword_boost"] = 10
        pos_signals.append("AUTH_CHANGE")

    if category not in ("new_api_documentation", "new_api_surface") and any(kw in words for kw in API_KEYWORDS):
        factors["api_keyword_boost"] = 8
        pos_signals.append("NEW_API")

    if any(kw in words for kw in SECURITY_KEYWORDS):
        factors["security_keyword_boost"] = 12
        pos_signals.append("HISTORICAL_SECURITY_CORRELATION")

    # 3. Explicit signals
    if signals:
        for signal in signals:
            if signal in POSITIVE_SIGNALS:
                delta = POSITIVE_SIGNALS[signal]
                factors[f"signal_{signal}"] = delta
                if signal not in pos_signals:
                    pos_signals.append(signal)
            elif signal in NEGATIVE_SIGNALS:
                delta = NEGATIVE_SIGNALS[signal]
                factors[f"signal_{signal}"] = delta
                if signal not in neg_signals:
                    neg_signals.append(signal)

    # 4. Multi-source reinforcement
    if source_count > 1:
        bonus = min(15, (source_count - 1) * 5)
        factors["multi_source_reinforcement"] = bonus
        pos_signals.append("MULTIPLE_INDEPENDENT_SOURCES")

    # 5. Historical correlation boost
    if historical_matches > 0:
        hist_bonus = min(20, historical_matches * 8)
        factors["historical_vulnerability_correlation"] = hist_bonus
        if "HISTORICAL_SECURITY_CORRELATION" not in pos_signals:
            pos_signals.append("HISTORICAL_SECURITY_CORRELATION")

    # 6. Admin capability boost
    if has_admin_capability:
        factors["admin_capability_boost"] = 15
        pos_signals.append("ADMIN_CAPABILITY")

    # 7. Compute Relevance Score (bounded 0 - 100)
    raw_relevance = sum(factors.values())
    if category == "noise" or "EPHEMERAL_NOISE" in (signals or []):
        raw_relevance = min(raw_relevance, 5)

    relevance_score = max(0, min(100, raw_relevance))

    # 8. Compute Confidence Score (0 - 100)
    # Starts from baseline confidence, augmented by multiple sources and direct observation
    conf_base = int(confidence * 100) if confidence <= 1.0 else int(confidence)
    conf_adjust = 0
    if is_direct_observation:
        conf_adjust += 5
    if source_count >= 2:
        conf_adjust += 10
    if source_count >= 3:
        conf_adjust += 5
    if "LOW_CONFIDENCE" in (signals or []):
        conf_adjust -= 25

    confidence_score = max(10, min(99, conf_base + conf_adjust))

    # 9. Compute Security Context Score (0 - 100)
    # Reflects the architectural sensitivity of the affected domain and capabilities
    context_factors: list[int] = [30]  # Base public asset context
    if any(k in pos_signals for k in ("AUTH_CHANGE", "AUTHORIZATION_CHANGE", "NEW_SECURITY_SENSITIVE_FEATURE")):
        context_factors.append(35)
    if "NEW_API" in pos_signals:
        context_factors.append(20)
    if "ADMIN_CAPABILITY" in pos_signals:
        context_factors.append(25)
    if "FILE_UPLOAD_CAPABILITY" in pos_signals or "DATA_EXPORT_CAPABILITY" in pos_signals:
        context_factors.append(20)
    if historical_matches > 0:
        context_factors.append(min(25, historical_matches * 10))

    security_context_score = max(0, min(100, sum(context_factors)))

    return ScoreResult(
        relevance_score=relevance_score,
        confidence_score=confidence_score,
        security_context_score=security_context_score,
        priority=_priority_from_score(relevance_score),
        factors=factors,
        positive_signals=pos_signals,
        negative_signals=neg_signals,
    )
