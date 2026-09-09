"""Abstract provider interface and stub implementations for the Security Knowledge Base."""
from __future__ import annotations

import abc
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from sqlalchemy.orm import Session


# ---------------------------------------------------------------------------
# Provider Status Enum
# ---------------------------------------------------------------------------

class ProviderStatus(str, Enum):
    """Operational status of a knowledge provider."""

    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNAVAILABLE = "UNAVAILABLE"
    NOT_IMPLEMENTED = "NOT_IMPLEMENTED"
    ERROR = "ERROR"


# ---------------------------------------------------------------------------
# Health Report Dataclass
# ---------------------------------------------------------------------------

@dataclass
class ProviderHealthReport:
    """Structured health report returned by provider.health()."""

    provider: str
    status: ProviderStatus
    message: str = ""
    checked_at: datetime = field(default_factory=datetime.utcnow)
    details: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Abstract Base Class
# ---------------------------------------------------------------------------

class SecurityKnowledgeProvider(abc.ABC):
    """Abstract contract that every knowledge-base provider must implement.

    Subclasses should override all abstract methods and provide a concrete
    implementation of the fetch → validate → normalize → upsert pipeline.
    """

    @property
    @abc.abstractmethod
    def source_name(self) -> str:
        """Canonical name identifying this provider (e.g., 'CISA_KEV', 'NVD')."""

    @abc.abstractmethod
    def fetch(self, **kwargs: Any) -> Any:
        """Retrieve raw data from the upstream source.

        Returns the raw payload (dict, list, or file path) ready for validation.
        """

    @abc.abstractmethod
    def validate(self, raw: Any) -> tuple[bool, str]:
        """Validate that the raw payload has the expected structure.

        Returns (is_valid, reason_message).
        """

    @abc.abstractmethod
    def normalize(self, raw: Any) -> list[dict[str, Any]]:
        """Transform raw provider records into canonical advisory dicts.

        Returns a list of normalized record dicts ready for upsert.
        """

    @abc.abstractmethod
    def upsert(self, db: Session, records: list[dict[str, Any]], **kwargs: Any) -> dict[str, int]:
        """Persist (insert or update) records into the database.

        Returns counters: {'created': N, 'updated': N, 'skipped': N, 'failed': N}.
        """

    @abc.abstractmethod
    def health(self) -> ProviderHealthReport:
        """Return the current operational health of this provider."""


# ---------------------------------------------------------------------------
# Stub Implementations
# ---------------------------------------------------------------------------

class NVDProvider(SecurityKnowledgeProvider):
    """Stub: National Vulnerability Database (NIST NVD) provider."""

    @property
    def source_name(self) -> str:
        return "NVD"

    def fetch(self, **kwargs: Any) -> Any:
        raise NotImplementedError("NVDProvider.fetch is not yet implemented.")

    def validate(self, raw: Any) -> tuple[bool, str]:
        raise NotImplementedError("NVDProvider.validate is not yet implemented.")

    def normalize(self, raw: Any) -> list[dict[str, Any]]:
        raise NotImplementedError("NVDProvider.normalize is not yet implemented.")

    def upsert(self, db: Session, records: list[dict[str, Any]], **kwargs: Any) -> dict[str, int]:
        raise NotImplementedError("NVDProvider.upsert is not yet implemented.")

    def health(self) -> ProviderHealthReport:
        return ProviderHealthReport(
            provider=self.source_name,
            status=ProviderStatus.NOT_IMPLEMENTED,
            message="NVD provider is not yet implemented.",
        )


