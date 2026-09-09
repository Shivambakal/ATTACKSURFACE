"""Comprehensive Test Suite for Security Intelligence Quality and Real-World Hardening.

Verifies:
1. Golden Scenarios (Cases 1 - 7)
2. Unified Evidence Graph & Source Fusion (Hierarchy, Convergence, Conflict Detection, Traceability)
3. Entity Resolution & Disambiguation (Aliases, Ambiguity Guards, Vendor != Company)
4. Semantic Fingerprinting & Multi-Source Artifact Unification
5. Historical Replay & Measurable Coverage Metrics
6. Temporal Scope Evaluation & Transparent Explanations
7. Signal Quality Analytics & Feedback Loop
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.base import Base
from app.models.company import Company
from app.models.product import Product
from app.models.asset import Asset
from app.models.security import SecurityEvent, SecurityRelationshipType
from app.models.security_program import ProgramScopeRule, InclusionType, ScopeStatus
from app.models.signal import ResearchSignal, ResearchSignalFeedback, FeedbackType, SignalStatus
from app.services.evidence_graph import (
    EvidenceSourceType,
    EvidenceStrength,
    EvidenceNode,
    EvidenceGraphService,
    ObservationState,
    STRENGTH_WEIGHTS,
)
from app.services.entity_resolution import (
    EntityResolutionService,
    EntityType,
)
from app.services.semantic_fingerprint import (
    SemanticFingerprintService,
)
from app.services.historical_replay import (
    HistoricalReplayService,
    EpochState,
)
from app.services.scope_resolver import (
    ScopeResolver,
    ScopeDecision,
)
from app.services.historical_reconstruction_service import (
    HistoricalReconstructionService,
)


@pytest.fixture
def memory_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()


# ==============================================================================
# 1. GOLDEN SCENARIOS (CASES 1 - 7)
# ==============================================================================

class TestGoldenScenarios:
    """Golden scenarios verifying real-world intelligence behaviors."""

    def test_case_1_technology_cve_is_context_only_never_vulnerable(self, memory_db):
        """CASE 1: Company uses technology X. X has CVE.

        Expected: RELATED_TECHNOLOGY_CONTEXT, never DIRECT_COMPANY_EVENT or claiming target is vulnerable.
        """
        company = Company(name="FinTech Corp", canonical_domain="fintech.example.com")
        memory_db.add(company)
        memory_db.flush()

        asset = Asset(company_id=company.id, name="app.fintech.example.com", hostname="app.fintech.example.com", asset_type="DOMAIN")
        memory_db.add(asset)
        memory_db.flush()

        # Record third-party technology CVE
        sec_event = SecurityEvent(
            company_id=company.id,
            asset_id=asset.id,
            cve_id="CVE-2021-44228",
            relationship_type=SecurityRelationshipType.RELATED_TECHNOLOGY_CONTEXT.value,
            vulnerability_class="INJECTION",
            summary="Apache Log4j JNDI remote code execution vulnerability.",
            source="CISA_KEV",
            confidence=0.85,
        )
        memory_db.add(sec_event)
        memory_db.commit()

        retrieved = memory_db.get(SecurityEvent, sec_event.id)
        assert retrieved.relationship_type == SecurityRelationshipType.RELATED_TECHNOLOGY_CONTEXT.value
        assert retrieved.relationship_type != SecurityRelationshipType.DIRECT_COMPANY_EVENT.value
        # Ensure company correlation requires explicit direct evidence
        is_direct, rationale = EntityResolutionService.assert_vendor_is_not_company(
            vendor_project="Apache", company_name=company.name, company_domain=company.canonical_domain
        )
        assert is_direct is False
        assert "third-party technology context" in rationale

    def test_case_2_official_company_advisory_is_direct_company_event(self, memory_db):
        """CASE 2: Company official advisory directly affects company product.

        Expected: DIRECT_COMPANY_EVENT with high confidence.
        """
        company = Company(name="Stripe", canonical_domain="stripe.com")
        memory_db.add(company)
        memory_db.flush()

        product = Product(company_id=company.id, name="Stripe CLI")
        memory_db.add(product)
        memory_db.flush()

        sec_event = SecurityEvent(
            company_id=company.id,
            product_id=product.id,
            cve_id="CVE-2023-XXXX",
            relationship_type=SecurityRelationshipType.DIRECT_COMPANY_EVENT.value,
            vulnerability_class="AUTHENTICATION",
            summary="Stripe CLI authentication token validation disclosure.",
            source="VENDOR_ADVISORY",
            source_url="https://stripe.com/docs/security/advisories",
            confidence=0.98,
        )
        memory_db.add(sec_event)
        memory_db.commit()

        retrieved = memory_db.get(SecurityEvent, sec_event.id)
        assert retrieved.relationship_type == SecurityRelationshipType.DIRECT_COMPANY_EVENT.value
        assert retrieved.confidence >= 0.95

    def test_case_3_new_admin_api_with_historical_access_control(self, memory_db):
        """CASE 3: New admin API detected + organization has historical access-control issues.

        Expected: HIGH contextual research relevance with non-speculative explanation.
        Never asserts 'IDOR confirmed'.
        """
        company = Company(name="Acme Corp", canonical_domain="acme.com")
        memory_db.add(company)
        memory_db.flush()

        # Prior historical access control event
        prior_event = SecurityEvent(
            company_id=company.id,
            cve_id="CVE-2022-1001",
            vulnerability_class="BROKEN ACCESS CONTROL",
            summary="Prior broken access control vulnerability in user administration.",
            relationship_type=SecurityRelationshipType.DIRECT_COMPANY_EVENT.value,
            source="PUBLIC_DISCLOSURE",
        )
        memory_db.add(prior_event)
        memory_db.commit()

        # Correlate current change
        res = HistoricalReconstructionService.correlate_historical_context(
            db=memory_db,
            company_id=company.id,
            current_title="POST /api/v2/admin/impersonate",
            current_summary="New administrative role impersonation endpoint added.",
        )

        assert res["has_historical_correlation"] is True
        assert "BROKEN ACCESS CONTROL" in res["matched_vulnerability_classes"][0]
        # Verify wording is non-speculative
        assert "Historical security context" in res["explanation"]
        assert "IDOR confirmed" not in res["explanation"]
        assert "vulnerable" not in res["explanation"].lower()

    def test_case_4_marketing_page_with_admin_word_no_high_signal(self, memory_db):
        """CASE 4: New marketing page containing the word 'admin' in narrative copy.

        Expected: Not classified as high security relevance.
        """
        company = Company(name="Acme Corp", canonical_domain="acme.com")
        memory_db.add(company)
        memory_db.commit()

        # Non-administrative content with passing mention of admin
        marketing_text = "Learn how our platform helps busy admin teams streamline workflows."
        res = HistoricalReconstructionService.correlate_historical_context(
            db=memory_db,
            company_id=company.id,
            current_title="Blog: Streamlining workflows for teams",
            current_summary=marketing_text,
        )
        # Without historical events matching or privileged endpoint patterns, no high correlation
        assert res["has_historical_correlation"] is False

    def test_case_5_github_commit_without_production_is_development_evidence(self):
        """CASE 5: GitHub commit adds a feature, but production does not observe it.

        Expected: Observation state is DEVELOPMENT_EVIDENCE, not OBSERVED or CONFIRMED.
        """
        node = EvidenceNode(
            source_type=EvidenceSourceType.GITHUB,
            strength=EvidenceStrength.OFFICIAL_GITHUB,
            source_url="https://github.com/acme/repo/commit/abc1234",
            evidence_text="feat(billing): add new crypto payment checkout",
            content_hash="hash_github_1",
            confidence=0.8,
        )

        fused = EvidenceGraphService.fuse_evidence(
            canonical_id="feature:crypto_checkout",
            evidence_nodes=[node],
            observed_in_production=False,
        )

        assert fused.observation_state == ObservationState.DEVELOPMENT_EVIDENCE
        assert fused.observation_state != ObservationState.CONFIRMED
        assert fused.observation_state != ObservationState.OBSERVED

    def test_case_6_docs_and_browser_corroborate_higher_confidence(self):
        """CASE 6: Documentation + Browser observation both verify new API.

        Expected: Multi-source convergence increases confidence, state is CONFIRMED.
        """
        doc_node = EvidenceNode(
            source_type=EvidenceSourceType.DOCUMENTATION,
            strength=EvidenceStrength.OFFICIAL_DOCUMENTATION,
            source_url="https://docs.acme.com/api/v2/webhooks",
            evidence_text="POST /v2/webhooks creates an asynchronous callback.",
            content_hash="hash_doc_1",
            confidence=0.85,
        )
        browser_node = EvidenceNode(
            source_type=EvidenceSourceType.BROWSER_OBSERVATION,
            strength=EvidenceStrength.DIRECT_PRODUCTION_OBSERVATION,
            source_url="https://app.acme.com/v2/webhooks",
            evidence_text="Observed HTTP 200 on /v2/webhooks endpoint.",
            content_hash="hash_browser_1",
            confidence=0.92,
        )

        fused = EvidenceGraphService.fuse_evidence(
            canonical_id="endpoint:POST:/v2/webhooks",
            evidence_nodes=[doc_node, browser_node],
            observed_in_production=True,
        )

        assert fused.observation_state == ObservationState.CONFIRMED
        # Convergence boost should be higher than single source
        assert fused.fused_confidence > browser_node.confidence
        assert fused.fused_confidence <= 0.98

    def test_case_7_conflicting_evidence_yields_documented_not_observed(self):
        """CASE 7: Docs specify an endpoint, but production browser check returns not found.

        Expected: DOCUMENTED_NOT_OBSERVED state with conflict notification.
        """
        doc_node = EvidenceNode(
            source_type=EvidenceSourceType.OPENAPI,
            strength=EvidenceStrength.OFFICIAL_DOCUMENTATION,
            source_url="https://api.acme.com/openapi.json",
            evidence_text="POST /api/v3/experimental/export",
            content_hash="hash_openapi_1",
            confidence=0.85,
        )

        fused = EvidenceGraphService.fuse_evidence(
            canonical_id="endpoint:POST:/api/v3/experimental/export",
            evidence_nodes=[doc_node],
            observed_in_production=False,
        )

        assert fused.observation_state == ObservationState.DOCUMENTED_NOT_OBSERVED
        assert fused.is_conflicting is True
        assert "not observed in direct production verification" in fused.conflict_note


# ==============================================================================
# 2. EVIDENCE GRAPH & STRENGTH HIERARCHY
# ==============================================================================

class TestEvidenceGraphEngine:
    """Verifies evidence strength hierarchy and traceability."""

    def test_evidence_strength_hierarchy_weights(self):
        assert STRENGTH_WEIGHTS[EvidenceStrength.DIRECT_PRODUCTION_OBSERVATION] == 1.0
        assert STRENGTH_WEIGHTS[EvidenceStrength.OFFICIAL_SECURITY_ADVISORY] > STRENGTH_WEIGHTS[EvidenceStrength.OFFICIAL_DOCUMENTATION]
        assert STRENGTH_WEIGHTS[EvidenceStrength.OFFICIAL_DOCUMENTATION] > STRENGTH_WEIGHTS[EvidenceStrength.OFFICIAL_GITHUB]
        assert STRENGTH_WEIGHTS[EvidenceStrength.OFFICIAL_GITHUB] > STRENGTH_WEIGHTS[EvidenceStrength.THIRD_PARTY_REFERENCE]
        assert STRENGTH_WEIGHTS[EvidenceStrength.THIRD_PARTY_REFERENCE] > STRENGTH_WEIGHTS[EvidenceStrength.HEURISTIC]

    def test_weak_evidence_cannot_override_strong_evidence(self):
        heuristic_node = EvidenceNode(
            source_type=EvidenceSourceType.WEB_ARCHIVE,
            strength=EvidenceStrength.HEURISTIC,
            source_url="https://archive.org/sample",
            evidence_text="Heuristic guess from old snapshot",
            content_hash="h1",
            confidence=0.99,  # Artificially high raw confidence
        )
        production_node = EvidenceNode(
            source_type=EvidenceSourceType.BROWSER_OBSERVATION,
            strength=EvidenceStrength.DIRECT_PRODUCTION_OBSERVATION,
            source_url="https://app.example.com",
            evidence_text="Observed live endpoint",
            content_hash="h2",
            confidence=0.85,
        )

        fused = EvidenceGraphService.fuse_evidence(
            canonical_id="endpoint:test",
            evidence_nodes=[heuristic_node, production_node],
        )
        # Primary strength should be DIRECT_PRODUCTION_OBSERVATION
        assert fused.primary_strength == EvidenceStrength.DIRECT_PRODUCTION_OBSERVATION

    def test_traceability_chain_builder(self):
        trace = EvidenceGraphService.trace_claim(
            signal_id=42,
            source_name="GITHUB",
            evidence_text="commit adding OAuth2 SSO flow",
            entity_name="SSO Service",
            change_summary="New OAuth2 callback endpoint",
            security_context_summary="Historical authentication weakness recorded in 2024",
        )
        assert trace["valid"] is True
        steps = [step["step"] for step in trace["chain"]]
        assert steps == ["SOURCE", "EVIDENCE", "ENTITY", "OBSERVATION", "CHANGE", "SECURITY_CONTEXT", "RESEARCH_SIGNAL"]


# ==============================================================================
# 3. ENTITY RESOLUTION & DISAMBIGUATION
# ==============================================================================

class TestEntityResolution:
    """Verifies technology alias resolution and ambiguity guarding."""

    def test_resolve_technology_aliases(self):
        res1 = EntityResolutionService.resolve_technology("Kludex Starlette")
        assert res1.canonical_name == "starlette"
        assert res1.resolution_confidence >= 0.95

        res2 = EntityResolutionService.resolve_technology("facebook react")
        assert res2.canonical_name == "react"

        res3 = EntityResolutionService.resolve_technology("k8s")
        assert res3.canonical_name == "kubernetes"

    def test_ambiguous_generic_names_not_merged(self):
        res = EntityResolutionService.resolve_technology("server")
        assert res.is_ambiguous is True
        assert res.resolution_confidence <= 0.5

    def test_resolve_vulnerability_canonical_id_dominance(self):
        res = EntityResolutionService.resolve_vulnerability_canonical_id(
            cve_id="CVE-2021-44228",
            ghsa_id="GHSA-jfh8-c2jp-5v3q",
            nvd_id="CVE-2021-44228",
        )
        assert res.canonical_name == "CVE-2021-44228"
        assert "GHSA-jfh8-c2jp-5v3q" in res.aliases
        assert res.resolution_confidence == 1.0


# ==============================================================================
# 4. SEMANTIC FINGERPRINTING & ARTIFACT UNIFICATION
# ==============================================================================

class TestSemanticFingerprinting:
    """Verifies stable fingerprinting across non-semantic variations."""

    def test_path_normalization_parameter_syntax(self):
        p1 = SemanticFingerprintService.normalize_path("/api/v1/users/123")
        p2 = SemanticFingerprintService.normalize_path("/api/v1/users/{userId}")
        p3 = SemanticFingerprintService.normalize_path("/api/v1/users/:id")
        p4 = SemanticFingerprintService.normalize_path("/api/v1/users/<id>")
        assert p1 == p2 == p3 == p4 == "/api/v1/users/{param}"

    def test_stable_fingerprint_across_parameter_order_and_minification(self):
        fp1 = SemanticFingerprintService.compute_endpoint_fingerprint("POST", "/api/v2/admin/impersonate", ["role", "user_id"])
        fp2 = SemanticFingerprintService.compute_endpoint_fingerprint("post", "/api/v2/admin/impersonate?bundle=abc817", ["user_id", "role"])
        assert fp1 == fp2

    def test_multi_source_endpoint_unification(self):
        obs = [
            {"method": "POST", "path": "/api/v2/admin/impersonate", "parameters": ["user_id"], "source": "AST_ANALYSIS"},
            {"method": "POST", "path": "/api/v2/admin/impersonate", "parameters": ["role"], "source": "OPENAPI"},
            {"method": "POST", "path": "/api/v2/admin/impersonate", "source": "BROWSER_OBSERVATION"},
        ]
        unified = SemanticFingerprintService.unify_endpoint_observations(obs)
        assert len(unified) == 1
        art = unified[0]
        assert art.canonical_name == "POST /api/v2/admin/impersonate"
        assert set(art.evidence_sources) == {"AST_ANALYSIS", "OPENAPI", "BROWSER_OBSERVATION"}
        assert set(art.parameters) == {"user_id", "role"}


# ==============================================================================
# 5. HISTORICAL REPLAY & MEASURABLE COVERAGE
# ==============================================================================

class TestHistoricalReplay:
    """Verifies historical replay delta computation and coverage quality."""

    def test_epoch_delta_comparison(self):
        epoch_2024 = EpochState(
            epoch_name="2024",
            timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
            active_endpoints={"GET /users", "POST /login"},
            active_features={"Auth"},
            active_technologies={"React 17", "Python 3.10"},
        )
        epoch_2025 = EpochState(
            epoch_name="2025",
            timestamp=datetime(2025, 1, 1, tzinfo=timezone.utc),
            active_endpoints={"GET /users", "POST /login", "POST /admin/export"},
            active_features={"Auth", "Data Export"},
            active_technologies={"React 18", "Python 3.11"},
            recorded_security_events=[{"cve_id": "CVE-2025-001"}],
        )

        delta = HistoricalReplayService.compare_epochs(epoch_2024, epoch_2025)
        assert delta.added_endpoints == ["POST /admin/export"]
        assert delta.removed_endpoints == []
        assert delta.added_features == ["Data Export"]
        assert "CVE-2025-001" in delta.new_security_events

    def test_coverage_quality_report_metrics(self):
        events = [
            {"quality_badge": "CONFIRMED_HISTORY", "confidence": 0.95},
            {"quality_badge": "CONFIRMED_HISTORY", "confidence": 0.90},
            {"quality_badge": "LIKELY_HISTORY", "confidence": 0.70},
            {"quality_badge": "WEAK_HISTORY", "confidence": 0.40},
        ]
        report = HistoricalReplayService.compute_coverage_quality(
            company_id=1,
            start_year=2021,
            end_year=2026,
            sources=["GITHUB", "OSV", "CISA_KEV"],
            events=events,
            known_gaps=["2022-Q3 unindexed"],
        )
        assert report.confirmed_events == 2
        assert report.likely_events == 1
        assert report.weak_events == 1
        assert report.source_count == 3
        assert "partial" in report.transparency_disclaimer.lower()
        assert "complete history" not in report.transparency_disclaimer.lower()


# ==============================================================================
# 6. TEMPORAL SCOPE RESOLUTION & EXPLANATIONS
# ==============================================================================

class TestTemporalScopeResolution:
    """Verifies scope rules respecting temporal windows (valid_from to valid_to)."""

    def test_temporal_scope_validity_window(self):
        now = datetime.now(timezone.utc)
        rule_2024 = ProgramScopeRule(
            pattern="api.example.com",
            inclusion_type=InclusionType.INCLUDE.value,
            valid_from=now - timedelta(days=730),
            valid_to=now - timedelta(days=365),
            confidence=0.95,
            source_url="https://hackerone.com/example/policy_2024",
        )
        rule_2026 = ProgramScopeRule(
            pattern="api.example.com",
            inclusion_type=InclusionType.EXCLUDE.value,
            valid_from=now - timedelta(days=30),
            valid_to=None,
            confidence=0.99,
            source_url="https://hackerone.com/example/policy_2026",
        )

        rules = [rule_2024, rule_2026]

        # In 2024: Should be IN_SCOPE
        time_2024 = now - timedelta(days=500)
        dec_2024 = ScopeResolver.evaluate("api.example.com", rules, at_time=time_2024)
        assert dec_2024.status == ScopeStatus.IN_SCOPE
        assert "policy_2024" in dec_2024.reason

        # In 2026: Should be OUT_OF_SCOPE
        time_2026 = now
        dec_2026 = ScopeResolver.evaluate("api.example.com", rules, at_time=time_2026)
        assert dec_2026.status == ScopeStatus.OUT_OF_SCOPE
        assert "policy_2026" in dec_2026.reason

    def test_unverified_scope_explanation(self):
        dec = ScopeResolver.evaluate("unknown.otherdomain.org", [])
        assert dec.status == ScopeStatus.UNKNOWN
        assert dec.reason == "Scope could not be verified from available evidence."


# ==============================================================================
# 7. SIGNAL QUALITY & FEEDBACK METRICS
# ==============================================================================

class TestSignalFeedbackAnalytics:
    """Verifies researcher feedback tracking and metrics calculation."""

    def test_feedback_enum_values(self):
        assert FeedbackType.USEFUL.value == "USEFUL"
        assert FeedbackType.NOT_USEFUL.value == "NOT_USEFUL"
        assert FeedbackType.NOT_IN_SCOPE.value == "NOT_IN_SCOPE"
        assert FeedbackType.FALSE_POSITIVE.value == "FALSE_POSITIVE"
        assert FeedbackType.DUPLICATE.value == "DUPLICATE"

    def test_signal_feedback_model_insertion(self, memory_db):
        signal = ResearchSignal(
            title="New GraphQL Batching Query",
            signal_type="NEW_API_SURFACE",
            summary="Discovered GraphQL endpoint supporting batched queries.",
            why_it_matters="Potential vector for rate limit bypassing.",
            relevance_score=85,
            confidence_score=90,
            priority="HIGH",
            status=SignalStatus.NEW.value,
        )
        memory_db.add(signal)
        memory_db.flush()

        fb = ResearchSignalFeedback(
            signal_id=signal.id,
            user_id=1,
            feedback=FeedbackType.USEFUL.value,
            reason="Confirmed rate limit bypass possibility.",
        )
        memory_db.add(fb)
        memory_db.commit()

        retrieved_fb = memory_db.query(ResearchSignalFeedback).filter_by(signal_id=signal.id).first()
        assert retrieved_fb is not None
        assert retrieved_fb.feedback == FeedbackType.USEFUL.value

    def test_metrics_calculation_formula(self, memory_db):
        from app.routers.signals import get_signal_quality_metrics
        from app.models.target import Target
        from app.models.user import User

        user = User(email="analyst@example.com", password_hash="pw")
        memory_db.add(user)
        memory_db.flush()

        target = Target(user_id=user.id, domain="metrics.example.com", authorization_confirmed=True)
        memory_db.add(target)
        memory_db.flush()

        s1 = ResearchSignal(target_id=target.id, title="Sig 1", summary="s1", why_it_matters="w1", priority="HIGH", status="investigating", signal_type="NEW_API")
        s2 = ResearchSignal(target_id=target.id, title="Sig 2", summary="s2", why_it_matters="w2", priority="HIGH", status="ignored", signal_type="NEW_API")
        s3 = ResearchSignal(target_id=target.id, title="Sig 3", summary="s3", why_it_matters="w3", priority="LOW", status="new", signal_type="OTHER")
        memory_db.add_all([s1, s2, s3])
        memory_db.flush()

        fb1 = ResearchSignalFeedback(signal_id=s1.id, user_id=user.id, feedback="USEFUL")
        fb2 = ResearchSignalFeedback(signal_id=s2.id, user_id=user.id, feedback="FALSE_POSITIVE")
        memory_db.add_all([fb1, fb2])
        memory_db.commit()

        metrics = get_signal_quality_metrics(target_id=target.id, db=memory_db, current_user=user)
        assert metrics["signals_generated"] == 3
        assert metrics["signals_opened"] == 2  # s1 and s2 not new
        assert metrics["signals_dismissed"] == 1  # s2 is ignored
        assert metrics["false_positive_rate"] == round(1 / 3, 3)
        assert metrics["investigation_rate"] == round(1 / 3, 3)
        assert metrics["high_priority_precision"] == 0.5  # 1 useful out of 2 high priority signals

    def test_multi_source_convergence_capped_at_98_percent(self):
        nodes = [
            EvidenceNode(source_type=EvidenceSourceType.DOCUMENTATION, strength=EvidenceStrength.OFFICIAL_DOCUMENTATION, source_url="u1", evidence_text="e1", content_hash="h1", confidence=0.9),
            EvidenceNode(source_type=EvidenceSourceType.OPENAPI, strength=EvidenceStrength.OFFICIAL_DOCUMENTATION, source_url="u2", evidence_text="e2", content_hash="h2", confidence=0.9),
            EvidenceNode(source_type=EvidenceSourceType.BROWSER_OBSERVATION, strength=EvidenceStrength.DIRECT_PRODUCTION_OBSERVATION, source_url="u3", evidence_text="e3", content_hash="h3", confidence=0.95),
            EvidenceNode(source_type=EvidenceSourceType.GITHUB, strength=EvidenceStrength.OFFICIAL_GITHUB, source_url="u4", evidence_text="e4", content_hash="h4", confidence=0.9),
            EvidenceNode(source_type=EvidenceSourceType.RELEASE, strength=EvidenceStrength.OFFICIAL_RELEASE, source_url="u5", evidence_text="e5", content_hash="h5", confidence=0.9),
        ]
        conf = EvidenceGraphService.calculate_converged_confidence(nodes)
        assert conf <= 0.98
        assert conf >= 0.95

    def test_conditional_scope_rule_evaluation(self):
        rule = ProgramScopeRule(
            pattern="*.beta.example.com",
            inclusion_type=InclusionType.CONDITIONAL.value,
            confidence=0.9,
            source_url="https://policy.example.com",
        )
        dec = ScopeResolver.evaluate("test.beta.example.com", [rule])
        assert dec.status == ScopeStatus.RELATED
        assert "conditional" in dec.reason.lower()

    def test_organizational_subdomain_fallback_without_rules(self):
        dec = ScopeResolver.evaluate("admin.example.com", [], canonical_domain="example.com")
        assert dec.status == ScopeStatus.PENDING_VERIFICATION
        assert "pending verification" in dec.reason.lower()

    def test_organizational_subdomain_fallback_with_existing_unmatched_rules(self):
        rule = ProgramScopeRule(
            pattern="api.example.com",
            inclusion_type=InclusionType.INCLUDE.value,
        )
        dec = ScopeResolver.evaluate("other.example.com", [rule], canonical_domain="example.com")
        assert dec.status == ScopeStatus.RELATED
        assert "not explicitly enumerated" in dec.reason.lower()

