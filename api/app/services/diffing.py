"""Content-aware difference engine.

Compares normalized snapshot observations across structural, functional,
security-sensitive, technology, marketing, and cosmetic dimensions.
Aggressively isolates and marks noise so it does not pollute the research timeline.
"""
from __future__ import annotations

import difflib
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .normalization import normalize_url, normalize_html_content, NormalizedContent


class ChangeType(str, Enum):
    SECURITY_SENSITIVE = "SECURITY_SENSITIVE"
    FUNCTIONAL = "FUNCTIONAL"
    STRUCTURAL = "STRUCTURAL"
    TECHNOLOGY = "TECHNOLOGY"
    MARKETING = "MARKETING"
    COSMETIC = "COSMETIC"
    TRACKING = "TRACKING"
    NOISE = "NOISE"


@dataclass(frozen=True)
class Diff:
    """Rich, content-aware differential result."""
    kind: str
    url: str
    before: object | None
    after: object | None
    change_type: str = ChangeType.FUNCTIONAL.value
    delta_details: dict[str, Any] = field(default_factory=dict)
    is_noise: bool = False
    text_diff: str = ""

    def __repr__(self) -> str:
        return f"<Diff kind={self.kind} type={self.change_type} is_noise={self.is_noise} url={self.url}>"


def _extract_norm_content(obj: object | None) -> NormalizedContent | None:
    """Safely extract or construct a NormalizedContent representation from an observation."""
    if obj is None:
        return None
    if isinstance(obj, NormalizedContent):
        return obj

    url = getattr(obj, "url", "")
    html = getattr(obj, "html", None)
    text = getattr(obj, "text_excerpt", "") or ""
    techs = getattr(obj, "technologies", []) or []
    headers = getattr(obj, "headers", {}) or {}

    if html:
        return normalize_html_content(html, url, technologies=techs, headers=headers)

    # Fallback when only raw observation attributes exist
    norm_url = normalize_url(url)
    return NormalizedContent(
        canonical_url=norm_url.canonical_url,
        title=getattr(obj, "title", None),
        clean_text=text,
        content_hash=getattr(obj, "content_hash", ""),
        structural_hash=getattr(obj, "structural_hash", getattr(obj, "content_hash", "")),
        forms=getattr(obj, "forms", []),
        auth_indicators=getattr(obj, "auth_indicators", []),
        api_endpoints=getattr(obj, "api_endpoints", []),
        sensitive_capabilities=getattr(obj, "sensitive_capabilities", []),
        technologies=techs,
        headers=headers,
    )


