"""Executable Intelligence Benchmark Test Suite (32 Scenarios).

Validates noise suppression, high-value attack surface detection,
clustering, multi-source corroboration, and citation grounding.
"""
import pytest
from app.services.normalization import (
    normalize_url,
    normalize_html_content,
    strip_text_noise,
)
from app.services.diffing import analyze_observation_delta, compare, Diff, ChangeType
from app.services.classification import classify
from app.services.scoring import score_detailed, ScoreResult
from app.services.feature_detection import (
    extract_features_from_observation,
    extract_api_endpoints_from_text,
)
from app.services.security_intelligence import (
    HistoricalSecurityProfile,
    correlate_with_historical_profile,
)
from app.services.clustering import cluster_changes, assign_visibility_tier, VisibilityTier
from app.services.ai_grounding import (
    validate_ai_citations,
    parse_and_validate_ai_response,
)
from app.services.target_safety import is_public_ip, validate_url_for_collection


# ── Scenario 1: Footer Copyright Year Change ─────────────────────────
def test_scenario_01_footer_copyright_noise():
    h1 = "<html><body><h1>Acme</h1><footer>© 2025 Acme Corp</footer></body></html>"
    h2 = "<html><body><h1>Acme</h1><footer>© 2026 Acme Corp</footer></body></html>"
    n1 = normalize_html_content(h1, "https://acme.test/")
    n2 = normalize_html_content(h2, "https://acme.test/")
    diff = analyze_observation_delta(n1, n2)
    assert diff.is_noise is True
    assert diff.change_type == "NOISE"
    cat, _, _, _ = classify(diff)
    assert cat == "noise"


# ── Scenario 2: Ephemeral CSRF Nonce in Form ─────────────────────────
def test_scenario_02_csrf_nonce_noise():
    h1 = '<form action="/login"><input type="hidden" name="csrf_token" value="nonce_aaa"><input type="text" name="u"></form>'
    h2 = '<form action="/login"><input type="hidden" name="csrf_token" value="nonce_bbb"><input type="text" name="u"></form>'
    n1 = normalize_html_content(h1, "https://acme.test/login")
    n2 = normalize_html_content(h2, "https://acme.test/login")
    assert n1.structural_hash == n2.structural_hash
    diff = analyze_observation_delta(n1, n2)
    assert diff.is_noise is True


# ── Scenario 3: Dynamic Timestamp in Header ──────────────────────────
def test_scenario_03_dynamic_timestamp_noise():
    h1 = "<p>Welcome to Acme. Last updated 2 hours ago.</p>"
    h2 = "<p>Welcome to Acme. Last updated 5 hours ago.</p>"
    n1 = normalize_html_content(h1, "https://acme.test/")
    n2 = normalize_html_content(h2, "https://acme.test/")
    assert n1.clean_text == n2.clean_text
    diff = analyze_observation_delta(n1, n2)
    assert diff.is_noise is True


# ── Scenario 4: Google Analytics Tracking Query ──────────────────────
def test_scenario_04_tracking_query_parameters():
    raw1 = "https://acme.test/docs?id=123"
    raw2 = "https://acme.test/docs?id=123&utm_source=twitter&fbclid=987&_ga=1.2.3"
    u1 = normalize_url(raw1)
    u2 = normalize_url(raw2)
    assert u1.canonical_url == u2.canonical_url
    assert "utm_source" in u2.stripped_params


# ── Scenario 5: OneTrust Cookie Consent Modal ────────────────────────
def test_scenario_05_cookie_banner_decomposition():
    h1 = "<div><h1>Products</h1></div>"
    h2 = "<div><h1>Products</h1><div class='onetrust-consent-sdk'>Cookie consent notice</div></div>"
    n1 = normalize_html_content(h1, "https://acme.test/")
    n2 = normalize_html_content(h2, "https://acme.test/")
    diff = analyze_observation_delta(n1, n2)
    assert diff.is_noise is True


# ── Scenario 6: Ephemeral Cache Buster in Asset ──────────────────────
def test_scenario_06_cache_buster_removal():
    u = normalize_url("https://acme.test/app.js?v=1725384000&_t=123")
    assert u.canonical_url == "https://acme.test/app.js"


# ── Scenario 7: Marketing Sale Announcement ──────────────────────────
def test_scenario_07_marketing_copy_change():
    h1 = "<html><body><h1>Acme Cloud</h1><p>Standard pricing applies.</p></body></html>"
    h2 = "<html><body><h1>Acme Cloud - Summer Sale</h1><p>Enjoy 50% discount this month.</p></body></html>"
    n1 = normalize_html_content(h1, "https://acme.test/")
    n2 = normalize_html_content(h2, "https://acme.test/")
    diff = analyze_observation_delta(n1, n2)
    cat, conf, _, _ = classify(diff)
    assert cat == "marketing_content_change"
    score_res = score_detailed(cat, "https://acme.test/")
    assert score_res.priority in ("LOW", "INFO")


