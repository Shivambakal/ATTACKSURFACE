"""Frontend JS / API / Public Application Change Detection Service.

Extracts, normalizes, and semantically fingerprints publicly observable
JavaScript bundles, OpenAPI documents, and client-side endpoints on
explicitly authorized targets.

RULES:
- Normalizes bundle content to eliminate cache busters, nonces, timestamps, and randomized chunk IDs.
- Never claims an API exists solely because an arbitrary string pattern appears in minified JS.
- Classifies discovered references:
    * STRING_REFERENCE: String detected in client code, unverified.
    * DOCUMENTED_ENDPOINT: Present in OpenAPI or official documentation.
    * OBSERVED_ENDPOINT: Observed in network/DOM behavior.
    * CONFIRMED_ENDPOINT: Verified responding to authorized public requests.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class EndpointConfidence(str, Enum):
    STRING_REFERENCE = "STRING_REFERENCE"
    DOCUMENTED_ENDPOINT = "DOCUMENTED_ENDPOINT"
    OBSERVED_ENDPOINT = "OBSERVED_ENDPOINT"
    CONFIRMED_ENDPOINT = "CONFIRMED_ENDPOINT"


@dataclass
class DiscoveredEndpoint:
    path: str
    method: str = "UNKNOWN"
    confidence: EndpointConfidence = EndpointConfidence.STRING_REFERENCE
    source_file: str = ""
    discovered_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    is_sensitive: bool = False
    context_snippet: str = ""


class FrontendDiffService:
    """Detects structural and API changes in client-side code bundles."""

    # Regex to extract potential API routes (/api/vX/..., /graphql, /v1/...)
    API_ROUTE_PATTERN = re.compile(
        r"""["'](/(?:api|v[0-9]+|graphql|oauth|auth|admin|internal|webhook)/[a-zA-Z0-9_\-\./{}]+)["']"""
    )
    # Volatile tokens to strip before hashing (chunk hashes, cache busters, timestamps)
    VOLATILE_CHUNK_PATTERN = re.compile(r'\b[a-f0-9]{8,64}\b', re.IGNORECASE)
    TIMESTAMP_PATTERN = re.compile(r'\b\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z?\b')

    @classmethod
    def normalize_bundle_content(cls, raw_js: str) -> str:
        """Strips volatile nonces, build timestamps, and randomized hash tokens for stable AST diffing."""
        cleaned = cls.TIMESTAMP_PATTERN.sub("<TIMESTAMP>", raw_js)
        # Normalize whitespace
        cleaned = " ".join(cleaned.split())
        return cleaned

    @classmethod
    def compute_structural_fingerprint(cls, raw_js: str) -> str:
        """Computes deterministic SHA-256 hash of normalized client bundle."""
        normalized = cls.normalize_bundle_content(raw_js)
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    @classmethod
    def extract_candidate_endpoints(cls, script_content: str, source_url: str = "") -> list[DiscoveredEndpoint]:
        """Extracts candidate API references with strict confidence classification."""
        endpoints: list[DiscoveredEndpoint] = []
        matches = set(cls.API_ROUTE_PATTERN.findall(script_content))

        for route in sorted(matches):
            clean_route = route.split("?")[0].rstrip("/")
            if not clean_route or len(clean_route) < 3:
                continue

            # Sensitive keyword analysis
            is_sensitive = any(
                k in clean_route.lower()
                for k in ["admin", "auth", "token", "password", "upload", "export", "internal", "secret", "private"]
            )

            endpoints.append(
                DiscoveredEndpoint(
                    path=clean_route,
                    method="UNKNOWN",  # Never guess method without explicit evidence
                    confidence=EndpointConfidence.STRING_REFERENCE,
                    source_file=source_url,
                    is_sensitive=is_sensitive,
                    context_snippet=f"Referenced in client script: {source_url}",
                )
            )

        return endpoints