def analyze_observation_delta(old_obj: object, new_obj: object) -> Diff:
    """Perform deep structural and semantic delta analysis between two observations of the same URL."""
    url = getattr(new_obj, "url", getattr(old_obj, "url", ""))
    old_norm = _extract_norm_content(old_obj)
    new_norm = _extract_norm_content(new_obj)

    if not old_norm or not new_norm:
        return Diff("content_changed", url, old_obj, new_obj, change_type=ChangeType.FUNCTIONAL.value)

    # 1. Technology changes
    old_techs = set(old_norm.technologies)
    new_techs = set(new_norm.technologies)
    tech_diff = new_techs ^ old_techs

    # 2. Check for identical normalized content
    if old_norm.content_hash == new_norm.content_hash and not tech_diff:
        # Identical functional and clean content -> If hashes match, any raw variation is NOISE
        return Diff(
            kind="content_changed",
            url=url,
            before=old_obj,
            after=new_obj,
            change_type=ChangeType.NOISE.value,
            is_noise=True,
            delta_details={"reason": "clean_content_hash_identical_ephemeral_noise_only"},
        )

    delta_details: dict[str, Any] = {}

    # 3. Analyze Security-Sensitive changes
    old_auth = set(old_norm.auth_indicators)
    new_auth = set(new_norm.auth_indicators)
    auth_added = list(new_auth - old_auth)

    old_caps = set(old_norm.sensitive_capabilities)
    new_caps = set(new_norm.sensitive_capabilities)
    caps_added = list(new_caps - old_caps)

    # Check for new password or file upload inputs in forms
    old_form_inputs = {
        f"{f.get('action')}:{inp.get('name')}:{inp.get('type')}"
        for f in old_norm.forms
        for inp in f.get("inputs", [])
    }
    new_form_inputs = {
        f"{f.get('action')}:{inp.get('name')}:{inp.get('type')}"
        for f in new_norm.forms
        for inp in f.get("inputs", [])
    }
    inputs_added = list(new_form_inputs - old_form_inputs)
    has_new_security_inputs = any(
        ":password" in i or ":file" in i or "token" in i.lower() or "role" in i.lower()
        for i in inputs_added
    )

    if auth_added:
        delta_details["auth_indicators_added"] = auth_added
    if caps_added:
        delta_details["sensitive_capabilities_added"] = caps_added
    if inputs_added:
        delta_details["form_inputs_added"] = inputs_added

    is_security_sensitive = bool(auth_added or caps_added or has_new_security_inputs)

    # 4. Analyze API changes
    old_apis = set(old_norm.api_endpoints)
    new_apis = set(new_norm.api_endpoints)
    apis_added = list(new_apis - old_apis)
    if apis_added:
        delta_details["api_endpoints_added"] = apis_added

    # 5. Analyze Structural changes (forms, headings, DOM layout)
    old_forms = len(old_norm.forms)
    new_forms = len(new_norm.forms)
    headings_changed = old_norm.headings != new_norm.headings

    if old_forms != new_forms:
        delta_details["forms_count_delta"] = new_forms - old_forms

    # 6. Compute unified text diff for forensic view
    old_lines = old_norm.clean_text.splitlines()
    new_lines = new_norm.clean_text.splitlines()
    diff_generator = difflib.unified_diff(
        old_lines, new_lines, fromfile="before", tofile="current", lineterm="", n=2
    )
    unified_text_diff = "\n".join(list(diff_generator)[:100])

    # 7. Determine Primary ChangeType
    if is_security_sensitive:
        change_type = ChangeType.SECURITY_SENSITIVE.value
        kind = "security_sensitive_change"
    elif apis_added or old_forms != new_forms:
        change_type = ChangeType.FUNCTIONAL.value
        kind = "api_or_feature_change"
    elif tech_diff:
        change_type = ChangeType.TECHNOLOGY.value
        kind = "technology_changed"
        delta_details["technologies_added"] = list(new_techs - old_techs)
        delta_details["technologies_removed"] = list(old_techs - new_techs)
    elif headings_changed or old_norm.title != new_norm.title:
        change_type = ChangeType.MARKETING.value
        kind = "content_changed"
        delta_details["title_changed"] = old_norm.title != new_norm.title
    elif not unified_text_diff.strip():
        # No actual clean text difference exists
        change_type = ChangeType.NOISE.value
        kind = "content_changed"
        return Diff(kind, url, old_obj, new_obj, change_type=change_type, is_noise=True, delta_details={"reason": "empty_clean_diff"})
    else:
        change_type = ChangeType.CONTENT.value if hasattr(ChangeType, "CONTENT") else "CONTENT"
        kind = "content_changed"

    return Diff(
        kind=kind,
        url=url,
        before=old_obj,
        after=new_obj,
        change_type=change_type,
        delta_details=delta_details,
        is_noise=False,
        text_diff=unified_text_diff,
    )


def compare(before: list, after: list) -> list[Diff]:
    """Compare before and after observation collections with content-aware delta analysis."""
    # Index by normalized canonical URL
    old_map = {getattr(o, "url", ""): o for o in before}
    new_map = {getattr(o, "url", ""): o for o in after}

    output: list[Diff] = []

    # Removed URLs
    for url in old_map.keys() - new_map.keys():
        output.append(
            Diff(
                kind="page_removed",
                url=url,
                before=old_map[url],
                after=None,
                change_type=ChangeType.STRUCTURAL.value,
                is_noise=False,
                delta_details={"removed_url": url},
            )
        )

    # Added URLs
    for url in new_map.keys() - old_map.keys():
        new_obj = new_map[url]
        norm = _extract_norm_content(new_obj)
        is_sec = bool(norm and (norm.auth_indicators or norm.sensitive_capabilities))
        is_api = bool(norm and norm.api_endpoints)

        change_type = (
            ChangeType.SECURITY_SENSITIVE.value
            if is_sec
            else ChangeType.FUNCTIONAL.value
            if is_api
            else ChangeType.STRUCTURAL.value
        )
        kind = "new_api_documentation" if is_api else "page_added"

        output.append(
            Diff(
                kind=kind,
                url=url,
                before=None,
                after=new_obj,
                change_type=change_type,
                is_noise=False,
                delta_details={
                    "auth_indicators": norm.auth_indicators if norm else [],
                    "api_endpoints": norm.api_endpoints if norm else [],
                },
            )
        )

    # Common URLs (potential updates)
    for url in old_map.keys() & new_map.keys():
        diff = analyze_observation_delta(old_map[url], new_map[url])
        output.append(diff)

    return output
