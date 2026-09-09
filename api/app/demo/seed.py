"""Synthetic demo data seed script for AttackSurface Timeline.

Creates complete, realistic demonstration data for "Acme Cloud":
- Demo user: demo@attacksurface.local
- Target: acmecloud.example.com
- Assets: Web App, API, Admin Panel, Mobile API
- Technologies: React 18, Node.js 20, PostgreSQL 15, nginx 1.25
- Features: OAuth SSO, REST API v2, Admin Dashboard, Webhook Integration
- Changes: New API endpoint, Auth change, Technology upgrade, New feature
- Evidence records with SHA-256 provenance hashes
- Timeline events with security priorities
- Research tasks and investigative notes
- Correlated security advisories and in-app alerts

ALL records are clearly marked with [DEMO DATA] in descriptions and summaries.
"""
from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models.base import utcnow
from app.models import (
    User,
    UserProfile,
    Target,
    Snapshot,
    Observation,
    Asset,
    Technology,
    AssetTechnology,
    Feature,
    FeatureObservation,
    Change,
    ChangeEvidence,
    Evidence,
    TimelineEvent,
    ResearchTask,
    ResearchNote,
    SecurityEvent,
    Alert,
    ResearchSignal,
    ResearchSignalFeedback,
    ChangeCluster,
    ApiSurface,
)
from app.services.auth import hash_password

logger = logging.getLogger(__name__)


