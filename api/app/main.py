"""AttackSurface Timeline — Application factory.

Registers all routers, middleware, and startup hooks.
The old monolithic route handlers have been moved to individual
router modules under ``app.routers``.
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .db import engine
from .models.base import Base
# Import all models so SQLAlchemy registers them before create_all
from .models import (  # noqa: F401
    Company, SecurityProgram, ProgramScopeRule, Product, AssetEvidence,
    Target, Snapshot, Observation, Change, ChangeEvidence,
    User, UserProfile, Session, OAuthAccount, VerificationToken, PasswordResetToken,
    TimelineEvent, Evidence, Asset, Technology, AssetTechnology,
    Feature, FeatureObservation, SecurityEvent, KevEntry,
    ResearchNote, ResearchTask, ResearchHypothesis, ResearchBookmark, ResearchFinding,
    WatchlistEntry, Alert, AlertPreference, UserSettings,
    ResearchSignal, ResearchSignalFeedback, ChangeCluster, ApiSurface,
    TrialRun, TrialTarget,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Ensure database migrations, admin accounts, and startup hooks."""
    import os
    if not os.environ.get("PYTEST_CURRENT_TEST"):
        try:
            from .db_migrate import run_database_migrations
            active_version = run_database_migrations()
            logger.info("Database schema and alembic_version verified at: %s", active_version)
            from .provision_admin import ensure_default_owner
            ensure_default_owner()
            logger.info("Default admin/owner accounts verified and provisioned")
        except Exception as exc:
            logger.warning("Database migration or provisioning skipped on lifespan startup: %s", exc)
    yield




def create_app() -> FastAPI:
    """Application factory."""
    application = FastAPI(
        title="AttackSurface Timeline",
        description="Bug Bounty Research Intelligence Platform",
        version="0.2.0",
        lifespan=lifespan,
    )

    # ── Rate limiting (inner middleware) ────────────────────────────
    try:
        from .middleware.rate_limit import RateLimitMiddleware
        application.add_middleware(RateLimitMiddleware)
    except Exception:
        logger.warning("Rate limiting middleware not loaded (Redis may be unavailable)")

    # ── CORS (outermost middleware to wrap all responses) ───────────
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.all_allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Register API v1 routers ─────────────────────────────────────
    try:
        from .routers.auth import router as auth_router
        from .routers.targets import router as targets_router
        from .routers.snapshots import router as snapshots_router
        from .routers.changes import router as changes_router
        from .routers.timeline import router as timeline_router
        from .routers.research import router as research_router
        from .routers.watchlist import router as watchlist_router
        from .routers.alerts import router as alerts_router
        from .routers.signals import router as signals_router
        from .routers.companies import router as companies_router
        from .routers.history import router as history_router
        from .routers.search import router as search_router
        from .routers.profile import router as profile_router
        from .routers.settings_router import router as settings_router
        from .routers.health import router as health_router
        from .routers.security_knowledge import router as security_knowledge_router

        from .routers.sources import router as sources_router
        from .routers.corporate_intelligence import router as corporate_intelligence_router
        from .routers.security_intelligence_router import router as security_intelligence_router
        from .routers.admin_router import router as admin_router
        from .routers.trial import router as trial_router
        from .routers.live_intelligence import router as live_intelligence_router

        from .routers.exports import router as exports_router
        from .routers.billing import router as billing_router
        from .routers.programs import router as programs_router

        application.include_router(auth_router)
        application.include_router(admin_router)
        application.include_router(exports_router)
        application.include_router(billing_router)
        application.include_router(trial_router)
        application.include_router(live_intelligence_router)
        application.include_router(sources_router)
        application.include_router(corporate_intelligence_router)
        application.include_router(security_intelligence_router)
        application.include_router(companies_router)
        application.include_router(programs_router)
        application.include_router(history_router)
        application.include_router(security_knowledge_router)
        application.include_router(targets_router)
        application.include_router(snapshots_router)
        application.include_router(changes_router)
        application.include_router(signals_router)
        application.include_router(timeline_router)
        application.include_router(research_router)
        application.include_router(watchlist_router)
        application.include_router(alerts_router)
        application.include_router(search_router)
        application.include_router(profile_router)
        application.include_router(settings_router)
        application.include_router(health_router)
        logger.info("All API v1 routers registered")

    except Exception as exc:
        logger.error("Failed to register routers: %s", exc)
        raise

    return application


app = create_app()
