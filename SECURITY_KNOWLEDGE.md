# Security Knowledge Base

The **Security Knowledge Base** is the global, multi-source vulnerability and weakness intelligence layer in **AttackSurface Timeline**. It provides researchers with authoritative, evidence-backed security context to evaluate detected technologies, understand threat landscapes, and prioritize research activities without making false or unsubstantiated vulnerability claims.

---

## 1. Core Architecture & Philosophy

### Global Knowledge vs. Company Security History

A foundational architectural principle of AttackSurface Timeline is the strict separation between:

1. **Global Security Knowledge (Shared / Public)**:
   - Authoritative vulnerability advisories (e.g., CISA Known Exploited Vulnerabilities catalog, NVD CVEs, GitHub Advisories, OSV).
   - Weakness taxonomies (MITRE CWE) and security categorizations (OWASP Top 10 2021).
   - Tenant-agnostic, publicly observable knowledge.

2. **Company Security History (Tenant-Scoped / Asset-Contextual)**:
   - Confirmed security events (`SecurityEvent`), observations, and incidents tied directly to a company's assets.
   - **Never Confuse Correlation With Exploitation**: Detecting that a target company uses a technology (e.g., `Apache Log4j` or `nginx 1.18.0`) **never** automatically asserts that the target company is vulnerable. Doing so generates false positives and damages research credibility.
   - Instead, the platform presents **Related Technology Context** alongside verified company history, explicitly qualifying it as contextual intelligence.

```
+-------------------------------------------------------------------------+
|                       Global Security Knowledge                         |
|   (CISA KEV, CWE Taxonomy, OWASP Top 10, Future: NVD, OSV, GHSA)        |
+-------------------------------------------------------------------------+
                                    |
                        Correlation Engine (Read-Only)
                                    |
                                    v
+-------------------------------------------------------------------------+
|                  Company Security & Research Intelligence               |
|                                                                         |
|  +--------------------------------+  +--------------------------------+ |
|  | Direct Company Security Events |  |   Related Technology Context   | |
|  | (Evidence-backed observations) |  |   (Advisories for detected tech) | |
|  +--------------------------------+  +--------------------------------+ |
|                                   |                                     |
|                                   v                                     |
|                       Weakness Fingerprint & Radar                      |
+-------------------------------------------------------------------------+
```

---

## 2. Data Models & Schema