def seed_demo_data(db: Session) -> dict[str, Any]:
    """Seed synthetic demonstration data for Acme Cloud into the database.

    Idempotent: cleans up previous demo data for demo@attacksurface.local
    and acmecloud.example.com before inserting fresh, cohesive records.
    """
    logger.info("Starting demo data seeding for Acme Cloud")
    now = utcnow()

    # ── 1. Clean up existing demo data to ensure idempotency ──────────
    existing_target = (
        db.query(Target).filter(Target.domain == "acmecloud.example.com").first()
    )
    if existing_target:
        # Delete dependent child tables first
        snap_ids = [s.id for s in db.query(Snapshot.id).filter(Snapshot.target_id == existing_target.id).all()]
        if snap_ids:
            db.query(Observation).filter(Observation.snapshot_id.in_(snap_ids)).delete(synchronize_session=False)
            db.query(FeatureObservation).filter(FeatureObservation.snapshot_id.in_(snap_ids)).delete(synchronize_session=False)
        change_ids = [c.id for c in db.query(Change.id).filter(Change.target_id == existing_target.id).all()]
        if change_ids:
            db.query(ChangeEvidence).filter(ChangeEvidence.change_id.in_(change_ids)).delete(synchronize_session=False)
        asset_ids = [a.id for a in db.query(Asset.id).filter(Asset.target_id == existing_target.id).all()]
        # Delete dependent research signals, clusters, api surfaces, tasks, notes, alerts
        sig_ids = [s.id for s in db.query(ResearchSignal.id).filter(ResearchSignal.target_id == existing_target.id).all()]
        if sig_ids:
            db.query(ResearchSignalFeedback).filter(ResearchSignalFeedback.signal_id.in_(sig_ids)).delete(synchronize_session=False)
        db.query(ResearchSignal).filter(ResearchSignal.target_id == existing_target.id).delete(synchronize_session=False)
        db.query(ChangeCluster).filter(ChangeCluster.target_id == existing_target.id).delete(synchronize_session=False)
        db.query(ApiSurface).filter(ApiSurface.target_id == existing_target.id).delete(synchronize_session=False)
        db.query(ResearchTask).filter(ResearchTask.target_id == existing_target.id).delete(synchronize_session=False)
        db.query(ResearchNote).filter(ResearchNote.target_id == existing_target.id).delete(synchronize_session=False)
        db.query(SecurityEvent).filter(SecurityEvent.target_id == existing_target.id).delete(synchronize_session=False)
        db.query(TimelineEvent).filter(TimelineEvent.target_id == existing_target.id).delete(synchronize_session=False)
        db.query(Evidence).filter(Evidence.target_id == existing_target.id).delete(synchronize_session=False)
        db.query(Change).filter(Change.target_id == existing_target.id).delete(synchronize_session=False)
        db.query(Feature).filter(Feature.target_id == existing_target.id).delete(synchronize_session=False)
        db.query(Asset).filter(Asset.target_id == existing_target.id).delete(synchronize_session=False)
        db.query(Snapshot).filter(Snapshot.target_id == existing_target.id).delete(synchronize_session=False)
        db.delete(existing_target)
        db.flush()

    demo_user = (
        db.query(User).filter(User.email == "demo@attacksurface.local").first()
    )
    if demo_user:
        db.query(Alert).filter(Alert.user_id == demo_user.id).delete(synchronize_session=False)
        db.delete(demo_user)
        db.flush()

    # ── 2. Create Demo User & Profile ─────────────────────────────────
    user = User(
        email="demo@attacksurface.local",
        password_hash=hash_password("DemoHunter2026!"),
        is_active=True,
        is_verified=True,
        created_at=now - timedelta(days=30),
    )
    db.add(user)
    db.flush()

    profile = UserProfile(
        user_id=user.id,
        display_name="Acme Bounty Hunter [DEMO]",
        username="acme_researcher",
        avatar_url="https://avatars.example.com/demo_researcher.png",
        bio="[DEMO DATA] Authorized security researcher tracking the Acme Cloud external attack surface.",
        country="USA",
        timezone="UTC",
        language="en",
        researcher_type="Bug Bounty Hunter",
        experience_level="Expert",
        favorite_vuln_classes=["BOLA", "Authentication Bypass", "SSRF", "Information Disclosure"],
        favorite_technologies=["React", "Node.js", "PostgreSQL", "nginx", "OAuth 2.0"],
        public_profile=True,
        created_at=now - timedelta(days=30),
    )
    db.add(profile)
    db.flush()

    # ── 3. Create Target ───────────────────────────────────────────────
    target = Target(
        user_id=user.id,
        domain="acmecloud.example.com",
        authorization_confirmed=True,
        monitoring_status="active",
        created_at=now - timedelta(days=14),
        updated_at=now,
        last_visited_at=now,
    )
    db.add(target)
    db.flush()

    # ── 4. Create Assets ───────────────────────────────────────────────
    asset_webapp = Asset(
        target_id=target.id,
        name="Acme Web App",
        url="https://acmecloud.example.com",
        asset_type="web_app",
        status="active",
        confidence=0.98,
        first_observed=now - timedelta(days=14),
        last_observed=now,
    )
    asset_webapp.metadata = {
        "description": "[DEMO DATA] Primary customer portal offering cloud management and SaaS dashboards.",
        "ip_addresses": ["198.51.100.12", "198.51.100.13"],
        "cdn": "Cloudflare",
    }
    db.add(asset_webapp)

    asset_api = Asset(
        target_id=target.id,
        name="Acme REST API",
        url="https://api.acmecloud.example.com",
        asset_type="api",
        status="active",
        confidence=0.95,
        first_observed=now - timedelta(days=14),
        last_observed=now,
    )
    asset_api.metadata = {
        "description": "[DEMO DATA] Public REST API gateway powering developer integrations and SaaS clients.",
        "api_versions": ["v1", "v2"],
    }
    db.add(asset_api)

    asset_admin = Asset(
        target_id=target.id,
        name="Acme Admin Panel",
        url="https://admin.acmecloud.example.com",
        asset_type="admin_panel",
        status="active",
        confidence=0.92,
        first_observed=now - timedelta(days=5),
        last_observed=now,
    )
    asset_admin.metadata = {
        "description": "[DEMO DATA] Internal administration dashboard for employee tenant management.",
        "restricted": True,
        "auth_method": "OAuth SSO + MFA",
    }
    db.add(asset_admin)

    asset_mobile_api = Asset(
        target_id=target.id,
        name="Acme Mobile API",
        url="https://mobile-api.acmecloud.example.com",
        asset_type="mobile_api",
        status="active",
        confidence=0.90,
        first_observed=now - timedelta(days=10),
        last_observed=now,
    )
    asset_mobile_api.metadata = {
        "description": "[DEMO DATA] Dedicated backend gateway for Acme iOS and Android native apps.",
        "protocol": "HTTPS/JSON",
    }
    db.add(asset_mobile_api)
    db.flush()

    # ── 5. Create Technologies ─────────────────────────────────────────
    tech_react = Technology(
        name="React",
        version="18.2.0",
        category="frontend",
        first_observed=now - timedelta(days=14),
        last_observed=now,
    )
    tech_nodejs = Technology(
        name="Node.js",
        version="20.11.0",
        category="runtime",
        first_observed=now - timedelta(days=14),
        last_observed=now,
    )
    tech_postgres = Technology(
        name="PostgreSQL",
        version="15.6",
        category="database",
        first_observed=now - timedelta(days=14),
        last_observed=now,
    )
    tech_nginx = Technology(
        name="nginx",
        version="1.25.4",
        category="web_server",
        first_observed=now - timedelta(days=2),
        last_observed=now,
    )
    db.add_all([tech_react, tech_nodejs, tech_postgres, tech_nginx])
    db.flush()

    # Link technologies to assets
    db.add_all([
        AssetTechnology(asset_id=asset_webapp.id, technology_id=tech_react.id, detected_at=now - timedelta(days=14)),
        AssetTechnology(asset_id=asset_webapp.id, technology_id=tech_nginx.id, detected_at=now - timedelta(days=2)),
        AssetTechnology(asset_id=asset_api.id, technology_id=tech_nodejs.id, detected_at=now - timedelta(days=14)),
        AssetTechnology(asset_id=asset_api.id, technology_id=tech_postgres.id, detected_at=now - timedelta(days=14)),
        AssetTechnology(asset_id=asset_admin.id, technology_id=tech_react.id, detected_at=now - timedelta(days=5)),
        AssetTechnology(asset_id=asset_admin.id, technology_id=tech_nodejs.id, detected_at=now - timedelta(days=5)),
        AssetTechnology(asset_id=asset_mobile_api.id, technology_id=tech_nodejs.id, detected_at=now - timedelta(days=10)),
    ])
    db.flush()

    # ── 6. Create Features ─────────────────────────────────────────────
    feat_oauth = Feature(
        target_id=target.id,
        name="OAuth SSO",
        description="[DEMO DATA] Single Sign-On integration supporting OAuth 2.0 PKCE and OpenID Connect.",
        status="ACTIVE",
        confidence=0.96,
        affected_assets=[asset_webapp.id, asset_admin.id],
        first_observed=now - timedelta(days=7),
        last_observed=now,
    )
    feat_api_v2 = Feature(
        target_id=target.id,
        name="REST API v2",
        description="[DEMO DATA] Comprehensive API v2 with enhanced resource scoping and rate limiting.",
        status="ACTIVE",
        confidence=0.95,
        affected_assets=[asset_api.id],
        first_observed=now - timedelta(days=4),
        last_observed=now,
    )
    feat_admin_dash = Feature(
        target_id=target.id,
        name="Admin Dashboard",
        description="[DEMO DATA] Centralized administrative portal for account tier management and audit log review.",
        status="NEW",
        confidence=0.92,
        affected_assets=[asset_admin.id],
        first_observed=now - timedelta(days=5),
        last_observed=now,
    )
    feat_webhook = Feature(
        target_id=target.id,
        name="Webhook Integration",
        description="[DEMO DATA] Customer webhook event streaming with HMAC-SHA256 signature verification.",
        status="ACTIVE",
        confidence=0.88,
        affected_assets=[asset_api.id],
        first_observed=now - timedelta(days=2),
        last_observed=now,
    )
    db.add_all([feat_oauth, feat_api_v2, feat_admin_dash, feat_webhook])
    db.flush()

    # ── 7. Create Snapshots & Observations ─────────────────────────────
    # Snapshot 1: Baseline (7 days ago)
    snap1 = Snapshot(
        target_id=target.id,
        collected_at=now - timedelta(days=7),
        status="complete",
    )
    db.add(snap1)
    db.flush()

    obs1_web = Observation(
        snapshot_id=snap1.id,
        url="https://acmecloud.example.com",
        kind="page",
        status_code=200,
        title="Acme Cloud — Cloud Management Platform [DEMO DATA]",
        content_hash=hashlib.sha256(b"acme_web_baseline_v1_demo").hexdigest(),
        text_excerpt="[DEMO DATA] Welcome to Acme Cloud Platform. Manage your virtual infrastructure and Kubernetes clusters.",
        technologies=["React", "nginx/1.24.0"],
        headers={"server": "nginx/1.24.0", "content-type": "text/html; charset=utf-8"},
        observed_at=now - timedelta(days=7),
    )
    obs1_api = Observation(
        snapshot_id=snap1.id,
        url="https://api.acmecloud.example.com/v1/docs",
        kind="page",
        status_code=200,
        title="Acme Cloud API Documentation v1 [DEMO DATA]",
        content_hash=hashlib.sha256(b"acme_api_baseline_v1_demo").hexdigest(),
        text_excerpt="[DEMO DATA] Acme Cloud REST API v1. Endpoints for /instances, /volumes, and /billing.",
        technologies=["Node.js", "Express"],
        headers={"server": "nginx/1.24.0", "x-powered-by": "Express"},
        observed_at=now - timedelta(days=7),
    )
    db.add_all([obs1_web, obs1_api])

    # Snapshot 2: Current / Recent (1 day ago)
    snap2 = Snapshot(
        target_id=target.id,
        collected_at=now - timedelta(days=1),
        status="complete",
    )
    db.add(snap2)
    db.flush()

    obs2_web = Observation(
        snapshot_id=snap2.id,
        url="https://acmecloud.example.com",
        kind="page",
        status_code=200,
        title="Acme Cloud — Cloud Management Platform [DEMO DATA]",
        content_hash=hashlib.sha256(b"acme_web_baseline_v2_demo").hexdigest(),
        text_excerpt="[DEMO DATA] Welcome to Acme Cloud Platform. Login with Google Workspace or GitHub Enterprise OAuth.",
        technologies=["React", "nginx/1.25.4"],
        headers={"server": "nginx/1.25.4", "content-type": "text/html; charset=utf-8"},
        observed_at=now - timedelta(days=1),
    )
    obs2_api_v2 = Observation(
        snapshot_id=snap2.id,
        url="https://api.acmecloud.example.com/v2/users/export",
        kind="page",
        status_code=200,
        title="Acme Cloud User Export API v2 [DEMO DATA]",
        content_hash=hashlib.sha256(b"acme_api_v2_users_export_demo").hexdigest(),
        text_excerpt="[DEMO DATA] GET /v2/users/export - Bulk export organization user profiles in JSON and CSV format.",
        technologies=["Node.js", "Express", "nginx/1.25.4"],
        headers={"server": "nginx/1.25.4", "content-type": "application/json"},
        observed_at=now - timedelta(days=1),
    )
    obs2_admin = Observation(
        snapshot_id=snap2.id,
        url="https://admin.acmecloud.example.com",
        kind="page",
        status_code=200,
        title="Acme Cloud Internal Admin Portal [DEMO DATA]",
        content_hash=hashlib.sha256(b"acme_admin_portal_observed_demo").hexdigest(),
        text_excerpt="[DEMO DATA] Acme Internal Staff Administration. Single Sign-On with required security hardware key.",
        technologies=["React", "nginx/1.25.4"],
        headers={"server": "nginx/1.25.4", "content-security-policy": "default-src 'self'"},
        observed_at=now - timedelta(days=1),
    )
    obs2_auth = Observation(
        snapshot_id=snap2.id,
        url="https://acmecloud.example.com/auth/oauth/pkce",
        kind="page",
        status_code=200,
        title="Acme Cloud OAuth 2.0 PKCE Documentation [DEMO DATA]",
        content_hash=hashlib.sha256(b"acme_oauth_pkce_doc_demo").hexdigest(),
        text_excerpt="[DEMO DATA] Authorization Endpoint /oauth/authorize requires code_challenge and code_challenge_method=S256.",
        technologies=["React", "nginx/1.25.4"],
        headers={"server": "nginx/1.25.4"},
        observed_at=now - timedelta(days=1),
    )
    db.add_all([obs2_web, obs2_api_v2, obs2_admin, obs2_auth])
    db.flush()

    # Link feature observations
    db.add_all([
        FeatureObservation(feature_id=feat_oauth.id, snapshot_id=snap2.id, observed_at=now - timedelta(days=1)),
        FeatureObservation(feature_id=feat_api_v2.id, snapshot_id=snap2.id, observed_at=now - timedelta(days=1)),
        FeatureObservation(feature_id=feat_admin_dash.id, snapshot_id=snap2.id, observed_at=now - timedelta(days=1)),
    ])
    db.flush()

    # ── 8. Create Evidence Records ─────────────────────────────────────
    ev_api = Evidence(
        target_id=target.id,
        source="collector",
        source_url="https://api.acmecloud.example.com/v2/users/export",
        retrieved_at=now - timedelta(days=1),
        content_hash=obs2_api_v2.content_hash,
        evidence_type="new_api_documentation",
        excerpt="[DEMO DATA] GET /v2/users/export endpoint exposed in public API documentation with bulk data extraction parameters.",
    )
    ev_api.metadata = {"method": "GET", "status_code": 200, "documented_params": ["format", "since", "include_pii"]}

    ev_auth = Evidence(
        target_id=target.id,
        source="collector",
        source_url="https://acmecloud.example.com/auth/oauth/pkce",
        retrieved_at=now - timedelta(days=1),
        content_hash=obs2_auth.content_hash,
        evidence_type="authentication_documentation_change",
        excerpt="[DEMO DATA] Authentication documentation updated to require OAuth 2.0 PKCE flow with S256 code challenge.",
    )
    ev_auth.metadata = {"flow": "OAuth 2.0 PKCE", "code_challenge_methods": ["S256"]}

    ev_nginx = Evidence(
        target_id=target.id,
        source="collector",
        source_url="https://acmecloud.example.com",
        retrieved_at=now - timedelta(days=1),
        content_hash=obs2_web.content_hash,
        evidence_type="technology_change",
        excerpt="[DEMO DATA] HTTP response header 'server' changed from 'nginx/1.24.0' to 'nginx/1.25.4'.",
    )
    ev_nginx.metadata = {"old_version": "1.24.0", "new_version": "1.25.4", "header": "server"}

    ev_admin = Evidence(
        target_id=target.id,
        source="collector",
        source_url="https://admin.acmecloud.example.com",
        retrieved_at=now - timedelta(days=1),
        content_hash=obs2_admin.content_hash,
        evidence_type="new_public_page",
        excerpt="[DEMO DATA] Newly reachable subdomain admin.acmecloud.example.com hosting internal administrative authentication.",
    )
    ev_admin.metadata = {"subdomain": "admin.acmecloud.example.com", "page_title": "Acme Cloud Internal Admin Portal"}

    ev_cve = Evidence(
        target_id=target.id,
        source="nvd",
        source_url="https://nvd.nist.gov/vuln/detail/CVE-2023-44487",
        retrieved_at=now - timedelta(hours=12),
        content_hash=hashlib.sha256(b"nvd_cve_2023_44487_demo").hexdigest(),
        evidence_type="vulnerability",
        excerpt="[DEMO DATA] CVE-2023-44487 HTTP/2 Rapid Reset Denial of Service attack vulnerability affecting web servers.",
    )
    ev_cve.metadata = {"cve_id": "CVE-2023-44487", "cvss_score": 7.5, "severity": "HIGH"}

    db.add_all([ev_api, ev_auth, ev_nginx, ev_admin, ev_cve])
    db.flush()

    # ── 9. Create Changes & ChangeEvidence ─────────────────────────────
    # Change 1: New API Endpoint
    chg_api = Change(
        target_id=target.id,
        snapshot_id=snap2.id,
        fingerprint=hashlib.sha256(b"change_demo_api_users_export").hexdigest(),
        category="new_api_documentation",
        confidence=0.92,
        security_relevance=88,
        summary="[DEMO DATA] New public API endpoint exposed: /v2/users/export",
        researcher_note="[DEMO DATA] Verify object-level authorization (BOLA/IDOR) on export requests. Check if tenant isolation is strictly enforced when exporting organizational users.",
        source_url="https://api.acmecloud.example.com/v2/users/export",
        detected_at=now - timedelta(days=1),
        priority="HIGH",
        score_factors={"category_base": 80, "api_keyword_boost": 8},
    )
    db.add(chg_api)
    db.flush()
    db.add(
        ChangeEvidence(
            change_id=chg_api.id,
            state="after",
            observation_id=obs2_api_v2.id,
            payload={"url": "https://api.acmecloud.example.com/v2/users/export", "kind": "page_added", "status_code": 200},
        )
    )

    # Change 2: Auth Change
    chg_auth = Change(
        target_id=target.id,
        snapshot_id=snap2.id,
        fingerprint=hashlib.sha256(b"change_demo_auth_oauth_pkce").hexdigest(),
        category="authentication_documentation_change",
        confidence=0.95,
        security_relevance=92,
        summary="[DEMO DATA] Authentication flow updated with OAuth 2.0 PKCE support",
        researcher_note="[DEMO DATA] Audit the PKCE implementation. Test whether the server accepts plain code_challenge, validates state parameters, or permits redirect_uri wildcards.",
        source_url="https://acmecloud.example.com/auth/oauth/pkce",
        detected_at=now - timedelta(days=1),
        priority="CRITICAL",
        score_factors={"category_base": 75, "auth_keyword_boost": 10, "signal_AUTH_CHANGE": 7},
    )
    db.add(chg_auth)
    db.flush()
    db.add(
        ChangeEvidence(
            change_id=chg_auth.id,
            state="after",
            observation_id=obs2_auth.id,
            payload={"url": "https://acmecloud.example.com/auth/oauth/pkce", "kind": "page_added", "status_code": 200},
        )
    )

    # Change 3: Technology Upgrade
    chg_tech = Change(
        target_id=target.id,
        snapshot_id=snap2.id,
        fingerprint=hashlib.sha256(b"change_demo_nginx_upgrade").hexdigest(),
        category="technology_change",
        confidence=0.90,
        security_relevance=65,
        summary="[DEMO DATA] Web server upgraded from nginx 1.24.0 to nginx 1.25.4",
        researcher_note="[DEMO DATA] Review nginx HTTP/2 and HTTP/3 configuration directives, cipher suites, and default proxy header pass-throughs for CRLF injection vectors.",
        source_url="https://acmecloud.example.com",
        detected_at=now - timedelta(days=1),
        priority="MEDIUM",
        score_factors={"category_base": 55, "signal_TECHNOLOGY_CHANGE": 10},
    )
    db.add(chg_tech)
    db.flush()
    db.add(
        ChangeEvidence(
            change_id=chg_tech.id,
            state="after",
            observation_id=obs2_web.id,
            payload={"url": "https://acmecloud.example.com", "kind": "technology_changed", "technologies": ["React", "nginx/1.25.4"]},
        )
    )

    # Change 4: New Feature (Admin Dashboard)
    chg_feature = Change(
        target_id=target.id,
        snapshot_id=snap2.id,
        fingerprint=hashlib.sha256(b"change_demo_admin_dashboard_discovered").hexdigest(),
        category="new_public_page",
        confidence=0.88,
        security_relevance=85,
        summary="[DEMO DATA] Discovered new Administrative Portal at admin.acmecloud.example.com",
        researcher_note="[DEMO DATA] Investigate scope eligibility for admin subdomain. Verify session handling, IP whitelisting bypasses, and unauthorized role elevation.",
        source_url="https://admin.acmecloud.example.com",
        detected_at=now - timedelta(days=1),
        priority="HIGH",
        score_factors={"category_base": 45, "auth_keyword_boost": 10, "signal_NEW_ASSET": 18, "signal_NEW_FEATURE": 12},
    )
    db.add(chg_feature)
    db.flush()
    db.add(
        ChangeEvidence(
            change_id=chg_feature.id,
            state="after",
            observation_id=obs2_admin.id,
            payload={"url": "https://admin.acmecloud.example.com", "kind": "page_added", "status_code": 200},
        )
    )

    # ── 9.5 Create Change Clusters and API Surfaces ────────────────────
    cluster_auth = ChangeCluster(
        target_id=target.id,
        title="[DEMO DATA] Authentication & OAuth Surface Evolution (2 endpoints)",
        summary="[DEMO DATA] Deployed OAuth 2.0 PKCE authentication flow and updated admin portal login boundaries.",
        primary_category="new_auth_surface",
        change_ids=[chg_auth.id, chg_feature.id],
        affected_urls=["https://acmecloud.example.com/auth/oauth/pkce", "https://admin.acmecloud.example.com"],
        source_count=2,
        confidence=0.96,
        relevance_score=94,
        priority="CRITICAL",
        created_at=now - timedelta(days=1),
    )
    cluster_api = ChangeCluster(
        target_id=target.id,
        title="[DEMO DATA] REST API v2 Expansion (/v2/users/export)",
        summary="[DEMO DATA] Introduced bulk user export capability documented in public OpenAPI schemas.",
        primary_category="new_api_surface",
        change_ids=[chg_api.id],
        affected_urls=["https://api.acmecloud.example.com/v2/users/export"],
        source_count=1,
        confidence=0.92,
        relevance_score=88,
        priority="HIGH",
        created_at=now - timedelta(days=2),
    )
    db.add_all([cluster_auth, cluster_api])
    db.flush()

    api_surf = ApiSurface(
        target_id=target.id,
        method="GET",
        path="/v2/users/export",
        version="v2",
        auth_requirement="Bearer Token",
        parameters=["format", "tenant_id", "limit"],
        source="https://api.acmecloud.example.com/docs",
        confidence=0.95,
        status="ACTIVE",
    )
    db.add(api_surf)
    db.flush()

    # ── 9.6 Create Top Research Signals ────────────────────────────────
    signal1 = ResearchSignal(
        target_id=target.id,
        change_id=chg_auth.id,
        cluster_id=cluster_auth.id,
        title="[DEMO DATA] New OAuth 2.0 PKCE Authentication Surface",
        signal_type="NEW_AUTH_SURFACE",
        summary="[DEMO DATA] Authentication portal documentation specifies Proof Key for Code Exchange (PKCE) flow.",
        why_it_matters="[DEMO DATA] Introduces a new authorization code and token exchange boundary using PKCE. Changes how client applications authenticate users.",
        recommended_research_area="Review state validation parameters, open redirect vulnerabilities on callback URLs, and token exchange security.",
        relevance_score=94,
        confidence_score=96,
        security_context_score=85,
        priority="CRITICAL",
        status="interesting",
        historical_context={"profile": {"AUTHENTICATION": "MEDIUM", "AUTHORIZATION": "HIGH"}},
        affected_assets=["https://acmecloud.example.com/auth/oauth/pkce"],
        evidence_ids=[str(ev_auth.id)],
        source_count=2,
        created_at=now - timedelta(days=1),
    )
    signal2 = ResearchSignal(
        target_id=target.id,
        change_id=chg_api.id,
        cluster_id=cluster_api.id,
        title="[DEMO DATA] New Bulk Data Export Endpoint (/v2/users/export)",
        signal_type="NEW_API_SURFACE",
        summary="[DEMO DATA] User account export endpoint documented in public OpenAPI specifications.",
        why_it_matters="[DEMO DATA] Introduces an administrative user export endpoint capable of bulk sensitive data transmission.",
        recommended_research_area="Verify Broken Object Level Authorization (BOLA/IDOR) by supplying unauthorized tenant/user IDs via query parameters.",
        relevance_score=88,
        confidence_score=92,
        security_context_score=80,
        priority="HIGH",
        status="new",
        historical_context={"profile": {"AUTHORIZATION": "HIGH"}},
        affected_assets=["https://api.acmecloud.example.com/v2/users/export"],
        evidence_ids=[str(ev_api.id)],
        source_count=1,
        created_at=now - timedelta(days=2),
    )
    signal3 = ResearchSignal(
        target_id=target.id,
        change_id=chg_feature.id,
        cluster_id=cluster_auth.id,
        title="[DEMO DATA] Discovered Admin Portal (admin.acmecloud.example.com)",
        signal_type="NEW_ASSET",
        summary="[DEMO DATA] Discovered new Administrative Portal at admin.acmecloud.example.com during attack surface mapping.",
        why_it_matters="[DEMO DATA] Administrative control plane exposed to public ingress with privilege management surfaces.",
        recommended_research_area="Check authentication enforcement, IP whitelist bypasses via proxy headers (X-Forwarded-For), and session handling.",
        relevance_score=85,
        confidence_score=90,
        security_context_score=75,
        priority="HIGH",
        status="investigating",
        historical_context={"profile": {"AUTHORIZATION": "HIGH"}},
        affected_assets=["https://admin.acmecloud.example.com"],
        evidence_ids=[str(ev_admin.id)],
        source_count=1,
        created_at=now - timedelta(days=1),
    )
    db.add_all([signal1, signal2, signal3])
    db.flush()

    # ── 10. Create Timeline Events ─────────────────────────────────────
    timeline_events: list[TimelineEvent] = []

    evt1 = TimelineEvent(
        target_id=target.id,
        event_type="asset_discovered",
        title="[DEMO DATA] Discovered Admin Portal (admin.acmecloud.example.com)",
        summary="[DEMO DATA] Internal administration dashboard detected during attack surface discovery.",
        source="discovery",
        source_url="https://admin.acmecloud.example.com",
        observed_at=now - timedelta(days=5),
        confidence=0.95,
        relevance_score=85,
        priority="HIGH",
        affected_asset_ids=[asset_admin.id],
        evidence_ids=[ev_admin.id],
        related_change_ids=[chg_feature.id],
    )
    evt1.metadata = {"asset_type": "admin_panel", "demo": True}
    timeline_events.append(evt1)

    evt2 = TimelineEvent(
        target_id=target.id,
        event_type="api_endpoint_added",
        title="[DEMO DATA] New Endpoint: /v2/users/export",
        summary="[DEMO DATA] User account export endpoint documented in public OpenAPI specifications.",
        source="collector",
        source_url="https://api.acmecloud.example.com/v2/users/export",
        observed_at=now - timedelta(days=2),
        confidence=0.92,
        relevance_score=88,
        priority="HIGH",
        affected_asset_ids=[asset_api.id],
        evidence_ids=[ev_api.id],
        related_change_ids=[chg_api.id],
    )
    evt2.metadata = {"endpoint": "/v2/users/export", "method": "GET", "demo": True}
    timeline_events.append(evt2)

    evt3 = TimelineEvent(
        target_id=target.id,
        event_type="auth_flow_changed",
        title="[DEMO DATA] OAuth 2.0 PKCE Flow Introduced",
        summary="[DEMO DATA] Authentication portal documentation specifies Proof Key for Code Exchange (PKCE) flow.",
        source="collector",
        source_url="https://acmecloud.example.com/auth/oauth/pkce",
        observed_at=now - timedelta(days=1),
        confidence=0.96,
        relevance_score=92,
        priority="CRITICAL",
        affected_asset_ids=[asset_webapp.id, asset_admin.id],
        evidence_ids=[ev_auth.id],
        related_change_ids=[chg_auth.id],
    )
    evt3.metadata = {"standard": "RFC 7636", "code_challenge": "S256", "demo": True}
    timeline_events.append(evt3)

    evt4 = TimelineEvent(
        target_id=target.id,
        event_type="technology_updated",
        title="[DEMO DATA] nginx Updated to 1.25.4",
        summary="[DEMO DATA] Edge web server upgraded from nginx 1.24.0 to 1.25.4 across public ingress.",
        source="collector",
        source_url="https://acmecloud.example.com",
        observed_at=now - timedelta(days=1),
        confidence=0.90,
        relevance_score=65,
        priority="MEDIUM",
        affected_asset_ids=[asset_webapp.id],
        evidence_ids=[ev_nginx.id],
        related_change_ids=[chg_tech.id],
    )
    evt4.metadata = {"component": "nginx", "version": "1.25.4", "demo": True}
    timeline_events.append(evt4)

    evt5 = TimelineEvent(
        target_id=target.id,
        event_type="security_correlation",
        title="[DEMO DATA] Security Advisory: CVE-2023-44487 (HTTP/2 Rapid Reset)",
        summary="[DEMO DATA] Correlated high-severity CVE-2023-44487 with nginx HTTP/2 reverse proxy configuration.",
        source="nvd",
        source_url="https://nvd.nist.gov/vuln/detail/CVE-2023-44487",
        observed_at=now - timedelta(hours=12),
        confidence=0.95,
        relevance_score=85,
        priority="HIGH",
        affected_asset_ids=[asset_webapp.id, asset_api.id],
        evidence_ids=[ev_cve.id],
    )
    evt5.metadata = {"cve_id": "CVE-2023-44487", "cvss": 7.5, "demo": True}
    timeline_events.append(evt5)

    db.add_all(timeline_events)
    db.flush()

    # ── 11. Create Research Tasks & Notes ──────────────────────────────
    task1 = ResearchTask(
        user_id=user.id,
        target_id=target.id,
        title="[DEMO DATA] Investigate new admin panel",
        description="[DEMO DATA] Perform authorized scope verification on admin.acmecloud.example.com. Check authentication bypasses, MFA enforcement, and tenant isolation.",
        status="open",
        priority="HIGH",
        due_date=(now + timedelta(days=5)).date(),
        related_change_id=chg_feature.id,
        created_at=now - timedelta(days=1),
    )
    task2 = ResearchTask(
        user_id=user.id,
        target_id=target.id,
        title="[DEMO DATA] Review OAuth flow changes",
        description="[DEMO DATA] Audit the new OAuth 2.0 PKCE implementation for state validation, client_secret leakage in client code, and open redirect parameters.",
        status="open",
        priority="CRITICAL",
        due_date=(now + timedelta(days=3)).date(),
        related_change_id=chg_auth.id,
        created_at=now - timedelta(days=1),
    )
    db.add_all([task1, task2])

    note1 = ResearchNote(
        user_id=user.id,
        target_id=target.id,
        title="[DEMO DATA] Notes on /v2/users/export Authorization Checks",
        body="[DEMO DATA] Observed that export endpoint requires Authorization Bearer header. Need to test with a low-privilege organization token to see if cross-tenant data can be requested via tenant_id URL parameter.",
        tags=["BOLA", "API", "Authorization", "Demo"],
        linked_change_id=chg_api.id,
        linked_asset_id=asset_api.id,
        linked_evidence_id=ev_api.id,
        created_at=now - timedelta(hours=6),
    )
    db.add(note1)
    db.flush()

    # ── 12. Create Security Events ─────────────────────────────────────
    sec_event = SecurityEvent(
        target_id=target.id,
        cve_id="CVE-2023-44487",
        source="nvd",
        severity="HIGH",
        summary="[DEMO DATA] HTTP/2 Rapid Reset Attack (CVE-2023-44487) correlated with detected nginx reverse proxy.",
        published=now - timedelta(days=60),
        references=["https://nvd.nist.gov/vuln/detail/CVE-2023-44487", "https://cve.org/CVERecord?id=CVE-2023-44487"],
    )
    sec_event.metadata = {"cvss_score": 7.5, "cwe": "CWE-400", "demo": True}
    db.add(sec_event)

    # ── 13. Create In-App Alerts ───────────────────────────────────────
    alert1 = Alert(
        user_id=user.id,
        alert_type="auth_flow_changed",
        entity_type="timeline_event",
        entity_id=evt3.id,
        title="[DEMO DATA] Critical Change: OAuth PKCE Flow Introduced",
        summary="[DEMO DATA] Acme Cloud deployed OAuth 2.0 PKCE. High security impact on authentication mechanisms.",
        priority="CRITICAL",
        read=False,
        created_at=now - timedelta(days=1),
    )
    alert2 = Alert(
        user_id=user.id,
        alert_type="api_endpoint_added",
        entity_type="timeline_event",
        entity_id=evt2.id,
        title="[DEMO DATA] High Priority: New User Export Endpoint",
        summary="[DEMO DATA] GET /v2/users/export observed in public API docs. Test for Broken Object Level Authorization (BOLA).",
        priority="HIGH",
        read=False,
        created_at=now - timedelta(days=1),
    )
    alert3 = Alert(
        user_id=user.id,
        alert_type="security_correlation",
        entity_type="timeline_event",
        entity_id=evt5.id,
        title="[DEMO DATA] Security Advisory: HTTP/2 Rapid Reset Correlated",
        summary="[DEMO DATA] CVE-2023-44487 correlated with Acme Cloud web server stack.",
        priority="HIGH",
        read=True,
        created_at=now - timedelta(hours=12),
    )
    db.add_all([alert1, alert2, alert3])

    # ── 14. Commit all records ─────────────────────────────────────────
    db.commit()

    logger.info(
        "Successfully seeded Acme Cloud demo data: target_id=%d, user_id=%d",
        target.id,
        user.id,
    )

    return {
        "status": "seeded",
        "user_id": user.id,
        "user_email": user.email,
        "target_id": target.id,
        "target_domain": target.domain,
        "assets_count": 4,
        "technologies_count": 4,
        "features_count": 4,
        "snapshots_count": 2,
        "observations_count": 6,
        "evidence_count": 5,
        "changes_count": 4,
        "timeline_events_count": len(timeline_events),
        "research_tasks_count": 2,
        "alerts_count": 3,
        "security_events_count": 1,
    }
