# AttackSurface Timeline — Intelligence Audit & Architecture Strategy

## Executive Summary

AttackSurface Timeline was initially architected as a lightweight differential crawler recording raw page additions, removals, and superficial text differences. While effective at capturing infrastructure snapshots, its primary bottleneck is **signal-to-noise ratio**:
- A single minor marketing update, copyright year change in a footer, or cookie consent banner triggers raw diffs.
- Diffs are treated uniformly as generic page modifications rather than semantic security evolutions.
- Security researchers are inundated with low-relevance events (`"public_content_change"` or `"removed_public_page"`), directly violating the core product promise:
  > *"Show a security researcher what changed in a target, prove the change with evidence, explain why it may matter from a security-research perspective, connect it to historical context, and help the researcher decide where to spend their next 30 minutes."*

This document provides a comprehensive audit of the legacy pipeline, identifies noise vectors, and details the **Multi-Layer Research Intelligence Architecture**.

---

## 1. Current Pipeline Audit

### 1.1 Current Observation Model
- **Mechanism** (`collector.py`):
  - Fetches up to `MAX_PAGES_PER_SNAPSHOT` (default 8) via HTTP GET.
  - Strips `<script>`, `<style>`, `<noscript>`.
  - Generates a single SHA-256 hash over the entire stripped text excerpt (`text[:12000]`).
  - Records only status code, page title, technology headers (`server`, `x-powered-by`), and raw excerpt (`text[:2000]`).
- **Deficiencies**:
  - No DOM-structural awareness: cannot distinguish a change in `<form action="...">` or `<input name="token">` from a change in marketing copy.
  - Query parameter stripping is rudimentary (`clean.rstrip('/')`), risking loss of legitimate endpoint parameters or retaining tracking parameters (e.g., `utm_*`, `fbclid`).
  - Ephemeral components (timestamps, CSRF tokens, session IDs, ads, cookie banners) trigger false content hash mismatches.

### 1.2 Current Diff Algorithm
- **Mechanism** (`diffing.py`):
  - Compares set of URLs between previous snapshot and current snapshot.
  - Generates:
    - `page_removed` if URL in old but not in new.
    - `page_added` if URL in new but not in old.
    - `content_changed` if `old.content_hash != new.content_hash`.
    - `technology_changed` if `old.technologies != new.technologies`.
- **Deficiencies**:
  - Binary hash comparison: 1 byte altered in a legal disclaimer flags the entire page as `content_changed`.
  - No granular diffing of forms, auth endpoints, API routes, or technology headers.
  - Flapping / transient errors (e.g. 503 or transient 404) generate noisy `page_removed` events.

### 1.3 Current Classification Rules
- **Mechanism** (`classification.py`):
  - Simple regex/substring checks on lowercased `title + text_excerpt`:
    - `api`, `openapi`, `swagger` $\to$ `"new_api_documentation"` or `"api_or_feature_change"`.
    - `login`, `authentication`, `authorization`, `oauth`, `sso`, `permission` $\to$ `"authentication_documentation_change"`.
    - Else $\to$ `"public_content_change"`.
- **Deficiencies**:
  - Lacks semantic nuance: A blog post mentioning "OAuth" is classified as an `"authentication_documentation_change"`, while an actual new OAuth login endpoint with a code challenge might be missed if words don't match exactly.
  - Does not extract features, endpoints, or attack surface objects.

### 1.4 Current Score Calculation
- **Mechanism** (`scoring.py`):
  - Base weight: `new_api_documentation` (80), `authentication_documentation_change` (75), `api_or_feature_change` (65), etc.
  - Substring boosts: `oauth`, `sso`, `auth`, `admin`, `webhook` (+10), `api`, `endpoint` (+8), `cve`, `vulnerability` (+12).
- **Deficiencies**:
  - Relevance and confidence are conflated into a single integer.
  - Negative signals (noise, cosmetic, marketing, tracking) are only minimally applied.
  - Historical target context does not influence score.

### 1.5 Current Provider Data Integration
- Providers (`github`, `osv`, `cisa_kev`, `nvd`) collect data independently.
- Correlation in `pipeline.py` is keyword-based and loosely coupled to changes.
- Multi-source correlation is missing: seeing a change in GitHub releases + documentation + API schema doesn't reinforce confidence or cluster into a unified product release.

### 1.6 Current AI Usage
- `ai_explain` in `pipeline.py` generates an unstructured text summary for changes.
- While prompt injection defenses exist (`ai_safety.py`), the model outputs freeform text rather than a strictly validated structured research signal with citations.

---

## 2. Identified Noise Sources

| Noise Source | Why It Triggers Today | Impact on Researcher |
|---|---|---|
| **Footer Copyright & Year** | Triggers `content_hash` mismatch across all crawled pages every Jan 1st or deployment | Fake "content_changed" across 100% of pages |
| **Session / CSRF Tokens** | Inline tokens in hidden form inputs change content hash on every GET request | Constant false positive changes |
| **Tracking / Analytics** | Changes to Google Tag Manager, Intercom, or Segment scripts | Noise treated as functional code change |
| **Marketing Copy & Banners** | Sale announcements, seasonal graphics, announcement bars | Clutters researcher timeline |
| **Ephemeral Query Strings** | `?v=1.2.3`, `?_t=1725384000`, `?utm_source=...` | Treated as distinct URLs / new pages |
| **Transient 5xx / 429 Errors** | Temporary network glitches cause page to be absent in one snapshot | Triggers false `page_removed` followed by `page_added` |

