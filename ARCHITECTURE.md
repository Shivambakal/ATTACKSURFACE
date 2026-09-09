# Architecture

## System Overview

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   Web (UI)   │───▶│   API (BE)   │───▶│  PostgreSQL  │
│  Next.js 15  │    │   FastAPI    │    │   16-alpine  │
│   Port 3000  │    │   Port 8000  │    │   Port 5432  │
└──────────────┘    └──────┬───────┘    └──────────────┘
                           │
                    ┌──────┴───────┐
                    │    Redis     │
                    │  7-alpine    │
                    │  Port 6379   │
                    └──────┬───────┘
                           │
                    ┌──────┴───────┐
                    │   Worker     │
                    │   RQ Jobs    │
                    └──────┬───────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
        ┌─────┴────┐ ┌────┴─────┐ ┌────┴────┐
        │ GitHub   │ │ Gemini   │ │  NVIDIA  │
        │ Provider │ │ Provider │ │ Provider │
        └──────────┘ └──────────┘ └─────────┘
              │
        ┌─────┴────┐ ┌──────────┐ ┌─────────┐
        │   OSV    │ │ CISA KEV │ │   NVD   │
        │ Provider │ │ Provider │ │ Provider│
        └──────────┘ └──────────┘ └─────────┘
```

## Data Flow

### Collection Pipeline

```
TARGET → SOURCE DISCOVERY → COLLECTORS → NORMALIZATION → DEDUPLICATION →
SNAPSHOT → DIFF → CHANGE CLASSIFICATION → SECURITY RELEVANCE →
HISTORICAL CORRELATION → AI EXPLANATION → TIMELINE → ALERT
```

Every event has **provenance** — traceable back to source evidence.

### AI Pipeline

```
RAW OBSERVATION → NORMALIZATION → DETERMINISTIC DIFF → RULE-BASED CLASSIFICATION →
EVIDENCE → GEMINI EXPLANATION → FINAL RESEARCH SUMMARY
```

AI is **never** the source of truth. Deterministic facts always come first.

## Data Model

### Core Models
- **Target** — Approved observation domain with authorization confirmation
- **Snapshot** — Collection event with timestamp and status
- **Observation** — Normalized URL/content/technology evidence per snapshot
- **Change** — Deduplicated classified before/after diff with deterministic score
- **ChangeEvidence** — Immutable before/current evidence references
- **Evidence** — Immutable chain-of-custody record

### Intelligence Models
- **TimelineEvent** — Unified timeline across all sources
- **Company** & **Asset** — Company graph and target infrastructure components
- **Technology** — Detected technology with version tracking
- **Feature** — Product feature with lifecycle tracking
- **SecurityEvent** — Company-specific CVE, advisory, and verified security history
- **ResearchSignal** — High-signal security research opportunities

### Security Knowledge Base (Global)
- **SecurityAdvisory** — Multi-source global vulnerability advisories (CISA KEV, CVEs)
- **CWEEntry** — MITRE Common Weakness Enumeration taxonomy
- **OWASPCategory** — OWASP Top 10 (2021) categories
- **KnowledgeSource** & **KnowledgeSyncRun** — Ingestion provenance, sync runs, and content hashing
- **VulnerabilityReference** — Cross-referenced external documentation and advisories

### User Models
- **User** — Authentication identity
- **UserProfile** — Display name, bio, researcher type
- **Session** — Cookie-based session with revocation
- **UserSettings** — Appearance, notifications, research, privacy settings

### Research Models
- **ResearchNote** — User notes linked to targets/changes/evidence
- **ResearchTask** — Investigation tasks with priorities
- **ResearchFinding** — Documented findings with evidence
- **WatchlistEntry** — Monitored entities
- **Alert** — User notifications

## Provider Architecture

All providers implement `BaseProvider` with consistent interfaces:
- `is_configured()` — Whether required credentials are present
- `check_health()` — Safe health check (never exposes credentials)
- `fetch()` — Data retrieval with rate limiting and retry

Provider errors are **isolated** — one failed provider never crashes the application.

### Fallback Order (AI)
1. Gemini (primary)
2. NVIDIA (if configured)
3. Deterministic rules only

## Security Architecture

See [SECURITY.md](SECURITY.md) for detailed security model.