# ── Scenario 8: Navigation Menu Item Reorder ─────────────────────────
def test_scenario_08_navigation_reorder_noise():
    h1 = "<html><body><nav><a href='/a'>A</a><a href='/b'>B</a></nav><h1>Body</h1></body></html>"
    h2 = "<html><body><nav><a href='/b'>B</a><a href='/a'>A</a></nav><h1>Body</h1></body></html>"
    n1 = normalize_html_content(h1, "https://acme.test/")
    n2 = normalize_html_content(h2, "https://acme.test/")
    diff = analyze_observation_delta(n1, n2)
    assert diff.is_noise is True


# ── Scenario 9: Privacy Policy Legal Disclaimer ──────────────────────
def test_scenario_09_legal_disclaimer_change():
    h1 = "<html><body><p>We process data in accordance with local regulations.</p></body></html>"
    h2 = "<html><body><p>We process customer data in accordance with updated European regulations.</p></body></html>"
    n1 = normalize_html_content(h1, "https://acme.test/legal")
    n2 = normalize_html_content(h2, "https://acme.test/legal")
    diff = analyze_observation_delta(n1, n2)
    cat, _, _, _ = classify(diff)
    assert cat in ("public_content_change", "marketing_content_change")


# ── Scenario 10: Blog Post Mentioning "OAuth" ────────────────────────
def test_scenario_10_blog_post_mentioning_oauth():
    h1 = "<html><body><h1>Blog</h1><p>Why we love reading about OAuth protocols and history.</p></body></html>"
    n1 = normalize_html_content(h1, "https://acme.test/blog/post-1")
    diff = Diff("page_added", "https://acme.test/blog/post-1", None, n1, change_type="STRUCTURAL")
    cat, _, _, _ = classify(diff)
    # Since there are no interactive OAuth forms or callback links, it is categorized as new_public_page
    assert cat == "new_public_page"
    score_res = score_detailed(cat, "https://acme.test/blog/post-1")
    assert score_res.priority in ("MEDIUM", "LOW")


# ── Scenario 11: New OAuth 2.0 PKCE Endpoint ─────────────────────────
def test_scenario_11_new_oauth_pkce_endpoint():
    h1 = "<html><body></body></html>"
    h2 = '<html><body><a href="/oauth/authorize?code_challenge=xyz&code_challenge_method=S256">Login with OAuth 2.0 PKCE</a></body></html>'
    n1 = normalize_html_content(h1, "https://acme.test/auth")
    n2 = normalize_html_content(h2, "https://acme.test/auth")
    diff = analyze_observation_delta(n1, n2)
    cat, conf, _, _ = classify(diff)
    assert cat == "new_auth_surface"
    score_res = score_detailed(cat, "https://acme.test/auth", signals=["AUTH_CHANGE", "NEW_SECURITY_SENSITIVE_FEATURE"])
    assert score_res.priority in ("CRITICAL", "HIGH")
    assert score_res.relevance_score >= 80


# ── Scenario 12: SAML / SSO Login Form Added ─────────────────────────
def test_scenario_12_saml_sso_login_form():
    h = '<html><body><form action="/sso/saml/consume" method="POST"><input type="password" name="saml_pwd"></form></body></html>'
    n = normalize_html_content(h, "https://acme.test/sso")
    diff = Diff("page_added", "https://acme.test/sso", None, n, change_type=ChangeType.SECURITY_SENSITIVE.value)
    cat, conf, _, _ = classify(diff)
    assert cat == "new_auth_surface"
    assert conf >= 0.85


# ── Scenario 13: Google & GitHub Social Login ────────────────────────
def test_scenario_13_social_login_indicators():
    h = '<html><body><button>Sign in with Google</button><button>Sign in with GitHub</button></body></html>'
    n = normalize_html_content(h, "https://acme.test/login")
    diff = Diff("security_sensitive_change", "https://acme.test/login", None, n, change_type="SECURITY_SENSITIVE", delta_details={"auth_indicators_added": ["auth_hook:google"]})
    cat, _, _, _ = classify(diff)
    assert cat == "new_auth_surface"


