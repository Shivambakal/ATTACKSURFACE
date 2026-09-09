# Development Guide

## Prerequisites

- Python 3.12+
- Node.js 22+
- Docker Desktop
- PostgreSQL 16 (or use Docker)
- Redis 7 (or use Docker)

## Setup

### 1. Clone and configure

```bash
cp .env.example .env
# Edit .env with your credentials
```

### 2. Docker (recommended)

```bash
docker compose up --build
```

This starts: PostgreSQL, Redis, API, Worker, and Web.

### 3. Local development

```bash
# Backend
cd api
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend
cd web
npm install
npm run dev
```

## Project Structure

```
├── api/
│   ├── app/
│   │   ├── main.py           # Application factory
│   │   ├── config.py         # Typed configuration
│   │   ├── db.py             # Database engine/session
│   │   ├── schemas.py        # Pydantic schemas
│   │   ├── worker.py         # RQ worker entrypoint
│   │   ├── models/           # SQLAlchemy models
│   │   ├── routers/          # FastAPI route handlers
│   │   ├── services/         # Business logic
│   │   ├── providers/        # External data providers
│   │   ├── middleware/       # Rate limiting, etc.
│   │   ├── jobs/             # Background job definitions
│   │   └── demo/             # Demo data seeding
│   └── tests/                # Test suite
├── web/
│   ├── app/                  # Next.js App Router pages
│   ├── components/           # Shared React components
│   └── lib/                  # Utilities and types
├── docker-compose.yml
├── .env.example
└── docs (*.md)
```

## Testing

```bash
cd api
pytest -q                    # All tests
pytest tests/test_services.py  # Service tests only
pytest -k "ssrf"             # Pattern match
```

## Database

Tables are auto-created on startup via `create_all()`. For production, migrate to Alembic.

## Environment Variables

See [README.md](README.md) for the full configuration table.

## Provider Development

All providers extend `BaseProvider` in `api/app/providers/base.py`. To add a new provider:

1. Create `api/app/providers/your_provider.py`
2. Implement `is_configured()`, `check_health()`, `fetch()`
3. Register in `api/app/services/provider_manager.py`
4. Add credential to `config.py` and `.env.example`