The Security Knowledge Base models are defined in [`api/app/models/knowledge.py`](file:///C:/Users/shiva/Documents/ChatGPT/AttackSurface%20Timeline/api/app/models/knowledge.py):

### `SecurityAdvisory`
Represents an authoritative vulnerability advisory:
- `canonical_id`: Unique identifier across providers (e.g., `CISA_KEV:CVE-2021-44228`).
- `cve_id`: Standardized Common Vulnerabilities and Exposures identifier (`CVE-YYYY-NNNN+`).
- `title` & `summary`: Vulnerability description and scope.
- `vendor` & `product`: Affected vendor project and software name.
- `severity` & `cvss_score`: Standard severity scoring.
- `is_known_exploited`: Boolean flag indicating confirmed in-the-wild active exploitation (e.g., CISA KEV listing).
- `known_ransomware_campaign`: Indication if actively weaponized in ransomware operations.
- `required_action` & `due_date`: Remediations and compliance due dates.
- `published_at` & `date_added`: Publication and catalog addition dates.

### `CWEEntry` & `OWASPCategory`
Taxonomy entities interconnected via many-to-many junction tables:
- `CWEEntry`: MITRE Common Weakness Enumeration entry (`cwe_id`, `name`, `description`, `vuln_class`).
- `OWASPCategory`: OWASP Top 10 (2021) categories (`code`, `name`, `year`, `description`).
- **Junction Tables**:
  - `advisory_cwe_association`: Links `SecurityAdvisory` to `CWEEntry`.
  - `advisory_owasp_association`: Links `SecurityAdvisory` to `OWASPCategory`.
  - `cwe_owasp_association`: Maps weaknesses directly to their relevant OWASP classifications.

### `KnowledgeSource` & `KnowledgeSyncRun`
Auditing, tracking, and operational observability:
- `KnowledgeSource`: Registered provider metadata (`name`, `display_name`, `provider_type`, `is_active`, `health_status`).
- `KnowledgeSyncRun`: Ingestion execution logs (`run_id`, `source_id`, `status`, `records_fetched`, `records_upserted`, `content_hash`, `error_log`, timestamps).

---

## 3. CISA KEV Ingestion Engine

Implemented in [`api/app/knowledge/cisa_kev_ingestor.py`](file:///C:/Users/shiva/Documents/ChatGPT/AttackSurface%20Timeline/api/app/knowledge/cisa_kev_ingestor.py):

### Key Characteristics:
1. **Raw Source Preservation**: The raw catalog (`cisa_kev_catalog.json`, containing 1,694 vulnerabilities) is never modified.
2. **Markdown Code Fence Handling**: Strips leading/trailing markdown code blocks (e.g., ```` ```json ... ````) automatically.
3. **Idempotency & Deduplication**:
   - Computes SHA-256 catalog content hashes to track modifications.
   - Upserts advisories based on `canonical_id`. Subsequent runs update timestamps without duplicating records.
   - Safe junction table inserts prevent duplicate key violations across both PostgreSQL and SQLite.
4. **Taxonomy Auto-Seeding**:
   - Automatically seeds the 10 standard OWASP 2021 categories.
   - Automatically resolves and inserts associated `CWEEntry` records and maps them to OWASP categories.
5. **Batch Processing**: Commits records in configurable batch sizes (default: 100) to balance memory usage and database throughput.

### CLI Usage:
```bash
# Dry run to preview records without modifying database
python -m app.knowledge.import_cisa_kev ..\cisa_kev_catalog.json --dry-run

# Import first 50 records
python -m app.knowledge.import_cisa_kev ..\cisa_kev_catalog.json --limit 50

# Full catalog ingestion (1,694 records)
python -m app.knowledge.import_cisa_kev ..\cisa_kev_catalog.json
```

---

## 4. Correlation & Historical Intelligence

Implemented in [`api/app/knowledge/correlation.py`](file:///C:/Users/shiva/Documents/ChatGPT/AttackSurface%20Timeline/api/app/knowledge/correlation.py):

The `SecurityKnowledgeCorrelationService` bridges the gap between detected technologies and security advisories:
- **Technology & Product Alias Matching**: Maps common asset technologies to canonical vendor and product names (e.g., `react` -> `Facebook / React`, `apache` -> `Apache HTTP Server`, `nginx` -> `Nginx / F5`, `log4j` -> `Apache Log4j`).
- **Signal Historical Context**: Matches detected changes to relevant CVEs and weaknesses to enrich `ResearchSignal` cards with actionable investigation guidance.
- **Weakness Fingerprint Generation**: Aggregates historical CWE and OWASP frequencies across a company's attack surface to generate a weakness radar/fingerprint.

---

## 5. REST API Endpoints

The router is mounted at `/api/v1/security-knowledge` in [`api/app/routers/security_knowledge.py`](file:///C:/Users/shiva/Documents/ChatGPT/AttackSurface%20Timeline/api/app/routers/security_knowledge.py):

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/security-knowledge/` | Paginated search of advisories with query, provider, and CVE filters |
| `GET` | `/api/v1/security-knowledge/stats` | Global metrics: total advisories, known exploited count, ransomware count, provider breakdown |
| `GET` | `/api/v1/security-knowledge/sources` | Registered knowledge sources and current health status |
| `GET` | `/api/v1/security-knowledge/sync-runs` | Ingestion run audit history with record counts and execution times |
| `GET` | `/api/v1/security-knowledge/cve/{cve_id}` | Direct lookup by CVE identifier (e.g., `CVE-2021-44228`) |
| `GET` | `/api/v1/security-knowledge/search` | Full-text query across titles, summaries, vendors, and products |
| `GET` | `/api/v1/security-knowledge/{advisory_id}` | Detailed advisory payload including CWE and OWASP relationships |

---

## 6. Frontend User Interface

1. **Global Security Knowledge Base** (`/security-knowledge`):
   - Key intelligence metrics (Total Advisories, Actively Exploited, Ransomware Weaponized, Monitored Sources).
   - Full-text search and filter bar.
   - Advisory cards with severity badges, CISA KEV tags, CWE/OWASP badges, and vendor info.
   - Slide-over inspection drawer for deep-dive investigation.
   - Sync run audit table and provider health status tabs.

2. **Company Security History** (`/companies/[id]/security-history`):
   - Dual-column layout strictly distinguishing **Direct Company Security Events** from **Related Technology Context**.
   - Weakness Fingerprint visual breakdown by CWE and OWASP Top 10 category.
   - Direct links to CVE details and advisories.

3. **Global Navigation**:
   - Added **Security KB** link to the primary navigation sidebar for 1-click access.

---

## 7. Extensibility & Future Providers

The provider interface in [`api/app/knowledge/provider_interface.py`](file:///C:/Users/shiva/Documents/ChatGPT/AttackSurface%20Timeline/api/app/knowledge/provider_interface.py) defines the `SecurityKnowledgeProvider` contract:
- `NVDProvider`: Full NIST National Vulnerability Database CVE & CVSS feed.
- `OSVProvider`: Open Source Vulnerabilities for package ecosystems (npm, PyPI, Go, Maven).
- `GitHubAdvisoryProvider`: GitHub Security Advisories (GHSA).
- `OWASPProvider`: Automated OWASP Top 10 definitions and mappings.
- `CWEProvider`: Automated MITRE CWE XML/JSON taxonomy syncing.

All future providers inherit the standard validation, normalization, and idempotent upsert lifecycle.
