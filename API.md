# API Reference

Base URL: `http://localhost:8000/api/v1`

## Authentication

### POST `/api/v1/auth/signup`
Create a new account.
```json
{ "email": "user@example.com", "password": "minimum8chars" }
```

### POST `/api/v1/auth/login`
Login with credentials. Sets `session_token` cookie.
```json
{ "email": "user@example.com", "password": "password" }
```

### POST `/api/v1/auth/logout`
Logout current session. Clears cookie.

### POST `/api/v1/auth/logout-all`
Revoke all sessions for current user.

### GET `/api/v1/auth/me`
Get current authenticated user.

## Targets

### POST `/api/v1/targets`
Create a new observation target.
```json
{ "domain": "example.com", "authorization_confirmed": true }
```

### GET `/api/v1/targets`
List user's targets.

### GET `/api/v1/targets/{id}`
Get target details.

### GET `/api/v1/targets/{id}/overview`
Get target overview with recent changes.

### POST `/api/v1/targets/{id}/visit`
Update last-visited timestamp.

## Snapshots

### POST `/api/v1/targets/{id}/snapshots`
Take a new snapshot of the target.

### GET `/api/v1/targets/{id}/snapshots`
List snapshots for a target.

## Changes

### GET `/api/v1/changes/{id}`
Get change details with evidence.

### POST `/api/v1/changes/{id}/status`
Update research status.
```json
{ "status": "investigating" }
```

## Timeline

### GET `/api/v1/targets/{id}/timeline`
Get timeline events for a target.

### GET `/api/v1/targets/{id}/timeline/since-last-visit`
Get events since user's last visit.

## Research

### Notes
- `POST /api/v1/research/notes` — Create note
- `GET /api/v1/research/notes` — List notes
- `GET /api/v1/research/notes/{id}` — Get note
- `PUT /api/v1/research/notes/{id}` — Update note
- `DELETE /api/v1/research/notes/{id}` — Delete note

### Tasks
- `POST /api/v1/research/tasks` — Create task
- `GET /api/v1/research/tasks` — List tasks
- `PUT /api/v1/research/tasks/{id}` — Update task

### Findings
- `POST /api/v1/research/findings` — Create finding
- `GET /api/v1/research/findings` — List findings

## Watchlist
- `POST /api/v1/watchlist` — Add to watchlist
- `GET /api/v1/watchlist` — List watchlist
- `DELETE /api/v1/watchlist/{id}` — Remove from watchlist

## Alerts
- `GET /api/v1/alerts` — List alerts
- `POST /api/v1/alerts/{id}/read` — Mark alert read
- `POST /api/v1/alerts/read-all` — Mark all read
- `GET /api/v1/alerts/preferences` — Get preferences
- `PUT /api/v1/alerts/preferences` — Update preferences

## Search

### GET `/api/v1/search?q={query}`
Global search across targets, changes, assets, features, notes, findings, evidence.

## Profile
- `GET /api/v1/profile` — Get profile
- `PUT /api/v1/profile` — Update profile

## Settings
- `GET /api/v1/settings` — Get settings
- `PUT /api/v1/settings` — Update settings
- `GET /api/v1/settings/sessions` — List active sessions
- `DELETE /api/v1/settings/sessions/{id}` — Revoke session

## Security Knowledge Base

- `GET /api/v1/security-knowledge/` — Paginated list of security advisories (supports `q`, `provider`, `cve_id`, `limit`, `offset`)
- `GET /api/v1/security-knowledge/stats` — Overall statistics (total advisories, known exploited, ransomware-linked, provider breakdown)
- `GET /api/v1/security-knowledge/sources` — List of configured knowledge sources with status
- `GET /api/v1/security-knowledge/sync-runs` — Audit history of recent ingestion sync runs
- `GET /api/v1/security-knowledge/cve/{cve_id}` — Get advisory by standard CVE ID (e.g. `CVE-2021-44228`)
- `GET /api/v1/security-knowledge/search?q={query}` — Search advisories across title, summary, vendor, and product
- `GET /api/v1/security-knowledge/{id}` — Get single advisory details with associated CWEs and OWASP categories

## Health
- `GET /health` — Basic health check
- `GET /api/v1/health` — API health
- `GET /api/v1/health/providers` — Provider health statuses (never exposes credentials)

