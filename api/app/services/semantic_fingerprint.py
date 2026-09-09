"""Semantic Fingerprinting & Artifact Unification Service.

Guarantees:
- Every attack-surface artifact (endpoint, parameter, route, capability) has a stable semantic identity.
- Immune to non-semantic churn: minification, bundle hash renames, variable renaming, formatting, source map changes.
- Unifies artifacts discovered across multiple collectors (AST, Browser, OpenAPI, GitHub, Docs) into 1 canonical artifact with multiple evidence references.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional, Sequence
from urllib.parse import urlparse


@dataclass
class SemanticArtifact:
    """A canonical, deduplicated attack-surface artifact."""
    artifact_id: str             # Stable SHA-256 semantic fingerprint
    artifact_type: str           # "API_ENDPOINT", "AUTH_SURFACE", "EXPORT_FUNCTION", etc.
    canonical_name: str          # e.g. "POST /api/v2/admin/impersonate"
    method: str | None = None    # e.g. "POST"
    path: str | None = None      # e.g. "/api/v2/admin/impersonate"
    parameters: list[str] = field(default_factory=list)
    auth_required: bool = True
    evidence_sources: list[str] = field(default_factory=list)
    discovered_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    raw_observations: list[dict[str, Any]] = field(default_factory=list)


class SemanticFingerprintService:
    """Computes stable semantic fingerprints and unifies artifacts."""

    @classmethod
    def normalize_path(cls, path: str) -> str:
        """Normalizes an API path by standardizing dynamic parameter syntax.

        Converts /users/123, /users/:id, /users/{id}, /users/<id> to /users/{param}
        so variable naming across documentation, OpenAPI, and code diffs matches identically.
        """
        if not path:
            return "/"

        # Strip query string and fragment if accidentally passed
        path = path.split("?")[0].split("#")[0].strip()

        # Remove leading/trailing redundant slashes
        segments = [s for s in path.split("/") if s]
        normalized_segments = []

        for seg in segments:
            # Matches {param}, :param, <param>, or pure integer IDs
            if (seg.startswith("{") and seg.endswith("}")) or seg.startswith(":") or (seg.startswith("<") and seg.endswith(">")) or seg.isdigit():
                normalized_segments.append("{param}")
            # Matches UUIDs / GUIDs
            elif re.match(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", seg, re.IGNORECASE):
                normalized_segments.append("{param}")
            # Matches hex hashes
            elif re.match(r"^[0-9a-f]{24,64}$", seg, re.IGNORECASE):
                normalized_segments.append("{param}")
            else:
                normalized_segments.append(seg.lower())

        return "/" + "/".join(normalized_segments)

    @classmethod
    def compute_endpoint_fingerprint(
        cls, method: str, raw_path: str, parameters: Optional[Sequence[str]] = None
    ) -> str:
        """Computes a stable SHA-256 fingerprint for an API endpoint.

        Immune to:
        - Bundle hash shifts (e.g. main.a8f9c1.js vs main.b7e2d4.js)
        - Parameter naming differences (:id vs {userId})
        - Minification and formatting
        """
        norm_method = (method or "GET").strip().upper()
        norm_path = cls.normalize_path(raw_path)

        payload = f"{norm_method}:{norm_path}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    @classmethod
    def unify_endpoint_observations(
        cls, observations: Sequence[dict[str, Any]]
    ) -> list[SemanticArtifact]:
        """Groups observations across AST, Browser, OpenAPI, GitHub into unified artifacts.

        Returns deduplicated SemanticArtifacts, each aggregating its evidence sources.
        """
        artifacts_by_id: dict[str, SemanticArtifact] = {}

        for obs in observations:
            method = obs.get("method", "GET").upper()
            path = obs.get("path") or urlparse(obs.get("url", "")).path or "/"
            params = obs.get("parameters") or []
            source = obs.get("source", "UNKNOWN")

            fp = cls.compute_endpoint_fingerprint(method, path, params)
            norm_path = cls.normalize_path(path)
            canonical_name = f"{method} {norm_path}"

            if fp not in artifacts_by_id:
                artifacts_by_id[fp] = SemanticArtifact(
                    artifact_id=fp,
                    artifact_type="API_ENDPOINT",
                    canonical_name=canonical_name,
                    method=method,
                    path=norm_path,
                    parameters=sorted(list(set(params))),
                    auth_required=obs.get("auth_required", True),
                    evidence_sources=[source],
                    raw_observations=[obs],
                )
            else:
                art = artifacts_by_id[fp]
                if source not in art.evidence_sources:
                    art.evidence_sources.append(source)
                # Merge parameters
                for p in params:
                    if p not in art.parameters:
                        art.parameters.append(p)
                art.raw_observations.append(obs)

        return list(artifacts_by_id.values())
