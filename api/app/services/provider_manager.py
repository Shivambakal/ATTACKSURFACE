"""Provider manager service.

Maintains the central registry of all external data and AI providers.
Coordinates concurrent health checks, aggregated data fetching, and graceful
degradation so that one failing provider never compromises the application.
Implements the Singleton pattern.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from ..providers.base import BaseProvider, NormalizedRecord, ProviderHealth, ProviderStatus
from ..providers.cisa_kev import CISAKEVProvider
from ..providers.gemini import GeminiProvider
from ..providers.github import GitHubProvider
from ..providers.nvd import NVDProvider
from ..providers.nvidia import NvidiaProvider
from ..providers.osv import OSVProvider
from ..providers.builtwith import BuiltWithProvider
from ..providers.censys import CensysProvider
from ..providers.shodan import ShodanProvider
from ..providers.domainee import DomaineeProvider
from ..providers.subdomains_finder import SubdomainsFinderProvider
from ..providers.cert_transparency import CertificateTransparencyProvider

logger = logging.getLogger(__name__)


class ProviderManager:
    """Central registry and coordinator for external data and AI providers."""

    _instance: ProviderManager | None = None

    def __new__(cls, *args: Any, **kwargs: Any) -> ProviderManager:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False  # type: ignore[attr-defined]
        return cls._instance

    def __init__(self) -> None:
        if getattr(self, "_initialized", False):
            return

        self._providers: dict[str, BaseProvider] = {}
        self.logger = logging.getLogger("service.provider_manager")

        # Register built-in providers
        self.register_provider(GitHubProvider())
        self.register_provider(GeminiProvider())
        self.register_provider(NvidiaProvider())
        self.register_provider(OSVProvider())
        self.register_provider(CISAKEVProvider())
        self.register_provider(NVDProvider())
        self.register_provider(BuiltWithProvider())
        self.register_provider(CensysProvider())
        self.register_provider(ShodanProvider())
        self.register_provider(DomaineeProvider())
        self.register_provider(SubdomainsFinderProvider())
        self.register_provider(CertificateTransparencyProvider())

        self._initialized = True

    def register_provider(self, provider: BaseProvider) -> None:
        """Register a new provider instance."""
        key = provider.name.lower().strip()
        self._providers[key] = provider
        self.logger.info("Registered provider '%s' (%s)", provider.name, type(provider).__name__)

    def get_provider(self, name: str) -> BaseProvider | None:
        """Retrieve a registered provider by name."""
        return self._providers.get(name.lower().strip())

    def list_providers(self) -> list[str]:
        """List names of all registered providers."""
        return list(self._providers.keys())

    def get_ai_provider(self) -> BaseProvider | None:
        """Select preferred configured AI provider: Gemini (primary) -> NVIDIA (secondary) -> None."""
        gemini = self.get_provider("gemini")
        if gemini and gemini.is_configured():
            return gemini

        nvidia = self.get_provider("nvidia")
        if nvidia and nvidia.is_configured():
            return nvidia

        return None

    async def health_check_all(self) -> list[ProviderHealth]:
        """Run health checks across all registered providers concurrently.

        Isolated: errors in one check do not impact others.
        """
        tasks: list[asyncio.Task[ProviderHealth]] = []
        providers_list = list(self._providers.values())

        async def _check_safe(prov: BaseProvider) -> ProviderHealth:
            try:
                return await prov.safe_health()
            except Exception as exc:
                self.logger.warning("Unexpected error during health check for '%s': %s", prov.name, type(exc).__name__)
                return ProviderHealth(
                    name=prov.name,
                    status=ProviderStatus.FAILED,
                    error_summary=type(exc).__name__,
                    recommended_fix="Check provider configuration and network connectivity.",
                )

        results = await asyncio.gather(*[_check_safe(p) for p in providers_list], return_exceptions=False)
        return list(results)

    async def fetch_from_all(self, target: str, **kwargs: Any) -> list[NormalizedRecord]:
        """Fetch and aggregate normalized records across providers with graceful degradation.

        Args:
            target: The domain, repository, or target string.
            **kwargs: Provider-specific options:
                providers (list[str]): Optional list of specific provider names to run.
                include_ai (bool): Whether to run generative AI providers (default: False).
                packages (list[dict]): Packages for vulnerability checks.
                cves (list[str]): Specific CVEs to query.
        """
        selected_names: list[str] | None = kwargs.get("providers")
        include_ai: bool = bool(kwargs.get("include_ai", False))

        if selected_names:
            target_providers = [
                self._providers[name.lower()] for name in selected_names if name.lower() in self._providers
            ]
        else:
            # By default, query intelligence/data providers: github, osv, cisa_kev, nvd
            # Generative AI providers require content/evidence inputs and are invoked selectively
            default_names = ["github", "osv", "cisa_kev", "nvd"]
            if include_ai:
                default_names.extend(["gemini", "nvidia"])
            target_providers = [
                self._providers[name] for name in default_names if name in self._providers
            ]

        async def _safe_fetch(prov: BaseProvider) -> list[NormalizedRecord]:
            try:
                return await prov.fetch(target=target, **kwargs)
            except Exception as exc:
                self.logger.warning("Provider '%s' failed during fetch: %s", prov.name, type(exc).__name__)
                return []

        fetch_results = await asyncio.gather(*[_safe_fetch(p) for p in target_providers], return_exceptions=True)

        aggregated: list[NormalizedRecord] = []
        for res in fetch_results:
            if isinstance(res, list):
                aggregated.extend(res)
            elif isinstance(res, Exception):
                self.logger.warning("Provider fetch exception: %s", type(res).__name__)

        return aggregated


# Global singleton instance
provider_manager = ProviderManager()


def get_provider_manager() -> ProviderManager:
    """Dependency injector / accessor for ProviderManager singleton."""
    return provider_manager
