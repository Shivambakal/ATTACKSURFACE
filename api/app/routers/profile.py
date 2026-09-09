"""User profile router."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import User, UserProfile, utcnow
from app.routers.deps import get_current_user
from app.schemas import ProfileOut, ProfileUpdate
from app.services.identity_verification import (
    verify_github_handle,
    verify_domain,
    verify_bounty_handle,
)

router = APIRouter(prefix="/api/v1/profile", tags=["profile"])


def _get_or_create_profile(user: User, db: Session) -> UserProfile:
    if user.profile:
        return user.profile

    profile = db.query(UserProfile).filter_by(user_id=user.id).first()
    if not profile:
        profile = UserProfile(user_id=user.id)
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return profile


@router.get("", response_model=ProfileOut)
@router.get("/", response_model=ProfileOut, include_in_schema=False)
def get_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserProfile:
    """Get the current user's profile."""
    return _get_or_create_profile(current_user, db)


@router.put("", response_model=ProfileOut)
@router.put("/", response_model=ProfileOut, include_in_schema=False)
def update_profile(
    body: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserProfile:
    """Update current user profile information."""
    profile = _get_or_create_profile(current_user, db)

    # Check for username conflict if changing username
    if body.username is not None and body.username != profile.username:
        normalized_username = body.username.strip()
        existing = (
            db.query(UserProfile)
            .filter(
                UserProfile.username == normalized_username,
                UserProfile.user_id != current_user.id,
            )
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken",
            )
        profile.username = normalized_username

    if body.display_name is not None:
        profile.display_name = body.display_name
    if body.bio is not None:
        profile.bio = body.bio
    if body.country is not None:
        profile.country = body.country
    if body.timezone is not None:
        profile.timezone = body.timezone
    if body.language is not None:
        profile.language = body.language
    if body.researcher_type is not None:
        profile.researcher_type = body.researcher_type
    if body.experience_level is not None:
        profile.experience_level = body.experience_level
    if body.favorite_vuln_classes is not None:
        profile.favorite_vuln_classes = body.favorite_vuln_classes
    if body.favorite_technologies is not None:
        profile.favorite_technologies = body.favorite_technologies
    if body.public_profile is not None:
        profile.public_profile = body.public_profile
    if body.handles is not None:
        profile.handles = body.handles

    profile.updated_at = utcnow()
    db.commit()
    db.refresh(profile)
    return profile


from pydantic import BaseModel
from typing import Any


class OnboardingRequest(BaseModel):
    researcher_type: str | None = None
    main_purpose: str | None = None
    preferred_intelligence: list[str] | None = None
    experience_level: str | None = None
    targets_of_interest: list[str] | None = None


@router.post("/onboarding")
def complete_onboarding(
    payload: OnboardingRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Persists 6-step researcher onboarding choices to user profile."""
    profile = _get_or_create_profile(current_user, db)

    if payload.researcher_type:
        profile.researcher_type = payload.researcher_type
    if payload.experience_level:
        profile.experience_level = payload.experience_level

    handles = profile.handles or {}
    handles["onboarding"] = {
        "completed": True,
        "completed_at": utcnow().isoformat(),
        "main_purpose": payload.main_purpose,
        "preferred_intelligence": payload.preferred_intelligence or [],
        "targets_of_interest": payload.targets_of_interest or [],
    }
    profile.handles = handles
    profile.updated_at = utcnow()
    db.commit()

    return {
        "status": "success",
        "onboarding_completed": True,
        "researcher_type": profile.researcher_type,
        "experience_level": profile.experience_level,
        "preferences": handles["onboarding"],
    }


@router.get("/preferences")
def get_preferences(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Returns researcher presentation preferences for dashboard personalization."""
    profile = _get_or_create_profile(current_user, db)
    handles = profile.handles or {}
    onboarding = handles.get("onboarding", {})

    return {
        "onboarding_completed": bool(onboarding.get("completed", False)),
        "researcher_type": profile.researcher_type or "Security researcher",
        "experience_level": profile.experience_level or "Intermediate",
        "main_purpose": onboarding.get("main_purpose", "Find new attack surface"),
        "preferred_intelligence": onboarding.get("preferred_intelligence", ["vulnerabilities", "new_assets", "timelines"]),
        "targets_of_interest": onboarding.get("targets_of_interest", []),
    }


class VerifyHandleRequest(BaseModel):
    platform: str
    handle: str


@router.post("/verify-handle")
async def verify_user_handle(
    payload: VerifyHandleRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Live verification of researcher handle or personal domain without synthetic data."""
    plat = payload.platform.lower().strip()
    if plat == "github":
        result = await verify_github_handle(payload.handle)
    elif plat in ("website", "domain"):
        result = await verify_domain(payload.handle)
    elif plat in ("hackerone", "bugcrowd"):
        result = await verify_bounty_handle(plat, payload.handle)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported platform '{payload.platform}'. Supported: github, website, hackerone, bugcrowd.",
        )

    # Persist verification result to user profile handles
    profile = _get_or_create_profile(current_user, db)
    handles = dict(profile.handles or {})
    verified_map = dict(handles.get("verified") or {})
    verified_map[plat] = result
    handles["verified"] = verified_map
    profile.handles = handles
    profile.updated_at = utcnow()
    db.commit()

    return result