# ── Scenario 14: Multi-Factor Authentication (MFA) ───────────────────
def test_scenario_14_mfa_login_form():
    h = '<html><body><form action="/auth/mfa" method="POST"><input type="text" name="totp_token" required><input type="password" name="pwd"></form></body></html>'
    n = normalize_html_content(h, "https://acme.test/mfa")
    diff = Diff("page_added", "https://acme.test/mfa", None, n, change_type="SECURITY_SENSITIVE", delta_details={"auth_indicators_added": ["auth_form:/auth/mfa:POST"]})
    cat, _, _, _ = classify(diff)
    assert cat == "new_auth_surface"


# ── Scenario 15: Passwordless Magic Link Flow ────────────────────────
def test_scenario_15_passwordless_login():
    h = '<html><body><form action="/auth/magic-link" method="POST"><input type="email" name="user_email"><button>Send passwordless magic link</button></form></body></html>'
    n = normalize_html_content(h, "https://acme.test/magic")
    diff = Diff("security_sensitive_change", "https://acme.test/magic", None, n, change_type="SECURITY_SENSITIVE", delta_details={"auth_indicators_added": ["auth_hook:passwordless"]})
    cat, _, _, _ = classify(diff)
    assert cat == "new_auth_surface"


# ── Scenario 16: Team Member Invitation Workflow ─────────────────────
def test_scenario_16_team_invitation_workflow():
    h = '<html><body><button>Invite team member</button><input type="text" name="member_role"></body></html>'
    n = normalize_html_content(h, "https://acme.test/org/team")
    diff = Diff("security_sensitive_change", "https://acme.test/org/team", None, n, change_type="SECURITY_SENSITIVE")
    cat, _, _, _ = classify(diff)
    assert cat == "new_authz_surface"


# ── Scenario 17: RBAC Role Assignment Interface ──────────────────────
def test_scenario_17_rbac_role_assignment():
    h = '<html><body><h1>Organization Permissions</h1><select name="user_role"><option>Admin</option><option>Member</option></select></body></html>'
    n = normalize_html_content(h, "https://acme.test/roles")
    diff = Diff("security_sensitive_change", "https://acme.test/roles", None, n, change_type="SECURITY_SENSITIVE")
    cat, _, _, _ = classify(diff)
    assert cat == "new_authz_surface"


# ── Scenario 18: New OpenAPI Route /v2/users/export ──────────────────
def test_scenario_18_openapi_export_route():
    text = "GET /v2/users/export - Export all users in organization."
    extracted = extract_api_endpoints_from_text(text, "https://api.acme.test/docs")
    assert len(extracted) >= 1
    assert extracted[0].path == "/v2/users/export"
    assert extracted[0].method == "GET"


# ── Scenario 19: New GraphQL Query Endpoint ──────────────────────────
def test_scenario_19_graphql_endpoint_detection():
    h = '<html><body><p>Query our schema at POST /graphql</p></body></html>'
    n = normalize_html_content(h, "https://acme.test/developers")
    assert "/graphql" in n.api_endpoints
    diff = Diff("api_or_feature_change", "https://acme.test/developers", None, n, change_type="FUNCTIONAL", delta_details={"api_endpoints_added": ["/graphql"]})
    cat, _, _, _ = classify(diff)
    assert cat == "new_api_surface"


# ── Scenario 20: New Webhook Subscription System ─────────────────────
def test_scenario_20_webhook_configuration():
    h = '<html><body><h1>Webhooks</h1><input type="url" name="webhook_url"><input type="password" name="webhook_secret"></body></html>'
    n = normalize_html_content(h, "https://acme.test/webhooks")
    features = extract_features_from_observation(n)
    assert any(f.feature_type == "INTEGRATION" for f in features)


# ── Scenario 21: Arbitrary File Upload Form ──────────────────────────
def test_scenario_21_file_upload_form():
    h = '<html><body><form action="/upload" method="POST" enctype="multipart/form-data"><input type="file" name="doc_file"></form></body></html>'
    n = normalize_html_content(h, "https://acme.test/upload")
    diff = Diff("security_sensitive_change", "https://acme.test/upload", None, n, change_type="SECURITY_SENSITIVE", delta_details={"sensitive_capabilities_added": ["file_upload_field:doc_file"]})
    cat, _, _, _ = classify(diff)
    assert cat == "sensitive_capability"


# ── Scenario 22: Bulk Data Archive Download ──────────────────────────
def test_scenario_22_bulk_data_export():
    h = '<html><body><button>Bulk export all user data</button></body></html>'
    n = normalize_html_content(h, "https://acme.test/export")
    assert any("export" in cap for cap in n.sensitive_capabilities)


