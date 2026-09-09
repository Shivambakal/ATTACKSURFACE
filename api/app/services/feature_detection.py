"""Feature and API attack-surface extraction service.

Analyzes normalized observations to identify user capabilities, authentication boundaries,
API surfaces, and asset lifecycles.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse

from .normalization import NormalizedContent


@dataclass
class ExtractedFeature:
    name: str
    feature_type: str
    description: str
    confidence: float
    affected_assets: list[str] = field(default_factory=list)
    evidence_payload: dict[str, Any] = field(default_factory=dict)
    security_relevant: bool = True


@dataclass
class ExtractedApiSurface:
    method: str
    path: str
    version: str | None
    auth_requirement: str | None
    parameters: list[str] = field(default_factory=list)
    confidence: float = 0.9
    source_url: str = ""


FEATURE_RULES = [
    {
        "name": "OAuth & Social Sign-On Integration",
        "type": "AUTHENTICATION_WORKFLOW",
        "pattern": re.compile(r"\b(?:oauth|google login|github login|sign in with|sso|saml|oidc)\b", re.IGNORECASE),
        "description": "Publicly exposed single sign-on or OAuth authorization endpoint.",
        "security_relevant": True,
    },
    {
        "name": "Team & Organization Invitation System",
        "type": "AUTHORIZATION_WORKFLOW",
        "pattern": re.compile(r"\b(?:invite (?:team|member|user)|organization roles?|membership invitation|add collaborator)\b", re.IGNORECASE),
        "description": "User invitation and role delegation capability.",
        "security_relevant": True,
    },
    {
        "name": "Bulk Data Export / Archive Download",
        "type": "DATA_HANDLING",
        "pattern": re.compile(r"\b(?:bulk export|export (?:users|data|records)|download report|audit log export)\b", re.IGNORECASE),
        "description": "Data retrieval capability that generates bulk data downloads.",
        "security_relevant": True,
    },
    {
        "name": "File Upload & Media Ingestion",
        "type": "FILE_HANDLING",
        "pattern": re.compile(r"\b(?:upload (?:avatar|file|document|attachment)|multipart/form-data|choose file)\b", re.IGNORECASE),
        "description": "Arbitrary or media file submission capability.",
        "security_relevant": True,
    },
    {
        "name": "Outbound Webhook Delivery Configuration",
        "type": "INTEGRATION",
        "pattern": re.compile(r"\b(?:webhooks?|webhook (?:url|endpoint|secret)|event subscriptions?|deliver payloads?)\b", re.IGNORECASE),
        "description": "System configured to deliver automated HTTP callbacks to user-supplied URLs.",
        "security_relevant": True,
    },
    {
        "name": "Administrative Console & RBAC",
        "type": "ADMINISTRATIVE_CONTROL",
        "pattern": re.compile(r"\b(?:admin portal|superadmin|manage permissions|system settings|tenant configuration)\b", re.IGNORECASE),
        "description": "Administrative control plane and privilege management surface.",
        "security_relevant": True,
    },
    {
        "name": "Personal Access Tokens & API Credentials",
        "type": "CREDENTIAL_MANAGEMENT",
        "pattern": re.compile(r"\b(?:api keys?|personal access tokens?|service accounts?|generate secret)\b", re.IGNORECASE),
        "description": "Developer credential generation and management interface.",
        "security_relevant": True,
    },
]


def extract_features_from_observation(norm: NormalizedContent) -> list[ExtractedFeature]:
    """Inspect normalized DOM, headings, and capabilities to extract concrete features."""
    features: list[ExtractedFeature] = []
    seen_types: set[str] = set()

    # Aggregate form inputs
    form_inputs_text = " ".join(
        f"{f.get('action', '')} {' '.join(i.get('name', '') for i in f.get('inputs', []))}"
        for f in norm.forms
    )

    combined_text = (
        f"{norm.title or ''} "
        f"{' '.join(norm.headings)} "
        f"{' '.join(norm.auth_indicators)} "
        f"{' '.join(norm.sensitive_capabilities)} "
        f"{form_inputs_text} "
        f"{norm.clean_text[:4000]}"
    )

    domain = urlparse(norm.canonical_url).netloc

    # 1. Evaluate declarative feature rules
    for rule in FEATURE_RULES:
        if rule["pattern"].search(combined_text):
            if rule["type"] not in seen_types:
                seen_types.add(rule["type"])
                features.append(
                    ExtractedFeature(
                        name=rule["name"],
                        feature_type=rule["type"],
                        description=rule["description"],
                        confidence=0.92,
                        affected_assets=[domain, norm.canonical_url],
                        evidence_payload={
                            "url": norm.canonical_url,
                            "matched_capability": rule["name"],
                        },
                        security_relevant=rule["security_relevant"],
                    )
                )

    # 2. File Upload from Form Inputs
    if any("file_upload" in cap for cap in norm.sensitive_capabilities) and "FILE_HANDLING" not in seen_types:
        features.append(
            ExtractedFeature(
                name="File Upload & Document Processing",
                feature_type="FILE_HANDLING",
                description="Interactive form containing file input fields for uploading documents or attachments.",
                confidence=0.95,
                affected_assets=[domain, norm.canonical_url],
                evidence_payload={"url": norm.canonical_url, "input_type": "file"},
                security_relevant=True,
            )
        )

    # 3. API Surface Feature
    if norm.api_endpoints and "API_SURFACE" not in seen_types:
        features.append(
            ExtractedFeature(
                name=f"Public API Surface ({len(norm.api_endpoints)} endpoints)",
                feature_type="API_SURFACE",
                description=f"Publicly documented API routes observed: {', '.join(norm.api_endpoints[:3])}",
                confidence=0.95,
                affected_assets=[domain, norm.canonical_url],
                evidence_payload={"endpoints": norm.api_endpoints},
                security_relevant=True,
            )
        )

    return features


def extract_api_endpoints_from_text(text: str, source_url: str) -> list[ExtractedApiSurface]:
    """Parse HTTP route patterns and OpenAPI references from public documentation or page bodies."""
    extracted: list[ExtractedApiSurface] = []
    seen: set[str] = set()

    # Match patterns like: POST /v2/orgs/{id}/members, GET /api/v1/users
    route_pattern = re.compile(
        r"\b(GET|POST|PUT|DELETE|PATCH)\s+([/][a-zA-Z0-9_\-/{}/.]+)\b"
    )
    for method, path in route_pattern.findall(text):
        key = f"{method}:{path}"
        if key not in seen:
            seen.add(key)
            # Infer auth requirement
            auth_req = "Bearer Token" if any(w in text.lower() for w in ("bearer", "authorization", "api key")) else "Public / Session"
            # Extract version
            version_match = re.search(r"/(v\d+)/", path)
            version = version_match.group(1) if version_match else "v1"

            extracted.append(
                ExtractedApiSurface(
                    method=method.upper(),
                    path=path,
                    version=version,
                    auth_requirement=auth_req,
                    confidence=0.92,
                    source_url=source_url,
                )
            )

    return extracted