---

## 3. The Target Intelligence Paradigm

```
RAW OBSERVATIONS (100)
       │
       ▼
[ Normalization & Canonicalization ] ── Drops tracking, normalizes markup, extracts semantic blocks
       │
       ▼
[ Multi-Aspect Content Diff Engine ] ── Detects: Structural, Functional, Security-Sensitive, Cosmetic, Noise
       │
       ▼
[ Change Clustering & Dedup ] ────── Collapses 25 related page changes into 1 Product Release
       │
       ▼
[ Feature & API Intelligence ] ───── Extracts: Auth Boundaries, APIs, Workflows, Assets, Tech
       │
       ▼
[ Historical Security Correlation ] ─ Cross-references target's vulnerability history (CISA KEV, OSV, NVD)
       │
       ▼
[ Dual Engine: Relevance vs Confidence ]
       │
       ▼
[ Structured AI Grounding ] ──────── Generates validated JSON research briefs with verified citations
       │
       ▼
RESEARCH SIGNALS (3 - 5 High-Value Actionable Leads)
```

---

## 4. Multi-Layer Pipeline Architecture

### Layer 1: Normalization & Content Decomposition
Deconstructs each page into discrete semantic layers before hashing:
- **Canonical URL Engine**: Strips tracking parameters (`utm_*`, `fbclid`, `gclid`, `_ga`, `ref`, `source`), sorts meaningful parameters, normalizes scheme, port, case, trailing slashes.
- **Noise Stripping**: Removes cookie banners, tracking scripts, dynamic timestamps, CSRF nonces, legal disclaimers.
- **DOM Feature Extraction**:
  - `forms`: actions, methods, input names, input types.
  - `auth_indicators`: OAuth buttons, login forms, SSO providers, session endpoints.
  - `api_endpoints`: Paths matching `/api/*`, `/v[0-9]+/*`, GraphQL endpoints, Swagger/OpenAPI links.
  - `interactive_elements`: File upload fields, export buttons, webhook configurations, role selectors.

### Layer 2: Content Difference & Classification Engine
Evaluates changes across 7 distinct dimensions:
1. `SECURITY_SENSITIVE`: New authentication scheme, new admin path, modified authorization headers, file upload capability, exposed API key pattern.
2. `FUNCTIONAL`: New interactive forms, API routes, user workflows.
3. `STRUCTURAL`: DOM hierarchy alterations without security implications.
4. `TECHNOLOGY`: Framework, library, or web server changes with version tracking.
5. `MARKETING`: Copy changes in hero banners, feature descriptions.
6. `COSMETIC`: CSS classes, typography, spacing changes.
7. `NOISE`: Timestamp, cache-buster, or tracking changes $\to$ **Suppressed automatically**.

### Layer 3: Feature & API Intelligence
Elevates raw URLs to domain entities:
- **`Feature`**: "Team Invitation Workflow", "OAuth 2.0 PKCE Authorization", "Bulk User Export API".
- **`ApiSurface`**: Method (`GET`, `POST`), Path (`/v2/users/export`), Auth Requirement (`Bearer JWT`), Parameters.
- **`Asset`**: Hostname, WebApp, API Documentation, Public Repository with status lifecycle (`NEW`, `ACTIVE`, `CHANGED`, `REMOVED`, `REAPPEARED`).

### Layer 4: Historical Security Correlation & Target Fingerprinting
- Calculates the target's historical security profile:
  - If a target historically had authorization issues (`CWE-862`, `CWE-639` / BOLA), newly detected API endpoints or invitation workflows receive a significant security context boost.
  - Technology correlation against CISA KEV and OSV catalogs for high-confidence match.

### Layer 5: Research Relevance, Confidence & Context Scoring
- **`relevance_score`** (0–100): How interesting is this change for an authorized bug bounty hunter?
- **`confidence_score`** (0–100): How certain are we that this change is genuine and non-transient?
- **`security_context_score`** (0–100): How sensitive is the affected asset and functionality based on target history?
- **Factors Breakdown**: Transparent audit trail showing every positive and negative delta.

### Layer 6: Research Signal & Visibility Filtering
Changes are triaged into four visibility levels:
- `INTERNAL_RAW`: Stored for forensic audit and model retraining, hidden from timeline.
- `USER_VISIBLE`: Informational updates visible in raw change logs.
- `HIGH_SIGNAL`: Promoted to the main Security Timeline.
- `ALERT_WORTHY`: Dispatches immediate notification / alert.

First-class **`ResearchSignal`** object created for high-value research leads with clear researcher action guides ("Examine access control boundary on /v2/orgs/{id}/members").
