"""Database models package.

Re-exports all models so existing imports like
``from app.models import Target`` continue to work.
"""
from .base import Base, utcnow
from .company import Company
from .security_program import (
    SecurityProgram, ProgramScopeRule, ProgramSnapshot, ProgramChangeEvent,
    InclusionType, ScopeStatus, VerificationStatus,
)
from .product import Product
from .asset_evidence import AssetEvidence
from .target import Target
from .snapshot import Snapshot, Observation
from .change import Change, ChangeEvidence
from .user import User, UserProfile, Session, OAuthAccount, VerificationToken, PasswordResetToken
from .timeline import TimelineEvent
from .evidence import Evidence
from .asset import Asset, Technology, AssetTechnology
from .feature import Feature, FeatureObservation
from .security import SecurityEvent, KevEntry, SecurityRelationshipType
from .research import ResearchNote, ResearchTask, ResearchHypothesis, ResearchBookmark, ResearchFinding
from .watchlist import WatchlistEntry
from .alert import Alert, AlertPreference
from .settings import UserSettings
from .signal import ResearchSignal, ResearchSignalFeedback, SignalType, SignalStatus, FeedbackType
from .cluster import ChangeCluster
from .api_surface import ApiSurface
from .history import HistoricalCoverage, HistoricalRelease
from .source_registry import (
    CompanySource, RawSourceSnapshot, SourceCollectionRun,
    NormalizedSourceDocument, SourceHealth, SourceType, SourceAuthorityLevel,
    SourceStatus, SourceHealthState, CompanyTrackingState,
)
from .knowledge import (
    SecurityAdvisory, VulnerabilityReference, CWEEntry, OWASPCategory,
    KnowledgeSource, KnowledgeSyncRun,
    PrivateProgram, PrivateReport, PrivateFinding, PrivateScopeRule,
    BountyEvidence,
    advisory_cwe_association, advisory_owasp_association, cwe_owasp_association,
)
from .security_intelligence import SecurityIntelligenceEvent
from .trial import TrialRun, TrialTarget
from .cisa_kev import CISAFeedSnapshot, CISAKEVItem
from .export import ExportJob, ExportType, ExportFormat, ExportStatus
from .billing import Subscription, SubscriptionTier, SubscriptionStatus, PaymentTransaction, PaymentStatus
from .email_event import EmailEvent

__all__ = [
    "Base", "utcnow",
    "Company", "SecurityProgram", "ProgramScopeRule", "ProgramSnapshot", "ProgramChangeEvent",
    "InclusionType", "ScopeStatus", "VerificationStatus",
    "Product", "AssetEvidence",
    "Target", "Snapshot", "Observation", "Change", "ChangeEvidence",
    "User", "UserProfile", "Session", "OAuthAccount", "VerificationToken", "PasswordResetToken",
    "TimelineEvent", "Evidence",
    "Asset", "Technology", "AssetTechnology",
    "Feature", "FeatureObservation",
    "SecurityEvent", "KevEntry", "SecurityRelationshipType",
    "ResearchNote", "ResearchTask", "ResearchHypothesis", "ResearchBookmark", "ResearchFinding",
    "WatchlistEntry", "Alert", "AlertPreference", "UserSettings",
    "ResearchSignal", "ResearchSignalFeedback", "SignalType", "SignalStatus", "FeedbackType",
    "ChangeCluster", "ApiSurface",
    "HistoricalCoverage", "HistoricalRelease",
    # Source Registry
    "CompanySource", "RawSourceSnapshot", "SourceCollectionRun",
    "NormalizedSourceDocument", "SourceHealth", "SourceType", "SourceAuthorityLevel",
    "SourceStatus", "SourceHealthState", "CompanyTrackingState",
    # Security Knowledge Base
    "SecurityAdvisory", "VulnerabilityReference", "CWEEntry", "OWASPCategory",
    "KnowledgeSource", "KnowledgeSyncRun",
    "PrivateProgram", "PrivateReport", "PrivateFinding", "PrivateScopeRule",
    "advisory_cwe_association", "advisory_owasp_association", "cwe_owasp_association",
    # Security Intelligence
    "SecurityIntelligenceEvent",
    "TrialRun", "TrialTarget",
    # CISA KEV
    "CISAFeedSnapshot", "CISAKEVItem",
    # Exports
    "ExportJob", "ExportType", "ExportFormat", "ExportStatus",
    # Billing
    "Subscription", "SubscriptionTier", "SubscriptionStatus", "PaymentTransaction", "PaymentStatus",
    # Email Events
    "EmailEvent",
]