class OSVProvider(SecurityKnowledgeProvider):
    """Stub: Open Source Vulnerabilities (OSV.dev) provider."""

    @property
    def source_name(self) -> str:
        return "OSV"

    def fetch(self, **kwargs: Any) -> Any:
        raise NotImplementedError("OSVProvider.fetch is not yet implemented.")

    def validate(self, raw: Any) -> tuple[bool, str]:
        raise NotImplementedError("OSVProvider.validate is not yet implemented.")

    def normalize(self, raw: Any) -> list[dict[str, Any]]:
        raise NotImplementedError("OSVProvider.normalize is not yet implemented.")

    def upsert(self, db: Session, records: list[dict[str, Any]], **kwargs: Any) -> dict[str, int]:
        raise NotImplementedError("OSVProvider.upsert is not yet implemented.")

    def health(self) -> ProviderHealthReport:
        return ProviderHealthReport(
            provider=self.source_name,
            status=ProviderStatus.NOT_IMPLEMENTED,
            message="OSV provider is not yet implemented.",
        )


class GitHubAdvisoryProvider(SecurityKnowledgeProvider):
    """Stub: GitHub Security Advisory (GHSA) provider."""

    @property
    def source_name(self) -> str:
        return "GHSA"

    def fetch(self, **kwargs: Any) -> Any:
        raise NotImplementedError("GitHubAdvisoryProvider.fetch is not yet implemented.")

    def validate(self, raw: Any) -> tuple[bool, str]:
        raise NotImplementedError("GitHubAdvisoryProvider.validate is not yet implemented.")

    def normalize(self, raw: Any) -> list[dict[str, Any]]:
        raise NotImplementedError("GitHubAdvisoryProvider.normalize is not yet implemented.")

    def upsert(self, db: Session, records: list[dict[str, Any]], **kwargs: Any) -> dict[str, int]:
        raise NotImplementedError("GitHubAdvisoryProvider.upsert is not yet implemented.")

    def health(self) -> ProviderHealthReport:
        return ProviderHealthReport(
            provider=self.source_name,
            status=ProviderStatus.NOT_IMPLEMENTED,
            message="GitHub Advisory provider is not yet implemented.",
        )


class OWASPProvider(SecurityKnowledgeProvider):
    """Stub: OWASP taxonomy provider."""

    @property
    def source_name(self) -> str:
        return "OWASP"

    def fetch(self, **kwargs: Any) -> Any:
        raise NotImplementedError("OWASPProvider.fetch is not yet implemented.")

    def validate(self, raw: Any) -> tuple[bool, str]:
        raise NotImplementedError("OWASPProvider.validate is not yet implemented.")

    def normalize(self, raw: Any) -> list[dict[str, Any]]:
        raise NotImplementedError("OWASPProvider.normalize is not yet implemented.")

    def upsert(self, db: Session, records: list[dict[str, Any]], **kwargs: Any) -> dict[str, int]:
        raise NotImplementedError("OWASPProvider.upsert is not yet implemented.")

    def health(self) -> ProviderHealthReport:
        return ProviderHealthReport(
            provider=self.source_name,
            status=ProviderStatus.NOT_IMPLEMENTED,
            message="OWASP provider is not yet implemented.",
        )


class CWEProvider(SecurityKnowledgeProvider):
    """Stub: MITRE CWE taxonomy provider."""

    @property
    def source_name(self) -> str:
        return "CWE"

    def fetch(self, **kwargs: Any) -> Any:
        raise NotImplementedError("CWEProvider.fetch is not yet implemented.")

    def validate(self, raw: Any) -> tuple[bool, str]:
        raise NotImplementedError("CWEProvider.validate is not yet implemented.")

    def normalize(self, raw: Any) -> list[dict[str, Any]]:
        raise NotImplementedError("CWEProvider.normalize is not yet implemented.")

    def upsert(self, db: Session, records: list[dict[str, Any]], **kwargs: Any) -> dict[str, int]:
        raise NotImplementedError("CWEProvider.upsert is not yet implemented.")

    def health(self) -> ProviderHealthReport:
        return ProviderHealthReport(
            provider=self.source_name,
            status=ProviderStatus.NOT_IMPLEMENTED,
            message="CWE provider is not yet implemented.",
        )


__all__ = [
    "ProviderStatus",
    "ProviderHealthReport",
    "SecurityKnowledgeProvider",
    "NVDProvider",
    "OSVProvider",
    "GitHubAdvisoryProvider",
    "OWASPProvider",
    "CWEProvider",
]