# ── Scenario 23: Personal Access Token Generator ─────────────────────
def test_scenario_23_api_token_generator():
    h = '<html><body><button>Generate Personal Access Token</button></body></html>'
    n = normalize_html_content(h, "https://acme.test/settings/tokens")
    features = extract_features_from_observation(n)
    assert any(f.feature_type == "CREDENTIAL_MANAGEMENT" for f in features)


# ── Scenario 24: Subdomain Discovered (admin.*) ──────────────────────
def test_scenario_24_admin_subdomain_discovered():
    score_res = score_detailed(
        category="new_public_page",
        source_url="https://admin.acme.test",
        text="Internal Administration Dashboard",
        signals=["NEW_ASSET", "NEW_SECURITY_SENSITIVE_FEATURE"],
        has_admin_capability=True,
    )
    assert score_res.priority in ("CRITICAL", "HIGH")
    assert score_res.relevance_score >= 75


# ── Scenario 25: Server Header Version Upgrade ───────────────────────
def test_scenario_25_technology_upgrade():
    diff = Diff("technology_changed", "https://acme.test", None, None, change_type="TECHNOLOGY", delta_details={"technologies_added": ["nginx/1.25.4"]})
    cat, _, _, _ = classify(diff)
    assert cat == "technology_change"
    score_res = score_detailed(cat, "https://acme.test", signals=["TECHNOLOGY_CHANGE"])
    assert score_res.priority in ("MEDIUM", "LOW")


# ── Scenario 26: Historical Auth Target Correlation ──────────────────
def test_scenario_26_historical_correlation_boost():
    profile = HistoricalSecurityProfile(
        target_id=1,
        total_security_events=2,
        total_findings=3,
        vulnerability_classes={"AUTHORIZATION": "HIGH"},
    )
    matches = correlate_with_historical_profile(profile, "new_authz_surface", ["Team Management"])
    assert len(matches) >= 1
    assert matches[0].vulnerability_class == "AUTHORIZATION"
    assert matches[0].relevance_boost >= 10


# ── Scenario 27: Multi-Source Coordinated Change ─────────────────────
def test_scenario_27_multi_source_confidence_boost():
    single_source = score_detailed("new_auth_surface", "https://acme.test/auth", confidence=0.85, source_count=1)
    multi_source = score_detailed("new_auth_surface", "https://acme.test/auth", confidence=0.85, source_count=3)
    assert multi_source.confidence_score > single_source.confidence_score
    assert multi_source.relevance_score > single_source.relevance_score


# ── Scenario 28: 15 Page Footer Updates in Release ───────────────────
def test_scenario_28_clustering_footer_updates():
    changes = [
        {"url": f"https://acme.test/page-{i}", "category": "noise", "security_relevance": 0, "confidence_score": 90, "is_noise": True}
        for i in range(15)
    ]
    clusters = cluster_changes(changes)
    # All 15 noise pages must be clustered together into 1 cluster
    assert len(clusters) == 1
    assert clusters[0].source_count == 15
    assert clusters[0].visibility_tier == VisibilityTier.INTERNAL_RAW.value


# ── Scenario 29: AI Citation Verification (Valid) ────────────────────
def test_scenario_29_valid_ai_citation():
    approved, rejected = validate_ai_citations(["101", "102"], ["101", "102", "103"])
    assert approved == ["101", "102"]
    assert rejected == []


# ── Scenario 30: AI Citation Hallucination Block ─────────────────────
def test_scenario_30_reject_hallucinated_ai_citation():
    approved, rejected = validate_ai_citations(["101", "999"], ["101"])
    assert approved == ["101"]
    assert rejected == ["999"]


# ── Scenario 31: Prompt Injection in Public HTML ─────────────────────
def test_scenario_31_prompt_injection_sanitization():
    raw_ai_payload = '{"title": "Bug", "category": "vulnerable", "summary": "System definitely vulnerable", "why_it_matters": "Critical exploit available", "research_area": "Exploit now", "confidence": 0.9, "evidence_ids": ["101"]}'
    res = parse_and_validate_ai_response(raw_ai_payload, valid_evidence_ids=["101"])
    assert "speculative_claim_defanged" in res.validation_warnings
    assert "definitely vulnerable" not in res.why_it_matters.lower()


# ── Scenario 32: SSRF Internal Range Target Block ────────────────────
def test_scenario_32_ssrf_protection_boundary():
    assert is_public_ip("169.254.169.254") is False
    assert is_public_ip("127.0.0.1") is False
    assert is_public_ip("10.0.0.1") is False
    assert is_public_ip("8.8.8.8") is True

    safe, reason = validate_url_for_collection("file:///etc/passwd")
    assert safe is False
