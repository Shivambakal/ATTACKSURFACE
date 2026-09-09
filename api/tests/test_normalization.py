"""Tests for the raw observation normalization engine."""
import pytest
from app.services.normalization import (
    normalize_url,
    normalize_html_content,
    strip_text_noise,
)


def test_url_normalization_strips_tracking_retains_functional():
    raw = "HTTPS://Example.COM:443/docs/api/?utm_source=twitter&id=42&fbclid=xyz&category=auth#section-1"
    norm = normalize_url(raw)

    assert norm.scheme == "https"
    assert norm.domain == "example.com"
    assert norm.path == "/docs/api"
    # Functional param retained
    assert "id" in norm.functional_params
    assert norm.functional_params["id"] == ["42"]
    assert "category" in norm.functional_params
    # Tracking params stripped
    assert "utm_source" in norm.stripped_params
    assert "fbclid" in norm.stripped_params
    # Canonical URL clean
    assert norm.canonical_url == "https://example.com/docs/api?category=auth&id=42"


def test_noise_stripping_ignores_copyright_year_change():
    html_2025 = """
    <html>
      <head><title>Acme Portal</title></head>
      <body>
        <h1>Welcome to Acme</h1>
        <p>Manage your cloud resources and deployments.</p>
        <footer>
          <p>© 2025 Acme Corp. All rights reserved. Last updated 2025-01-01.</p>
        </footer>
      </body>
    </html>
    """

    html_2026 = """
    <html>
      <head><title>Acme Portal</title></head>
      <body>
        <h1>Welcome to Acme</h1>
        <p>Manage your cloud resources and deployments.</p>
        <footer>
          <p>© 2026 Acme Corp. All rights reserved. Last updated 2026-09-04.</p>
        </footer>
      </body>
    </html>
    """

    norm_2025 = normalize_html_content(html_2025, "https://acme.test/")
    norm_2026 = normalize_html_content(html_2026, "https://acme.test/")

    # Clean body text and content hash must match despite copyright / timestamp delta
    assert norm_2025.content_hash == norm_2026.content_hash
    assert norm_2025.structural_hash == norm_2026.structural_hash


def test_normalization_extracts_forms_and_auth_hooks():
    html = """
    <html>
      <head><title>Login & Auth</title></head>
      <body>
        <h2>Authentication</h2>
        <form action="/login" method="POST">
          <input type="hidden" name="csrf_token" value="ephemeral_nonce_12345" />
          <input type="text" name="username" required />
          <input type="password" name="password" required />
          <button type="submit">Sign In</button>
        </form>
        <a href="/auth/google/callback">Sign in with Google OAuth</a>
      </body>
    </html>
    """

    norm = normalize_html_content(html, "https://acme.test/login")

    assert len(norm.forms) == 1
    assert norm.forms[0]["action"] == "/login"
    assert norm.forms[0]["method"] == "POST"
    # Inputs extracted, csrf_token ignored
    input_names = [i["name"] for i in norm.forms[0]["inputs"]]
    assert "username" in input_names
    assert "password" in input_names
    assert "csrf_token" not in input_names
    # Auth indicators present
    assert any("auth_form" in a for a in norm.auth_indicators)
    assert any("oauth" in a.lower() for a in norm.auth_indicators)


def test_normalization_detects_api_endpoints_and_file_upload():
    html = """
    <html>
      <body>
        <h1>API Documentation</h1>
        <p>Query GET /v2/users/export to download user archives.</p>
        <form action="/upload" method="POST" enctype="multipart/form-data">
          <input type="file" name="avatar_file" />
        </form>
      </body>
    </html>
    """

    norm = normalize_html_content(html, "https://acme.test/docs")

    assert "/v2/users/export" in norm.api_endpoints
    assert any("file_upload" in cap for cap in norm.sensitive_capabilities)
