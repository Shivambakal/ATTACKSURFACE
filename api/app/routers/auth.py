"""Authentication router."""
from __future__ import annotations

from typing import Any
import hashlib
import logging
import urllib.parse
import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.models import OAuthAccount, PasswordResetToken, User, UserProfile, UserSettings
from app.routers.deps import get_current_user
from app.schemas import (
    LoginRequest,
    PasswordResetConfirm,
    PasswordResetRequest,
    SignupRequest,
    UserOut,
    VerifyEmailRequest,
)
from app.services.auth import (
    _is_expired,
    create_password_reset_token,
    create_session,
    create_user,
    create_verification_token,
    reset_password,
    revoke_all_sessions,
    revoke_session,
    verify_email,
    verify_password,
)
from app.services.email import email_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

SESSION_COOKIE_NAME = "session_token"
SESSION_MAX_AGE_SECONDS = 7 * 24 * 3600  # 7 days


def _raise_auth_storage_unavailable(exc: Exception) -> None:
    """Convert database outages into a clear client-facing 503 instead of a bare 500."""
    logger.exception("Auth storage unavailable: %s", type(exc).__name__)
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=(
            "Authentication service is temporarily unavailable (database unreachable). "
            "Please try again shortly."
        ),
    ) from exc


def _set_session_cookie(response: Response, token: str) -> None:
    is_https = (
        settings.cookie_secure
        if settings.cookie_secure is not None
        else (settings.app_base_url.startswith("https://") or settings.app_env == "production")
    )
    cookie_kwargs: dict[str, Any] = {
        "key": SESSION_COOKIE_NAME,
        "value": token,
        "httponly": True,
        "secure": is_https,
        "samesite": "lax",
        "max_age": SESSION_MAX_AGE_SECONDS,
        "path": "/",
    }
    if settings.cookie_domain:
        cookie_kwargs["domain"] = settings.cookie_domain
    response.set_cookie(**cookie_kwargs)


