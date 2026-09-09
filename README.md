# AttackSurface Timeline

**Bug Bounty Research Intelligence Platform**

> Show a security researcher what changed in a target, prove the change with evidence, explain why it may matter from a security-research perspective, connect it to historical context, and help the researcher decide what to investigate next.

This is **not** an autonomous hacking platform, exploit generator, or unrestricted scanner. Only authorized/public data and conservative collection.

## Quick Start

```bash
cp .env.example .env
# Add your credentials to .env (GITHUB_TOKEN, GEMINI_API_KEY, etc.)
docker compose up --build
```

- **Web UI**: http://localhost:3000
- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

## Architecture

```
Web (Next.js 15) → API (FastAPI) → PostgreSQL (Company Graph, Assets, Security KB)
                                  → Redis (jobs, cache, rate limits)
                                  → Worker (RQ background jobs)
                                  → Providers (GitHub, Gemini, NVIDIA, OSV, CISA, NVD)
                                  → Security Knowledge Base (CISA KEV, CWE, OWASP)
```

See [ARCHITECTURE.md](ARCHITECTURE.md) and [SECURITY_KNOWLEDGE.md](SECURITY_KNOWLEDGE.md) for full details.

## Configuration

All configuration is via environment variables. Copy `.env.example` to `.env` and fill in your values.

| Variable | Required | Description |
|---|---|---|
| `DATABASE_URL` | Yes | PostgreSQL connection string |
| `REDIS_URL` | Yes | Redis connection string |
| `SECRET_KEY` | Yes | Session signing key (auto-generated if empty) |
| `GITHUB_TOKEN` | No | GitHub API token for enhanced rate limits |
| `GEMINI_API_KEY` | No | Google Gemini API key (primary AI) |
| `NVIDIA_API_KEY` | No | NVIDIA API key (secondary AI) |
| `NVD_API_KEY` | No | NVD API key for enhanced rate limits |
| `GOOGLE_CLIENT_ID` | No | Google OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | No | Google OAuth client secret |

**The application starts and operates even when all optional credentials are absent.** AI features degrade gracefully to deterministic-only mode.

## Development

```bash
# Backend
cd api
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend
cd web
npm install
npm run dev

# Tests
cd api && pytest -q
```

See [DEVELOPMENT.md](DEVELOPMENT.md) for full setup guide.

## Security Model

- Only authorized targets may be observed
- Conservative public-only collection (robots.txt, GET-only, same-origin, bounded)
- SSRF prevention with DNS rebinding defense
- Prompt injection defense for all AI interactions
- Cookie-based session auth with secure defaults
- All collected content treated as untrusted data
- Rate limiting on all endpoints

See [SECURITY.md](SECURITY.md) for full details.

## Legal

Use only for targets you are authorized to observe. Respect the target's terms and `robots.txt`. This project has no offensive/exploitation capabilities.
