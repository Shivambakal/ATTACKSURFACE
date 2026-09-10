"""Typed application configuration.

All provider credentials are optional — the application starts and
operates with deterministic-only features when credentials are absent.
Secret values are NEVER exposed through API responses, logs, or tracebacks.
"""
from __future__ import annotations

import secrets
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # ── Infrastructure ──────────────────────────────────────────────
    database_url: str = "postgresql+psycopg://attack:attack@localhost:5432/attacksurface"
    redis_url: str = "redis://localhost:6379/0"
    secret_key: str = secrets.token_urlsafe(64)

    # ── API behavior ────────────────────────────────────────────────
    app_env: str = "production"
    allowed_origins: str = "http://localhost:3000,http://localhost:8000,https://attacksurface.online,https://www.attacksurface.online"
    cors_origins: str | None = None
    cookie_domain: str | None = None
    cookie_secure: bool | None = None
    collector_user_agent: str = "AttackSurfaceTimeline/0.2 (authorized research; desk@attacksurface.online)"
    request_delay_seconds: float = 1.0
    max_pages_per_snapshot: int = 8
    app_base_url: str = "https://attacksurface.online"

    # ── Supabase Integration (Server-Side Only) ─────────────────────
    supabase_url: str | None = None
    supabase_anon_key: str | None = None
    supabase_service_role_key: str | None = None

    # ── Rate limits ─────────────────────────────────────────────────
    rate_limit_enabled: bool = True
    rate_limit_per_minute: int = 600
    rate_limit_user_per_minute: int = 1200
    rate_limit_collection_per_hour: int = 60

    # ── Provider credentials (all optional) ─────────────────────────
    github_token: str | None = None
    gemini_api_key: str | None = None
    nvidia_api_key: str | None = None
    nvd_api_key: str | None = None
    builtwith_api_key: str | None = None
    censys_api_key: str | None = None
    censys_organization_id: str | None = None
    shodan_api_key: str | None = None
    subdomains_finder_api_key: str | None = None
    domainee_api_key: str | None = None
    stackblitz_api_key: str | None = None

    # ── Monetization & Payments (Razorpay) ───────────────────────────
    razorpay_key_id: str | None = None
    razorpay_key_secret: str | None = None
    razorpay_webhook_secret: str | None = None

    # ── CISA Feed & Export Engine ────────────────────────────────────
    cisa_feed_url: str = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"
    export_storage_path: str = "data/exports"

    # ── OAuth (Google OAuth 2.0) ────────────────────────────────────
    google_client_id: str | None = None
    google_client_secret: str | None = None
    google_redirect_uri: str = "https://attacksurface.online/api/v1/auth/google/callback"

    # ── Email Infrastructure (Resend) ───────────────────────────────
    resend_api_key: str | None = None
    resend_from_email: str = "AttackSurface <noreply@attacksurface.online>"
    resend_reply_to: str = "attacksurface.alerts@gmail.com"

    # ── Provider availability helpers ───────────────────────────────
    @property
    def resend_configured(self) -> bool:
        return bool(self.resend_api_key)

    @property
    def google_oauth_configured(self) -> bool:
        return bool(self.google_client_id and self.google_client_secret)

    @property
    def github_configured(self) -> bool:
        return bool(self.github_token)

    @property
    def gemini_configured(self) -> bool:
        return bool(self.gemini_api_key)

    @property
    def nvidia_configured(self) -> bool:
        return bool(self.nvidia_api_key)

    @property
    def nvd_configured(self) -> bool:
        return bool(self.nvd_api_key)

    @property
    def builtwith_configured(self) -> bool:
        return bool(self.builtwith_api_key)

    @property
    def censys_configured(self) -> bool:
        return bool(self.censys_api_key)

    @property
    def shodan_configured(self) -> bool:
        return bool(self.shodan_api_key)

    @property
    def subdomains_finder_configured(self) -> bool:
        return bool(self.subdomains_finder_api_key)

    @property
    def domainee_configured(self) -> bool:
        return bool(self.domainee_api_key)

    @property
    def stackblitz_configured(self) -> bool:
        return bool(self.stackblitz_api_key)

    @property
    def razorpay_configured(self) -> bool:
        return bool(self.razorpay_key_id and self.razorpay_key_secret)

    @property
    def razorpay_environment(self) -> str:
        if not self.razorpay_configured:
            return "PAYMENTS NOT CONFIGURED"
        if self.razorpay_key_id and self.razorpay_key_id.startswith("rzp_test_"):
            return "TEST MODE"
        if self.razorpay_key_id and self.razorpay_key_id.startswith("rzp_live_"):
            return "LIVE MODE"
        return "CONFIGURED"

    @property
    def razorpay_status_label(self) -> str:
        if not self.razorpay_configured:
            return "PAYMENTS NOT CONFIGURED"
        if self.razorpay_key_id and self.razorpay_key_id.startswith("rzp_test_"):
            return "RAZORPAY TEST MODE"
        if self.razorpay_key_id and self.razorpay_key_id.startswith("rzp_live_"):
            return "RAZORPAY LIVE MODE"
        return "RAZORPAY CONFIGURED"

    @property
    def google_oauth_configured(self) -> bool:
        return bool(self.google_client_id and self.google_client_secret)

    @property
    def all_allowed_origins(self) -> list[str]:
        raw = f"{self.allowed_origins},{self.cors_origins or ''}"
        origins = [o.strip() for o in raw.split(",") if o.strip()]
        defaults = [
            "https://attacksurface.online",
            "https://www.attacksurface.online",
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:8000",
        ]
        for d in defaults:
            if d not in origins:
                origins.append(d)
        return origins


settings = Settings()


def _warn_if_misconfigured_database() -> None:
    """Surface the most common production outage cause: DATABASE_URL still on localhost."""
    url = (settings.database_url or "").lower()
    looks_local = any(
        host in url
        for host in ("@localhost", "@127.0.0.1", "@0.0.0.0", "@db:", "@postgres:")
    )
    if settings.app_env.lower() in {"production", "prod", "staging"} and looks_local:
        import logging

        logging.getLogger(__name__).error(
            "DATABASE_URL points at a local host (%s) while APP_ENV=%s. "
            "Auth (login/signup) will fail until DATABASE_URL is set to your "
            "managed Postgres (e.g. Supabase) connection string.",
            settings.database_url.split("@")[-1] if "@" in settings.database_url else "(redacted)",
            settings.app_env,
        )


_warn_if_misconfigured_database()
