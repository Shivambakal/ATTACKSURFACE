"""Semantic classification engine for attack surface changes.

Classifies differential observations into actionable security categories,
extracting distinct feature and attack-surface signals while isolating noise.
"""
from __future__ import annotations

from .diffing import Diff, ChangeType


# High-value security keywords for lexical fallback
AUTH_KEYWORDS = ("oauth", "sso", "saml", "oidc", "login", "authenticate", "mfa", "passwordless", "session", "jwt", "bearer")
AUTHZ_KEYWORDS = ("role", "permission", "rbac", "acl", "admin", "privilege", "impersonate", "organization", "membership", "invite team")
API_KEYWORDS = ("api", "endpoint", "graphql", "rest", "swagger", "openapi", "webhook", "sdk")
SENSITIVE_CAP_KEYWORDS = ("file upload", "upload avatar", "bulk export", "export data", "download archive", "webhook", "api token", "secret key")


def classify(diff: Diff) -> tuple[str, float, str, str]:
    """Classify a diff into a standardized semantic category with confidence score and researcher guidance."""
    # 1. Noise check
    if diff.is_noise or diff.change_type == ChangeType.NOISE.value:
        return (
            "noise",
            0.99,
            f"Routine non-functional or ephemeral update observed at {diff.url}.",
            "Ephemeral or cosmetic change without security relevance; filtered from main timeline.",
        )

    # 2. Check rich delta details
    delta = diff.delta_details or {}
    auth_added = delta.get("auth_indicators_added", [])
    caps_added = delta.get("sensitive_capabilities_added", [])
    apis_added = delta.get("api_endpoints_added", [])
    form_inputs = delta.get("form_inputs_added", [])

    after_obj = diff.after
    title = getattr(after_obj, "title", "") or ""
    text_corpus = (
        f"{title} "
        f"{getattr(after_obj, 'clean_text', getattr(after_obj, 'text_excerpt', ''))} "
        f"{diff.url}"
    ).lower()

    # 3. Category Determination

    # A. Authentication boundary changes (OAuth, SSO, login forms, MFA)
    if auth_added or any(f":password" in inp for inp in form_inputs) or (
        diff.change_type == ChangeType.SECURITY_SENSITIVE.value and any(k in text_corpus for k in AUTH_KEYWORDS)
    ):
        category = "new_auth_surface"
        confidence = 0.94 if auth_added else 0.85
        summary = (
            f"New authentication surface observed at {diff.url} "
            f"({len(auth_added)} new auth indicators/hooks detected)."
            if auth_added
            else f"Authentication boundary update observed at {diff.url}."
        )
        note = (
            "Review the newly introduced authentication mechanism, token issuance flow, "
            "and callback parameters only within authorized scope; this is not a vulnerability finding."
        )

    # B. Authorization and access control changes (roles, permissions, invitations)
    elif any(k in text_corpus for k in AUTHZ_KEYWORDS) and (
        diff.change_type in (ChangeType.SECURITY_SENSITIVE.value, ChangeType.FUNCTIONAL.value)
    ):
        category = "new_authz_surface"
        confidence = 0.90
        summary = f"Authorization or role management surface detected at {diff.url}."
        note = (
            "Examine whether newly introduced user capabilities, role distinctions, "
            "or organization invitations enforce strict server-side authorization controls."
        )

    # C. Sensitive functional capabilities (file upload, bulk export, webhooks)
    elif caps_added or any(f":file" in inp for inp in form_inputs) or any(k in text_corpus for k in SENSITIVE_CAP_KEYWORDS):
        category = "sensitive_capability"
        confidence = 0.92 if caps_added else 0.80
        summary = f"Sensitive user capability (e.g., file handling or data export) detected at {diff.url}."
        note = (
            "Inspect input validation, file storage restrictions, and access boundaries "
            "governing this newly introduced workflow."
        )

    # D. New or changed API documentation and endpoints
    elif diff.kind == "new_api_documentation" or (
        diff.kind == "page_added" and any(k in text_corpus or k in diff.url.lower() for k in ("openapi", "swagger", "api"))
    ):
        category = "new_api_documentation"
        confidence = 0.90
        summary = f"New API documentation observed at {diff.url}."
        note = (
            "Review the documented public change, related access controls, and scope only if authorized; "
            "this is not a vulnerability finding."
        )

    elif apis_added or (diff.change_type == ChangeType.FUNCTIONAL.value and any(k in text_corpus for k in API_KEYWORDS)):
        category = "new_api_surface"
        confidence = 0.95 if apis_added else 0.90
        summary = (
            f"API attack surface expansion at {diff.url} ({len(apis_added)} endpoints documented: {', '.join(apis_added[:2])})."
            if apis_added
            else f"API attack surface expansion observed at {diff.url}."
        )
        note = (
            "Review the documented public change, related access controls, and scope only if authorized; "
            "this is not a vulnerability finding."
        )

    # E. Technology infrastructure changes
    elif diff.kind == "technology_changed" or diff.change_type == ChangeType.TECHNOLOGY.value:
        category = "technology_change"
        confidence = 0.92
        techs_added = delta.get("technologies_added", [])
        summary = (
            f"Technology infrastructure change observed at {diff.url}: {', '.join(techs_added)}"
            if techs_added
            else f"Technology stack modification observed at {diff.url}."
        )
        note = (
            "Verify whether technology versions have known public CVEs or advisories "
            "documented in OSV, CISA KEV, or NVD."
        )

    # F. External code repositories and package registries
    # CRITICAL: A public repository or external platform artifact is NEVER a "new_public_page" of the target company website.
    elif diff.kind == "repository":
        category = "repository_activity"
        confidence = 0.90
        summary = f"Verified repository activity observed at {diff.url}."
        note = "Official organization repository update; review commits, releases, and access control."

    elif diff.kind == "release":
        category = "software_release"
        confidence = 0.95
        summary = f"Software release observed at {diff.url}."
        note = "Official software release; inspect release notes and package artifacts."

    elif any(host in diff.url.lower() for host in ("github.com", "gitlab.com", "bitbucket.org", "npmjs.com", "pypi.org", "hub.docker.com", "crates.io")):
        category = "external_repository_reference"
        confidence = 0.30
        summary = f"External third-party reference observed at {diff.url}."
        note = "External third-party reference; unverified for corporate ownership and excluded from confirmed attack surface changes."

    # G. Added / Removed general pages (first-party canonical assets only)
    elif diff.kind == "page_added":
        category = "new_public_page"
        confidence = 0.85
        summary = f"New public page discovered at {diff.url}."
        note = "Explore newly exposed routes to map functionality and asset boundaries."

    elif diff.kind == "page_removed":
        category = "removed_public_page"
        confidence = 0.80
        summary = f"Public page removed or unreachable at {diff.url}."
        note = "Note endpoint decommissioning; verify that dependent APIs or references are safely retired."

    # H. Marketing or content updates
    elif diff.change_type == ChangeType.MARKETING.value:
        category = "marketing_content_change"
        confidence = 0.70
        summary = f"Marketing copy or page title updated at {diff.url}."
        note = "Informational content update with low security relevance."

    else:
        category = "public_content_change"
        confidence = 0.65
        summary = f"Public content update observed at {diff.url}."
        note = "Review documented public changes to identify functional evolutions."

    return category, confidence, summary, note

