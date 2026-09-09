"""Raw observation normalization engine.

Performs robust URL canonicalization, parameter categorization,
DOM noise stripping, and structural feature decomposition prior to diffing.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse
from bs4 import BeautifulSoup, Comment

# Known non-functional tracking and ephemeral parameters
TRACKING_PARAMS: set[str] = {
    # Analytics & Campaigns
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "utm_id", "utm_reader", "utm_referrer", "fbclid", "gclid", "dclid",
    "msclkid", "twclid", "igshid", "mc_cid", "mc_eid", "yclid", "_ga", "_gl",
    "ref", "ref_src", "source", "affiliate", "promo",
    # Ephemeral / Cache-busting
    "_t", "t", "timestamp", "_", "nocache", "cb", "cache_buster", "v",
    "session_id", "sid", "nonce", "_csrf", "csrf_token",
}

# Regex patterns for stripping dynamic timestamps and dates
TIMESTAMP_PATTERNS = [
    re.compile(r"\b\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})\b"),
    re.compile(r"\b\d{4}-\d{2}-\d{2}\b"),
    re.compile(r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4}\b", re.IGNORECASE),
    re.compile(r"\b\d{1,2}\s+(?:hours?|days?|minutes?|seconds?|weeks?|months?|years?)\s+ago\b", re.IGNORECASE),
    re.compile(r"\b©\s*\d{4}(?:\s*-\s*\d{4})?\b"),
    re.compile(r"\bcopyright\s+\d{4}(?:\s*-\s*\d{4})?\b", re.IGNORECASE),
]

# Noise classes and IDs common in consent, marketing banners, and ads
NOISE_SELECTORS = [
    "nav", "footer", "header", "aside",
    ".cookie", ".cookie-banner", ".cookie-notice", ".cookie-consent",
    "#cookie-banner", "#cookie-notice", "#cookie-law",
    ".onetrust", "#onetrust-consent-sdk", ".onetrust-consent-sdk",
    ".gdpr", "#gdpr", ".cc-window", ".cc-banner",
    ".advertisement", ".ad-banner", ".adsbygoogle",
    ".social-share", ".share-buttons", ".newsletter-signup",
]


@dataclass
class NormalizedUrl:
    """Canonicalized URL preserving original representation and parameter analysis."""
    original_url: str
    canonical_url: str
    scheme: str
    domain: str
    path: str
    functional_params: dict[str, list[str]]
    stripped_params: dict[str, list[str]]


@dataclass
class NormalizedContent:
    """Decomposed, noise-reduced content structure."""
    canonical_url: str
    title: str | None
    headings: list[str] = field(default_factory=list)
    clean_text: str = ""
    content_hash: str = ""
    structural_hash: str = ""
    forms: list[dict] = field(default_factory=list)
    auth_indicators: list[str] = field(default_factory=list)
    api_endpoints: list[str] = field(default_factory=list)
    sensitive_capabilities: list[str] = field(default_factory=list)
    technologies: list[str] = field(default_factory=list)
    headers: dict[str, str] = field(default_factory=dict)
    metadata: dict = field(default_factory=dict)


def normalize_url(raw_url: str) -> NormalizedUrl:
    """Normalize and canonicalize a URL.

    - Lowercases scheme and hostname.
    - Strips port if standard (80/443).
    - Removes fragments.
    - Canonicalizes trailing slashes (preserves root /).
    - Strips tracking & cache-busting parameters while retaining functional parameters.
    - Sorts query parameters deterministically.
    """
    if not raw_url or not isinstance(raw_url, str):
        return NormalizedUrl(
            original_url="",
            canonical_url="",
            scheme="https",
            domain="",
            path="",
            functional_params={},
            stripped_params={},
        )

    parsed = urlparse(raw_url.strip())
    scheme = parsed.scheme.lower() or "https"
    netloc = parsed.netloc.lower()

    # Remove default ports
    if ":" in netloc:
        host, _, port = netloc.partition(":")
        if (scheme == "https" and port == "443") or (scheme == "http" and port == "80"):
            netloc = host

    # Normalize path: clean double slashes, strip trailing slash unless root
    path = re.sub(r"/+", "/", parsed.path)
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")
    if not path:
        path = "/"

    # Categorize query parameters
    query_dict = parse_qs(parsed.query, keep_blank_values=True)
    functional_params: dict[str, list[str]] = {}
    stripped_params: dict[str, list[str]] = {}

    for k, v in query_dict.items():
        k_lower = k.lower()
        if k_lower in TRACKING_PARAMS or k_lower.startswith(("utm_", "ref_")):
            stripped_params[k] = v
        else:
            functional_params[k] = v

    # Build canonical query string with sorted keys
    canonical_query = ""
    if functional_params:
        sorted_pairs = []
        for key in sorted(functional_params.keys()):
            for val in sorted(functional_params[key]):
                sorted_pairs.append((key, val))
        canonical_query = urlencode(sorted_pairs)

    canonical_url = urlunparse((scheme, netloc, path, "", canonical_query, ""))

    return NormalizedUrl(
        original_url=raw_url,
        canonical_url=canonical_url,
        scheme=scheme,
        domain=netloc,
        path=path,
        functional_params=functional_params,
        stripped_params=stripped_params,
    )


def strip_text_noise(text: str) -> str:
    """Remove dynamic timestamps, dates, and copyright noise from text."""
    cleaned = text
    for pattern in TIMESTAMP_PATTERNS:
        cleaned = pattern.sub(" ", cleaned)
    return re.sub(r"\s+", " ", cleaned).strip()


def normalize_html_content(
    html: str,
    url: str,
    technologies: list[str] | None = None,
    headers: dict[str, str] | None = None,
) -> NormalizedContent:
    """Deconstruct and normalize raw HTML into functional components.

    Extracts:
    - Cleaned title and headings
    - Functional interactive forms (action, method, inputs)
    - Authentication indicators (SSO, OAuth, login forms)
    - API endpoints & references
    - High-value sensitive capabilities (file upload, export, roles)
    - Deterministic structural and content hashes immune to copyright/timestamp noise.
    """
    norm_url = normalize_url(url)
    soup = BeautifulSoup(html or "", "html.parser")

    # 1. Remove non-functional nodes and comments
    for comment in soup.find_all(string=lambda t: isinstance(t, Comment)):
        comment.extract()

    for tag in soup(["script", "style", "noscript", "svg", "iframe"]):
        tag.decompose()

    # 2. Extract title before stripping navigation
    raw_title = soup.title.get_text(strip=True) if soup.title else None
    clean_title = strip_text_noise(raw_title) if raw_title else None

    # 3. Extract Headings (h1, h2, h3)
    headings: list[str] = []
    for h in soup.find_all(["h1", "h2", "h3"]):
        h_text = strip_text_noise(h.get_text(strip=True))
        if h_text and len(h_text) > 2 and h_text not in headings:
            headings.append(h_text[:120])

    # 4. Extract and analyze Forms before removing noise containers
    forms: list[dict] = []
    auth_indicators: list[str] = []
    sensitive_caps: list[str] = []

    for form in soup.find_all("form"):
        form_action = form.get("action", "") or norm_url.path
        form_method = form.get("method", "GET").upper()
        inputs: list[dict] = []

        is_auth_form = False
        is_upload_form = False

        for inp in form.find_all(["input", "select", "textarea"]):
            inp_type = inp.get("type", "text").lower()
            inp_name = inp.get("name", "")
            if not inp_name and inp.get("id"):
                inp_name = inp.get("id")

            # Ignore CSRF nonces and hidden session keys for structural comparison
            if inp_type == "hidden" and any(
                n in inp_name.lower() for n in ("csrf", "token", "_token", "nonce", "state")
            ):
                continue

            if inp_type == "password":
                is_auth_form = True
            if inp_type == "file":
                is_upload_form = True
                sensitive_caps.append(f"file_upload_field:{inp_name or 'unnamed'}")

            inputs.append({
                "name": inp_name,
                "type": inp_type,
                "required": inp.has_attr("required"),
            })

        if is_auth_form:
            auth_indicators.append(f"auth_form:{form_action}:{form_method}")

        forms.append({
            "action": form_action,
            "method": form_method,
            "inputs": sorted(inputs, key=lambda x: x.get("name", "")),
        })

    # 5. Extract Links, Buttons, and OAuth/SSO indicators
    for el in soup.find_all(["a", "button"]):
        text_content = el.get_text(strip=True).lower()
        href = (el.get("href") or "").lower()

        # Check for OAuth / SSO / Login hooks
        if any(kw in text_content or kw in href for kw in ("oauth", "sso", "saml", "oidc", "google login", "github login", "sign in with")):
            auth_indicators.append(f"auth_hook:{text_content[:40] or href[:40]}")

        # Check for sensitive capabilities
        if any(kw in text_content for kw in ("invite team", "add user", "role", "permissions", "api key", "create token", "webhook")):
            sensitive_caps.append(f"action_hook:{text_content[:40]}")
        if any(kw in text_content for kw in ("export users", "export data", "download report", "bulk export")):
            sensitive_caps.append(f"export_capability:{text_content[:40]}")

    # 6. Extract API routes and endpoint documentation in page
    api_endpoints: list[str] = []
    text_corpus = soup.get_text(" ", strip=True)
    api_patterns = [
        re.compile(r"(?:GET|POST|PUT|DELETE|PATCH)\s+([/][a-zA-Z0-9_\-/{}/.]+)"),
        re.compile(r"[\"'](/api/(?:v\d+/)?[a-zA-Z0-9_\-/{}/.]+)[\"']"),
        re.compile(r"(?:^|\s|[\"'])(/graphql(?:/[a-zA-Z0-9_\-]+)?)(?:\s|[\"']|$)"),
    ]
    for pat in api_patterns:
        matches = pat.findall(text_corpus)
        for m in matches:
            m_clean = m.strip()
            if m_clean and m_clean not in api_endpoints:
                api_endpoints.append(m_clean)

    # 7. Strip noise containers (nav, footer, cookie banners) for clean body text
    for selector in NOISE_SELECTORS:
        for node in soup.select(selector):
            node.decompose()

    raw_clean_text = soup.get_text(" ", strip=True)
    clean_text = strip_text_noise(raw_clean_text)

    # 8. Compute Structural Hash (combines forms, endpoints, auth, and sensitive capabilities)
    structural_summary = (
        f"TITLE:{clean_title or ''}|"
        f"HEADINGS:{','.join(headings)}|"
        f"FORMS:{len(forms)}|"
        f"AUTH:{','.join(sorted(set(auth_indicators)))}|"
        f"API:{','.join(sorted(set(api_endpoints)))}|"
        f"CAPS:{','.join(sorted(set(sensitive_caps)))}"
    )
    structural_hash = hashlib.sha256(structural_summary.encode()).hexdigest()

    # 9. Compute Clean Content Hash
    content_hash = hashlib.sha256(
        f"{structural_summary}|{clean_text[:10000]}".encode()
    ).hexdigest()

    return NormalizedContent(
        canonical_url=norm_url.canonical_url,
        title=clean_title,
        headings=headings,
        clean_text=clean_text[:12000],
        content_hash=content_hash,
        structural_hash=structural_hash,
        forms=forms,
        auth_indicators=sorted(set(auth_indicators)),
        api_endpoints=sorted(set(api_endpoints)),
        sensitive_capabilities=sorted(set(sensitive_caps)),
        technologies=sorted(set(technologies or [])),
        headers={k.lower(): v for k, v in (headers or {}).items() if k.lower() in ("server", "x-powered-by", "content-security-policy", "access-control-allow-origin")},
        metadata={
            "stripped_tracking_params": list(norm_url.stripped_params.keys()),
            "functional_params": list(norm_url.functional_params.keys()),
            "forms_count": len(forms),
            "auth_indicators_count": len(auth_indicators),
            "api_endpoints_count": len(api_endpoints),
        },
    )
