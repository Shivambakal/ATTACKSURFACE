"""Expanded Pydantic schemas for the AttackSurface Timeline API."""
from __future__ import annotations

from datetime import datetime, date
from pydantic import BaseModel, Field, EmailStr, ConfigDict


# ── Auth ────────────────────────────────────────────────────────────

class SignupRequest(BaseModel):
    email: str
    password: str = Field(min_length=8, max_length=128)

class LoginRequest(BaseModel):
    email: str
    password: str

class PasswordResetRequest(BaseModel):
    email: str

class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)

class VerifyEmailRequest(BaseModel):
    token: str

class UserOut(BaseModel):
    id: int
    email: str
    role: str = "RESEARCHER"
    is_active: bool
    is_verified: bool
    is_admin: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class AdminUserOut(BaseModel):
    id: int
    email: str
    role: str
    is_admin: bool
    is_active: bool
    is_verified: bool
    created_at: datetime
    session_count: int = 0
    model_config = ConfigDict(from_attributes=True)


class UserRoleUpdate(BaseModel):
    role: str
    is_admin: bool | None = None


class AdminAuditOut(BaseModel):
    id: int | str
    action: str
    actor: str
    target: str | None = None
    detail: str | None = None
    timestamp: datetime
    ip_address: str | None = None


# ── Target ──────────────────────────────────────────────────────────

class TargetCreate(BaseModel):
    domain: str = Field(pattern=r"^[a-zA-Z0-9.-]+$")
    company: str | None = None
    company_name: str | None = None
    program_source: str | None = "Direct Authorization"
    authorization_source: str | None = None
    scope: list[str] | None = None
    scope_type: str | None = "DOMAIN"
    notes: str | None = None
    authorization_confirmed: bool = True


class BulkImportResponse(BaseModel):
    total_imported: int
    imported_count: int = 0
    total_targets: int = 0
    targets: list[str]
    message: str


class TargetOut(BaseModel):
    id: int
    domain: str
    company_id: int | None = None
    company_name: str | None = None
    program_source: str | None = None
    authorization_source: str | None = None
    scope: list[str] | None = None
    scope_type: str | None = None
    notes: str | None = None
    authorization_record: dict | None = None
    authorization_confirmed: bool
    monitoring_status: str = "active"
    last_visited_at: datetime | None = None
    created_at: datetime
    class Config:
        from_attributes = True


# ── Snapshot ────────────────────────────────────────────────────────

class SnapshotOut(BaseModel):
    id: int
    collected_at: datetime
    status: str
    error: str | None = None
    class Config:
        from_attributes = True


# ── Change ──────────────────────────────────────────────────────────

class ChangeOut(BaseModel):
    id: int
    category: str
    summary: str
    security_relevance: int
    confidence: float
    priority: str = "MEDIUM"
    status: str = "interesting"
    source_url: str
    detected_at: datetime
    score_factors: dict | None = None
    class Config:
        from_attributes = True

class ChangeStatusUpdate(BaseModel):
    status: str = Field(pattern="^(interesting|investigating|ignored|resolved)$")


# ── Timeline ────────────────────────────────────────────────────────

class TimelineEventOut(BaseModel):
    id: int
    event_type: str
    title: str
    summary: str
    source: str
    source_url: str | None = None
    observed_at: datetime
    published_at: datetime | None = None
    confidence: float
    relevance_score: int
    priority: str
    class Config:
        from_attributes = True


# ── Research ────────────────────────────────────────────────────────

class NoteCreate(BaseModel):
    title: str = Field(max_length=255)
    body: str | None = None
    tags: list[str] | None = None
    target_id: int | None = None
    linked_change_id: int | None = None
    linked_asset_id: int | None = None
    linked_evidence_id: int | None = None

class NoteOut(BaseModel):
    id: int
    title: str
    body: str | None = None
    tags: list | None = None
    target_id: int | None = None
    created_at: datetime
    updated_at: datetime
    class Config:
        from_attributes = True

class NoteUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=255)
    body: str | None = None
    tags: list[str] | None = None
    target_id: int | None = None
    linked_change_id: int | None = None
    linked_asset_id: int | None = None
    linked_evidence_id: int | None = None

class TaskCreate(BaseModel):
    title: str = Field(max_length=255)
    description: str | None = None
    priority: str = "MEDIUM"
    due_date: date | None = None
    target_id: int | None = None
    related_change_id: int | None = None

class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=255)
    description: str | None = None
    status: str | None = None
    priority: str | None = None
    due_date: date | None = None

class TaskOut(BaseModel):
    id: int
    title: str
    description: str | None = None
    status: str
    priority: str
    due_date: date | None = None
    target_id: int | None = None
    created_at: datetime
    class Config:
        from_attributes = True

class FindingCreate(BaseModel):
    title: str = Field(max_length=255)
    description: str | None = None
    severity: str | None = None
    target_id: int | None = None
    evidence_ids: list[int] | None = None
    change_ids: list[int] | None = None

class FindingUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=255)
    description: str | None = None
    severity: str | None = None
    status: str | None = None
    evidence_ids: list[int] | None = None
    change_ids: list[int] | None = None

class FindingOut(BaseModel):
    id: int
    title: str
    description: str | None = None
    severity: str | None = None
    status: str
    target_id: int | None = None
    created_at: datetime
    class Config:
        from_attributes = True


# ── Watchlist ───────────────────────────────────────────────────────

class WatchlistAdd(BaseModel):
    entity_type: str
    entity_id: int

class WatchlistOut(BaseModel):
    id: int
    entity_type: str
    entity_id: int
    created_at: datetime
    class Config:
        from_attributes = True


# ── Alert ───────────────────────────────────────────────────────────

class AlertOut(BaseModel):
    id: int
    alert_type: str
    title: str
    summary: str | None = None
    priority: str
    read: bool
    created_at: datetime
    class Config:
        from_attributes = True

class AlertPreferenceUpdate(BaseModel):
    alert_type: str
    frequency: str = "instant"


# ── Profile ─────────────────────────────────────────────────────────

class ProfileUpdate(BaseModel):
    display_name: str | None = None
    username: str | None = None
    bio: str | None = None
    country: str | None = None
    timezone: str | None = None
    language: str | None = None
    researcher_type: str | None = None
    experience_level: str | None = None
    favorite_vuln_classes: list[str] | None = None
    favorite_technologies: list[str] | None = None
    public_profile: bool | None = None
    handles: dict | None = None

class ProfileOut(BaseModel):
    display_name: str | None = None
    username: str | None = None
    bio: str | None = None
    country: str | None = None
    timezone: str | None = None
    researcher_type: str | None = None
    public_profile: bool = False
    handles: dict | None = None
    class Config:
        from_attributes = True


# ── Settings ────────────────────────────────────────────────────────

class SettingsUpdate(BaseModel):
    appearance: dict | None = None
    notifications: dict | None = None
    research: dict | None = None
    privacy: dict | None = None

class SettingsOut(BaseModel):
    appearance: dict | None = None
    notifications: dict | None = None
    research: dict | None = None
    privacy: dict | None = None
    class Config:
        from_attributes = True

class SessionOut(BaseModel):
    id: int
    ip_address: str | None = None
    user_agent: str | None = None
    created_at: datetime
    expires_at: datetime
    is_current: bool = False
    class Config:
        from_attributes = True


# ── Provider Health ─────────────────────────────────────────────────

class ProviderHealthOut(BaseModel):
    name: str
    status: str
    error_summary: str | None = None
    recommended_fix: str | None = None


# ── Pagination ──────────────────────────────────────────────────────

class PaginatedResponse(BaseModel):
    items: list
    total: int
    page: int
    page_size: int
    pages: int