@router.post("/signup", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def signup(
    body: SignupRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> User:
    """Create a new user account, establish a session, and set session cookie."""
    try:
        normalized_email = body.email.lower().strip()
        existing = db.query(User).filter_by(email=normalized_email).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )

        user = create_user(db, email=normalized_email, password=body.password)

        # Dispatch welcome & verification emails via Resend
        try:
            v_token = create_verification_token(db, user.id, hours=48)
            email_service.send_welcome_email(
                to=user.email,
                display_name=user.email.split("@")[0],
                user_id=user.id,
                db=db,
            )
            email_service.send_email_verification_email(
                to=user.email,
                verification_token=v_token,
                user_id=user.id,
                db=db,
            )
        except Exception as exc:
            logger.warning("Failed to dispatch signup emails: %s", exc)

        client_ip = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")
        token = create_session(db, user, ip_address=client_ip, user_agent=user_agent)
        _set_session_cookie(response, token)

        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
        return user
    except HTTPException:
        raise
    except (OperationalError, SQLAlchemyError) as exc:
        _raise_auth_storage_unavailable(exc)
    except Exception as exc:
        # Catch unexpected infra failures (e.g. bcrypt/runtime) so clients never see a blank 500.
        logger.exception("Signup failed: %s", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Account registration failed. Please try again.",
        ) from exc


@router.post("/login", response_model=UserOut)
def login(
    body: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> User:
    """Verify credentials, create session, and set session cookie."""
    try:
        normalized_email = body.email.lower().strip()
        user = db.query(User).filter_by(email=normalized_email).first()

        if not user or not user.password_hash or not verify_password(body.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is disabled",
            )

        client_ip = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")
        token = create_session(db, user, ip_address=client_ip, user_agent=user_agent)
        _set_session_cookie(response, token)
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
        return user
    except HTTPException:
        raise
    except (OperationalError, SQLAlchemyError) as exc:
        _raise_auth_storage_unavailable(exc)
    except Exception as exc:
        logger.exception("Login failed: %s", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Sign-in failed. Please try again.",
        ) from exc


@router.post("/logout")
def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """Revoke current session and clear session cookie."""
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()

    if token:
        revoke_session(db, token)

    response.delete_cookie(key=SESSION_COOKIE_NAME, path="/")
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    return {"message": "Successfully logged out"}


@router.post("/logout-all")
def logout_all(
    response: Response,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """Revoke all active sessions for current user and clear cookie."""
    count = revoke_all_sessions(db, current_user.id)
    response.delete_cookie(key=SESSION_COOKIE_NAME, path="/")
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    return {"message": f"Successfully revoked {count} sessions"}


@router.post("/verify-email")
def verify_user_email(
    body: VerifyEmailRequest,
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """Verify email using verification token."""
    success = verify_email(db, body.token)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token",
        )
    return {"message": "Email verified successfully"}


@router.get("/verify-email")
def verify_email_link(
    token: str,
    db: Session = Depends(get_db),
) -> RedirectResponse:
    """Verify email via one-click link clicked from transactional email."""
    success = verify_email(db, token)
    if success:
        return RedirectResponse(
            url=f"{settings.app_base_url}/dashboard?email_verified=true",
            status_code=status.HTTP_302_FOUND,
        )
    return RedirectResponse(
        url=f"{settings.app_base_url}/dashboard?error=invalid_verification_token",
        status_code=status.HTTP_302_FOUND,
    )


@router.post("/send-verification")
def resend_verification_email(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """Resend email verification link to current authenticated user."""
    if current_user.is_verified:
        return {"message": "Email address is already verified."}
    v_token = create_verification_token(db, current_user.id, hours=48)
    try:
        email_service.send_email_verification_email(
            to=current_user.email,
            verification_token=v_token,
            user_id=current_user.id,
            db=db,
        )
    except Exception as exc:
        logger.warning("Failed to dispatch verification email: %s", exc)
    return {"message": "Verification instructions have been sent to your email."}


@router.post("/forgot-password")
def forgot_password(
    body: PasswordResetRequest,
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """Create password reset token and dispatch instructions via Resend.

    Always returns generic success message to prevent user enumeration.
    """
    normalized_email = body.email.lower().strip()
    user = db.query(User).filter_by(email=normalized_email).first()
    if user and user.is_active:
        try:
            raw_token = create_password_reset_token(db, user.id, hours=0.5)
            email_service.send_password_reset_email(
                to=user.email,
                reset_token=raw_token,
                expires_in_minutes=30,
                user_id=user.id,
                db=db,
            )
        except Exception as exc:
            logger.warning("Failed to send password reset email: %s", exc)

    return {"message": "If an account exists for that address, password reset instructions have been sent."}


@router.post("/reset-password")
def reset_user_password(
    body: PasswordResetConfirm,
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """Reset password using single-use reset token and invalidate all user sessions."""
    token_hash = hashlib.sha256(body.token.encode()).hexdigest()
    token_rec = db.query(PasswordResetToken).filter_by(token_hash=token_hash, used=False).first()
    if not token_rec or _is_expired(token_rec.expires_at):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )
    user = db.get(User, token_rec.user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    success = reset_password(db, body.token, body.new_password)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    try:
        email_service.send_password_changed_email(
            to=user.email,
            user_id=user.id,
            db=db,
        )
    except Exception as exc:
        logger.warning("Failed to send password changed notification: %s", exc)

    return {"message": "Password has been successfully updated. Please sign in with your new credentials."}


@router.get("/me", response_model=UserOut)
def me(response: Response, current_user: User = Depends(get_current_user)) -> User:
    """Get the currently authenticated user."""
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    return current_user


# ── Google OAuth 2.0 Authentication ─────────────────────────────────

@router.get("/google")
def google_login(request: Request) -> RedirectResponse:
    """Initiate Google OAuth 2.0 authorization code flow."""
    if not settings.google_client_id or not settings.google_client_secret:
        logger.info("Google OAuth accessed before credentials were set in environment")
        return RedirectResponse(
            url=f"{settings.app_base_url}/login?error=google_oauth_config_required",
            status_code=status.HTTP_302_FOUND,
        )

    redirect_uri = settings.google_redirect_uri or f"{settings.app_base_url}/api/v1/auth/google/callback"
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "online",
        "prompt": "select_account",
    }
    google_auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(params)}"
    return RedirectResponse(url=google_auth_url, status_code=status.HTTP_302_FOUND)


@router.get("/google/callback")
async def google_callback(
    request: Request,
    code: str | None = None,
    error: str | None = None,
    db: Session = Depends(get_db),
) -> RedirectResponse:
    """Handle Google OAuth 2.0 callback, exchange code, and establish session."""
    if error or not code:
        return RedirectResponse(
            url=f"{settings.app_base_url}/login?error=google_auth_cancelled",
            status_code=status.HTTP_302_FOUND,
        )

    redirect_uri = settings.google_redirect_uri or f"{settings.app_base_url}/api/v1/auth/google/callback"

    # 1. Exchange authorization code for tokens
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            token_res = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "code": code,
                    "client_id": settings.google_client_id,
                    "client_secret": settings.google_client_secret,
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code",
                },
            )
            if token_res.status_code != 200:
                logger.warning("Google token exchange failed: %s", token_res.text)
                return RedirectResponse(
                    url=f"{settings.app_base_url}/login?error=google_token_exchange_failed",
                    status_code=status.HTTP_302_FOUND,
                )
            tokens = token_res.json()
            access_token = tokens.get("access_token")
            if not access_token:
                return RedirectResponse(
                    url=f"{settings.app_base_url}/login?error=google_token_missing",
                    status_code=status.HTTP_302_FOUND,
                )

            # 2. Fetch user profile from Google API
            userinfo_res = await client.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if userinfo_res.status_code != 200:
                return RedirectResponse(
                    url=f"{settings.app_base_url}/login?error=google_userinfo_failed",
                    status_code=status.HTTP_302_FOUND,
                )
            userinfo = userinfo_res.json()
    except Exception as exc:
        logger.error("Error during Google OAuth exchange: %s", exc)
        return RedirectResponse(
            url=f"{settings.app_base_url}/login?error=google_network_error",
            status_code=status.HTTP_302_FOUND,
        )

    google_email = (userinfo.get("email") or "").lower().strip()
    google_id = userinfo.get("id")
    google_name = userinfo.get("name")
    google_picture = userinfo.get("picture")

    if not google_email:
        return RedirectResponse(
            url=f"{settings.app_base_url}/login?error=google_email_missing",
            status_code=status.HTTP_302_FOUND,
        )

    # 3. Locate or create user
    user = db.query(User).filter_by(email=google_email).first()

    # Sole Administrator Policy: only shivam8668bakal@gmail.com is granted OWNER / admin access
    is_sole_admin = (google_email == "shivam8668bakal@gmail.com")
    assigned_role = "OWNER" if is_sole_admin else "RESEARCHER"

    if not user:
        user = User(
            email=google_email,
            password_hash="",  # Authenticated via Google OAuth
            role=assigned_role,
            is_active=True,
            is_verified=True,
            is_admin=is_sole_admin,
        )
        db.add(user)
        db.flush()

        profile = UserProfile(
            user_id=user.id,
            display_name=google_name or google_email.split("@")[0],
            avatar_url=google_picture,
        )
        settings_rec = UserSettings(user_id=user.id)
        db.add(profile)
        db.add(settings_rec)
    else:
        user.is_active = True
        user.is_verified = True
        if is_sole_admin:
            user.role = "OWNER"
            user.is_admin = True
        if user.profile and google_picture and not user.profile.avatar_url:
            user.profile.avatar_url = google_picture
        if user.profile and google_name and not user.profile.display_name:
            user.profile.display_name = google_name

    # Link OAuth account record if ID is provided
    if google_id:
        oauth_link = db.query(OAuthAccount).filter_by(
            provider="google",
            provider_account_id=str(google_id),
        ).first()
        if not oauth_link:
            db.add(
                OAuthAccount(
                    user_id=user.id,
                    provider="google",
                    provider_account_id=str(google_id),
                )
            )

    db.commit()
    db.refresh(user)

    # 4. Establish user session
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    token = create_session(db, user, ip_address=client_ip, user_agent=user_agent)

    # 5. Redirect destination based on role
    dest = "/admin" if (user.role in ("OWNER", "ADMIN") or user.is_admin) else "/dashboard"
    redirect_target = f"{settings.app_base_url}{dest}"

    redirect_response = RedirectResponse(url=redirect_target, status_code=status.HTTP_302_FOUND)
    _set_session_cookie(redirect_response, token)
    redirect_response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    return redirect_response

