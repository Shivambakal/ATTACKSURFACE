"""Entity Resolution Service.

Implements strict verification chains for external repositories, packages,
and documents before any external finding is attributed to a company or target.

Enforces:
- PUBLIC != COMPANY OWNERSHIP.
- Requires explicit entity-resolution evidence.
- Third-party repositories (e.g. Senavia-Corp on Vercel, SemiAnalysisAI on AMD)
  are classified as UNVERIFIED (CONTEXT_ONLY / CANDIDATE) and never as
  CONFIRMED company changes or new public pages.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# Known verified GitHub organizations for major tech entities
KNOWN_COMPANY_GITHUB_ORGS: dict[str, set[str]] = {
    "vercel.com": {"vercel", "zeit", "nextjs", "turborepo", "swc-project"},
    "google.com": {"google", "googlecloudplatform", "google-deepmind", "golang", "kubernetes", "tensorflow", "chromium", "angular"},
    "microsoft.com": {"microsoft", "azure", "dotnet", "typescript", "powershell", "visualstudio", "github"},
    "apple.com": {"apple", "swiftlang", "webkit"},
    "amazon.com": {"aws", "awslabs", "amzn", "amazonwebservices", "opensearch-project"},
    "meta.com": {"facebook", "meta", "facebookresearch", "pytorch", "reactjs", "flowtype"},
    "amd.com": {"amd", "rocm", "rocm-developer-tools", "gpuopen-librariesandsdks", "gpuopen-tools"},
    "nvidia.com": {"nvidia", "rapidsai", "triton-inference-server"},
    "cloudflare.com": {"cloudflare"},
    "github.com": {"github", "githubdocs", "actions"},
    "openai.com": {"openai"},
    "netflix.com": {"netflix", "netflix-skunkworks"},
    "spotify.com": {"spotify"},
    "uber.com": {"uber", "uber-go", "uber-archive"},
    "airbnb.com": {"airbnb", "lottie-react-native"},
    "stripe.com": {"stripe", "stripe-archive"},
    "datadog.com": {"datadog"},
    "datadoghq.com": {"datadog"},
    "splunk.com": {"splunk"},
    "elastic.co": {"elastic"},
    "mongodb.com": {"mongodb"},
    "snowflake.com": {"snowflakedb"},
    "atlassian.com": {"atlassian"},
    "gitlab.com": {"gitlab-org", "gitlab-com"},
    "hashicorp.com": {"hashicorp"},
    "docker.com": {"docker"},
    "tailscale.com": {"tailscale"},
}


@dataclass
class EntityResolutionResult:
    is_confirmed_owner: bool
    entity_relationship: str  # "CONFIRMED_OWNER", "UNVERIFIED", "COMMUNITY_PROJECT", "UNKNOWN"
    confidence: float
    evidence: str
    timeline_eligible: bool
    quality_badge: str  # "CONFIRMED_HISTORY", "CANDIDATE", "CONTEXT_ONLY", "REJECTED"


class EntityResolutionService:
    """Evaluates whether an external resource is legitimately owned and operated by the target company."""

    @classmethod
    def resolve_github_repository(
        cls,
        company_name: str,
        canonical_domain: str,
        aliases: list[str] | None,
        repo_full_name: str,
        repo_metadata: dict[str, Any] | None = None,
    ) -> EntityResolutionResult:
        """Evaluates a GitHub repository against company identity through multi-factor entity resolution."""
        if not repo_full_name or "/" not in repo_full_name:
            return EntityResolutionResult(
                is_confirmed_owner=False,
                entity_relationship="UNVERIFIED",
                confidence=0.1,
                evidence="Malformed repository identifier",
                timeline_eligible=False,
                quality_badge="REJECTED",
            )

        owner, repo_name = repo_full_name.split("/", 1)
        owner_clean = owner.lower().strip()
        repo_clean = repo_name.lower().strip()
        domain_clean = canonical_domain.lower().strip()
        metadata = repo_metadata or {}

        # 1. Build allowed owner identities from verified company data
        allowed_owners: set[str] = set()

        # Domain root name (e.g. "vercel" from "vercel.com")
        domain_root = domain_clean.split(".")[0]
        if len(domain_root) >= 3:
            allowed_owners.add(domain_root)

        # Company name normalized
        c_clean = re.sub(r"[^a-z0-9]", "", company_name.lower())
        if len(c_clean) >= 3:
            allowed_owners.add(c_clean)

        # Verified aliases
        for alias in aliases or []:
            a_clean = re.sub(r"[^a-z0-9]", "", alias.lower())
            if len(a_clean) >= 3:
                allowed_owners.add(a_clean)

        # Pre-seeded authoritative known organizations
        if domain_clean in KNOWN_COMPANY_GITHUB_ORGS:
            allowed_owners.update(KNOWN_COMPANY_GITHUB_ORGS[domain_clean])

        # 2. Check direct owner match
        owner_norm = re.sub(r"[^a-z0-9]", "", owner_clean)
        if owner_norm in allowed_owners:
            return EntityResolutionResult(
                is_confirmed_owner=True,
                entity_relationship="CONFIRMED_OWNER",
                confidence=0.98,
                evidence=f"GitHub organization '{owner}' directly matches verified entity identity '{company_name}'",
                timeline_eligible=True,
                quality_badge="CONFIRMED_HISTORY",
            )

        # 3. Check official homepage in repository metadata
        homepage = (metadata.get("homepage") or "").strip().lower()
        if homepage:
            try:
                parsed_hp = urlparse(homepage if "://" in homepage else f"https://{homepage}")
                hp_netloc = parsed_hp.netloc.lower()
                if hp_netloc == domain_clean or hp_netloc.endswith(f".{domain_clean}"):
                    return EntityResolutionResult(
                        is_confirmed_owner=True,
                        entity_relationship="CONFIRMED_OWNER",
                        confidence=0.95,
                        evidence=f"Repository homepage '{homepage}' points directly to canonical domain '{domain_clean}'",
                        timeline_eligible=True,
                        quality_badge="CONFIRMED_HISTORY",
                    )
            except Exception:
                pass

        # 4. Check negative match / third-party indicators
        evidence = (
            f"GitHub owner '{owner}' is an independent third-party entity. "
            f"No verified corporate ownership link established for '{company_name}' ({domain_clean})."
        )
        logger.info(
            "Entity Resolution Gate: Unverified GitHub repository %s for %s (%s)",
            repo_full_name, company_name, domain_clean
        )

        return EntityResolutionResult(
            is_confirmed_owner=False,
            entity_relationship="UNVERIFIED",
            confidence=0.25,
            evidence=evidence,
            timeline_eligible=False,
            quality_badge="CANDIDATE",
        )

    @classmethod
    def is_external_third_party_url(cls, canonical_domain: str, url: str) -> bool:
        """Determines if a URL belongs to an external platform (GitHub, NPM, DockerHub, etc.) rather than the target's web domain."""
        if not url:
            return False
        try:
            parsed = urlparse(url)
            netloc = parsed.netloc.lower()
            domain_clean = canonical_domain.lower().strip()

            # If it matches the target's domain or a subdomain, it is first-party
            if netloc == domain_clean or netloc.endswith(f".{domain_clean}"):
                return False

            external_hosts = {
                "github.com",
                "gitlab.com",
                "bitbucket.org",
                "hub.docker.com",
                "npmjs.com",
                "pypi.org",
                "crates.io",
                "twitter.com",
                "x.com",
                "linkedin.com",
            }
            return any(host in netloc for host in external_hosts)
        except Exception:
            return False
