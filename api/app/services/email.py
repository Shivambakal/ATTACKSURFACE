"""Centralized Resend Email Service for AttackSurface Timeline.

Handles transactional security emails, password resets, account verifications,
security alerts, subscription updates, and export notifications.

NEVER logs or exposes RESEND_API_KEY, authentication tokens, passwords, or raw PII.
"""
from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from typing import Any

import httpx
from sqlalchemy.orm import Session as DBSession

from ..config import settings
from ..models.email_event import EmailEvent

logger = logging.getLogger("attacksurface.email")


def _mask_email(email: str) -> str:
    """Mask email for privacy-safe logging (e.g. j***@example.com)."""
    if not email or "@" not in email:
        return "invalid-email"
    parts = email.split("@")
    name = parts[0]
    domain = parts[1] if len(parts) > 1 else "unknown"
    if len(name) <= 2:
        masked_name = name[0] + "*"
    else:
        masked_name = name[0] + "*" * (len(name) - 2) + name[-1]
    return f"{masked_name}@{domain}"


def _hash_recipient(email: str) -> str:
    """SHA-256 hash of normalized email for zero-PII audit trail."""
    return hashlib.sha256(email.lower().strip().encode("utf-8")).hexdigest()


class EmailService:
    """Centralized transactional email service powered by Resend."""

    def __init__(self) -> None:
        self.api_key = settings.resend_api_key
        self.from_email = settings.resend_from_email or "AttackSurface <noreply@attacksurface.online>"
        self.reply_to = settings.resend_reply_to or "attacksurface.alerts@gmail.com"
        self.app_base_url = settings.app_base_url.rstrip("/")

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)

    def send_email(
        self,
        to: str,
        subject: str,
        html_body: str,
        text_body: str,
        event_type: str = "transactional",
        user_id: int | None = None,
        db: DBSession | None = None,
        reply_to: str | None = None,
    ) -> dict[str, Any]:
        """Send a transactional email via Resend API and log audit event."""
        recipient = to.strip().lower()
        masked = _mask_email(recipient)
        rec_hash = _hash_recipient(recipient)

        if not self.is_configured:
            logger.warning(
                "Resend not configured (RESEND_API_KEY missing). Simulated email '%s' to %s",
                event_type,
                masked,
            )
            self._record_audit(
                db=db,
                user_id=user_id,
                event_type=event_type,
                rec_hash=rec_hash,
                masked=masked,
                status="simulated",
                provider_id="simulated-no-key",
                failure_reason=None,
            )
            return {"id": "simulated", "status": "simulated"}

        payload = {
            "from": self.from_email,
            "to": [recipient],
            "subject": subject,
            "html": html_body,
            "text": text_body,
            "reply_to": reply_to or self.reply_to,
        }

        provider_id: str | None = None
        error_message: str | None = None
        send_status = "failed"

        try:
            with httpx.Client(timeout=12.0) as client:
                res = client.post(
                    "https://api.resend.com/emails",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )

                # Fallback: if domain not yet verified in Resend dashboard, retry with onboarding@resend.dev
                if res.status_code in (403, 422) and ("domain is not verified" in res.text.lower() or "testing" in res.text.lower()):
                    logger.info("Retrying email delivery with verified fallback sender onboarding@resend.dev")
                    payload["from"] = "AttackSurface <onboarding@resend.dev>"
                    res = client.post(
                        "https://api.resend.com/emails",
                        headers={
                            "Authorization": f"Bearer {self.api_key}",
                            "Content-Type": "application/json",
                        },
                        json=payload,
                    )

                if res.status_code in (200, 201):
                    data = res.json()
                    provider_id = data.get("id")
                    send_status = "sent"
                    logger.info(
                        "Resend email dispatched successfully: type=%s to=%s provider_id=%s",
                        event_type,
                        masked,
                        provider_id,
                    )
                else:
                    error_message = f"HTTP {res.status_code}: {res.text[:200]}"
                    logger.warning("Resend email delivery rejected for %s (%s): %s", masked, event_type, error_message)

        except Exception as exc:
            error_message = f"Transport error: {str(exc)[:200]}"
            logger.error("Resend email network error for %s (%s): %s", masked, event_type, exc)

        self._record_audit(
            db=db,
            user_id=user_id,
            event_type=event_type,
            rec_hash=rec_hash,
            masked=masked,
            status=send_status,
            provider_id=provider_id,
            failure_reason=error_message,
        )

        return {
            "id": provider_id,
            "status": send_status,
            "error": error_message,
        }

    def _record_audit(
        self,
        db: DBSession | None,
        user_id: int | None,
        event_type: str,
        rec_hash: str,
        masked: str,
        status: str,
        provider_id: str | None,
        failure_reason: str | None,
    ) -> None:
        if not db:
            return
        try:
            event = EmailEvent(
                user_id=user_id,
                type=event_type,
                recipient_hash=rec_hash,
                recipient_masked=masked,
                provider="resend",
                provider_message_id=provider_id,
                status=status,
                failure_reason_safe=failure_reason[:255] if failure_reason else None,
                sent_at=datetime.now(timezone.utc) if status == "sent" else None,
                failed_at=datetime.now(timezone.utc) if status == "failed" else None,
            )
            db.add(event)
            db.commit()
        except Exception as exc:
            logger.warning("Failed to record email audit record: %s", exc)
            try:
                db.rollback()
            except Exception:
                pass

    # ── Template Builders ──────────────────────────────────────────

    def _build_html_wrapper(self, title: str, content_html: str) -> str:
        """Standard AttackSurface cybersecurity intelligence email template."""
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
</head>
<body style="margin: 0; padding: 0; background-color: #030712; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #e2e8f0; line-height: 1.6;">
  <table width="100%" border="0" cellspacing="0" cellpadding="0" style="background-color: #030712; padding: 32px 16px;">
    <tr>
      <td align="center">
        <table width="100%" max-width="580" border="0" cellspacing="0" cellpadding="0" style="max-width: 580px; background-color: #0b0f19; border: 1px solid #1e293b; border-radius: 16px; overflow: hidden; box-shadow: 0 20px 40px rgba(0,0,0,0.6);">
          <!-- Header -->
          <tr>
            <td style="padding: 28px 32px 20px; border-bottom: 1px solid #1e293b; background: linear-gradient(180deg, rgba(6,182,212,0.06) 0%, transparent 100%);">
              <table width="100%" border="0" cellspacing="0" cellpadding="0">
                <tr>
                  <td>
                    <div style="font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; font-size: 11px; font-weight: 700; color: #00f0ff; letter-spacing: 0.12em; text-transform: uppercase;">
                      ATTACKSURFACE // TIMELINE OS
                    </div>
                    <div style="font-size: 18px; font-weight: 800; color: #ffffff; letter-spacing: -0.02em; margin-top: 4px;">
                      {title}
                    </div>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- Main Content Body -->
          <tr>
            <td style="padding: 32px; font-size: 14px; color: #cbd5e1;">
              {content_html}
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="padding: 24px 32px; background-color: #050811; border-top: 1px solid #1e293b; font-size: 11px; font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; color: #64748b; line-height: 1.6;">
              <div style="color: #94a3b8; font-weight: 600; margin-bottom: 4px;">
                AttackSurface Timeline · Continuous Security-Change Intelligence
              </div>
              <div>
                Platform: <a href="https://attacksurface.online" style="color: #00f0ff; text-decoration: none;">attacksurface.online</a> ·
                Desk: <a href="mailto:attacksurface.alerts@gmail.com" style="color: #00f0ff; text-decoration: none;">attacksurface.alerts@gmail.com</a>
              </div>
              <div style="margin-top: 8px; color: #475569;">
                Evidence-first observation · Zero weaponization · Cryptographic trace active
              </div>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""

    # ── High-Level Transactional Methods ───────────────────────────

    def send_password_reset_email(
        self,
        to: str,
        reset_token: str,
        expires_in_minutes: int = 30,
        user_id: int | None = None,
        db: DBSession | None = None,
    ) -> dict[str, Any]:
        """Send password reset instructions with secure HTTPS link."""
        reset_url = f"{self.app_base_url}/reset-password?token={reset_token}"
        subject = "Reset your AttackSurface password"

        content = f"""
<p style="margin-top: 0;">Hello Researcher,</p>
<p>We received an authorized request to reset the password for your AttackSurface account.</p>
<div style="margin: 28px 0; text-align: center;">
  <a href="{reset_url}" style="background-color: #00f0ff; color: #030712; padding: 12px 28px; border-radius: 8px; font-weight: 700; font-size: 13px; text-decoration: none; display: inline-block; font-family: ui-monospace, monospace; letter-spacing: 0.05em;">
    RESET PASSWORD &rarr;
  </a>
</div>
<p style="font-size: 12px; color: #94a3b8;">
  This link will expire in <strong style="color: #f1f5f9;">{expires_in_minutes} minutes</strong> and can only be used once. If you did not initiate this request, you can safely disregard this email—your account credentials remain intact.
</p>
<div style="margin-top: 24px; padding: 12px 16px; background-color: #0f172a; border-radius: 8px; border-left: 3px solid #00f0ff; font-size: 11px; font-family: ui-monospace, monospace; color: #94a3b8; word-break: break-all;">
  Direct URL: {reset_url}
</div>
"""
        text = f"""AttackSurface Password Reset

We received a request to reset your password.
Open the link below to set a new password (valid for {expires_in_minutes} minutes):

{reset_url}

If you did not request this, please ignore this email.
"""
        return self.send_email(
            to=to,
            subject=subject,
            html_body=self._build_html_wrapper("Password Reset", content),
            text_body=text,
            event_type="password_reset",
            user_id=user_id,
            db=db,
        )

    def send_password_changed_email(
        self,
        to: str,
        timestamp_str: str | None = None,
        user_id: int | None = None,
        db: DBSession | None = None,
    ) -> dict[str, Any]:
        """Notify user that account password was updated and all prior sessions invalidated."""
        ts = timestamp_str or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        subject = "Your AttackSurface password was changed"

        content = f"""
<p style="margin-top: 0;">Hello Researcher,</p>
<p>The password associated with your AttackSurface account was successfully changed on <strong>{ts}</strong>.</p>
<p style="color: #94a3b8;">For your security, all previously active sessions and API access tokens were invalidated. Please sign in with your new password to resume operations.</p>
<div style="margin: 24px 0; padding: 16px; background-color: #1e1b4b; border: 1px solid #4338ca; border-radius: 8px; color: #c7d2fe; font-size: 12px;">
  <strong>Security Warning:</strong> If you did not make this change, your credentials may be compromised. Please contact our security desk immediately at <a href="mailto:attacksurface.alerts@gmail.com" style="color: #00f0ff;">attacksurface.alerts@gmail.com</a>.
</div>
"""
        text = f"""AttackSurface — Password Changed

Your account password was updated on {ts}. All active sessions have been invalidated.
If you did not perform this action, contact attacksurface.alerts@gmail.com immediately.
"""
        return self.send_email(
            to=to,
            subject=subject,
            html_body=self._build_html_wrapper("Security Notice", content),
            text_body=text,
            event_type="password_changed",
            user_id=user_id,
            db=db,
        )

    def send_email_verification_email(
        self,
        to: str,
        verification_token: str,
        expires_in_minutes: int = 1440,  # 24h
        user_id: int | None = None,
        db: DBSession | None = None,
    ) -> dict[str, Any]:
        """Send email verification link for newly enrolled researcher accounts."""
        verify_url = f"{self.app_base_url}/verify-email?token={verification_token}"
        subject = "Verify your AttackSurface account"

        content = f"""
<p style="margin-top: 0;">Welcome to AttackSurface,</p>
<p>Please confirm ownership of this email address to activate verified status and enable customized attack surface alerts.</p>
<div style="margin: 28px 0; text-align: center;">
  <a href="{verify_url}" style="background-color: #00f0ff; color: #030712; padding: 12px 28px; border-radius: 8px; font-weight: 700; font-size: 13px; text-decoration: none; display: inline-block; font-family: ui-monospace, monospace; letter-spacing: 0.05em;">
    VERIFY ACCOUNT &rarr;
  </a>
</div>
<p style="font-size: 12px; color: #94a3b8;">
  This link will expire in {expires_in_minutes // 60} hours. If you did not create this account, you can disregard this message.
</p>
"""
        text = f"""Verify your AttackSurface Account

Open the verification link to activate your account:
{verify_url}
"""
        return self.send_email(
            to=to,
            subject=subject,
            html_body=self._build_html_wrapper("Account Verification", content),
            text_body=text,
            event_type="email_verification",
            user_id=user_id,
            db=db,
        )

    def send_welcome_email(
        self,
        to: str,
        name: str = "Researcher",
        user_id: int | None = None,
        db: DBSession | None = None,
    ) -> dict[str, Any]:
        """Send welcome onboarding email to new researcher."""
        subject = "Welcome to AttackSurface Timeline"
        workspace_url = f"{self.app_base_url}/dashboard"

        content = f"""
<p style="margin-top: 0;">Welcome, {name},</p>
<p>Your AttackSurface workspace is active. You now have access to continuous attack surface intelligence, CISA KEV real-time advisories, and forensic differential diffing across public bug bounty programs.</p>

<div style="margin: 24px 0; padding: 16px; background-color: #0f172a; border-radius: 8px; border: 1px solid #1e293b;">
  <div style="font-weight: 700; color: #ffffff; margin-bottom: 8px; font-size: 13px;">First Steps in Your Workspace:</div>
  <ul style="margin: 0; padding-left: 20px; color: #94a3b8; font-size: 12px;">
    <li style="margin-bottom: 6px;">Enroll an authorized target scope with verified program policy.</li>
    <li style="margin-bottom: 6px;">Explore the canonical company directory and bug bounty perimeters.</li>
    <li style="margin-bottom: 6px;">Configure your Personalization visual atmosphere and acoustic alert thresholds.</li>
  </ul>
</div>

<div style="margin: 28px 0; text-align: center;">
  <a href="{workspace_url}" style="background-color: #00f0ff; color: #030712; padding: 12px 28px; border-radius: 8px; font-weight: 700; font-size: 13px; text-decoration: none; display: inline-block; font-family: ui-monospace, monospace;">
    OPEN RESEARCH DECK &rarr;
  </a>
</div>

<p style="font-size: 11px; color: #64748b;">
  Reminder: AttackSurface strictly adheres to evidence-first observation and authorized public policy. Intrusive weaponization or uncoordinated probing is strictly prohibited.
</p>
"""
        text = f"""Welcome to AttackSurface Timeline

Your workspace is ready. Access live attack surface intelligence at:
{workspace_url}
"""
        return self.send_email(
            to=to,
            subject=subject,
            html_body=self._build_html_wrapper("Workspace Activated", content),
            text_body=text,
            event_type="welcome",
            user_id=user_id,
            db=db,
        )

    def send_security_alert_email(
        self,
        to: str,
        title: str,
        severity: str,
        summary: str,
        details_url: str | None = None,
        user_id: int | None = None,
        db: DBSession | None = None,
    ) -> dict[str, Any]:
        """Dispatch high-severity security alert notification matching user preferences."""
        sev_color = "#f43f5e" if severity.upper() == "CRITICAL" else "#f59e0b" if severity.upper() == "HIGH" else "#00f0ff"
        subject = f"[{severity.upper()}] Security Alert: {title}"
        target_link = details_url or f"{self.app_base_url}/alerts"

        content = f"""
<div style="margin-bottom: 16px;">
  <span style="background-color: {sev_color}20; color: {sev_color}; border: 1px solid {sev_color}40; padding: 4px 10px; border-radius: 6px; font-family: ui-monospace, monospace; font-size: 11px; font-weight: 700;">
    {severity.upper()} SIGNAL
  </span>
</div>
<h3 style="color: #ffffff; margin-top: 8px; font-size: 16px;">{title}</h3>
<p style="color: #cbd5e1; font-size: 13px; line-height: 1.6;">{summary}</p>
<div style="margin: 24px 0;">
  <a href="{target_link}" style="background-color: #1e293b; color: #ffffff; border: 1px solid #334155; padding: 10px 20px; border-radius: 8px; font-size: 12px; text-decoration: none; display: inline-block; font-weight: 600;">
    Inspect Signal Forensic Detail &rarr;
  </a>
</div>
"""
        text = f"""[{severity.upper()}] Security Alert: {title}

{summary}

Inspect forensic detail: {target_link}
"""
        return self.send_email(
            to=to,
            subject=subject,
            html_body=self._build_html_wrapper("Security Alert", content),
            text_body=text,
            event_type="security_alert",
            user_id=user_id,
            db=db,
        )

    def send_subscription_email(
        self,
        to: str,
        plan_name: str,
        amount: str,
        event_type: str = "activated",  # activated, renewed, payment_failed
        user_id: int | None = None,
        db: DBSession | None = None,
    ) -> dict[str, Any]:
        """Dispatch subscription payment confirmation or status update."""
        subject = f"AttackSurface Subscription {event_type.capitalize()}: {plan_name}"
        manage_url = f"{self.app_base_url}/billing"

        content = f"""
<p style="margin-top: 0;">Hello Researcher,</p>
<p>Your AttackSurface subscription for the <strong>{plan_name}</strong> tier has been confirmed.</p>
<table width="100%" border="0" cellspacing="0" cellpadding="8" style="background-color: #0f172a; border-radius: 8px; margin: 20px 0; font-family: ui-monospace, monospace; font-size: 12px;">
  <tr>
    <td style="color: #64748b;">Tier:</td>
    <td style="color: #ffffff; font-weight: 700;">{plan_name}</td>
  </tr>
  <tr>
    <td style="color: #64748b;">Amount:</td>
    <td style="color: #00f0ff; font-weight: 700;">{amount}</td>
  </tr>
  <tr>
    <td style="color: #64748b;">Status:</td>
    <td style="color: #34d399; font-weight: 700;">VERIFIED ACTIVE</td>
  </tr>
</table>
<div style="margin: 24px 0; text-align: center;">
  <a href="{manage_url}" style="background-color: #00f0ff; color: #030712; padding: 10px 24px; border-radius: 8px; font-weight: 700; font-size: 12px; text-decoration: none; display: inline-block;">
    MANAGE SUBSCRIPTION &rarr;
  </a>
</div>
"""
        text = f"""AttackSurface Subscription {event_type.capitalize()}

Tier: {plan_name}
Amount: {amount}
Status: VERIFIED ACTIVE

Manage subscription: {manage_url}
"""
        return self.send_email(
            to=to,
            subject=subject,
            html_body=self._build_html_wrapper("Subscription Confirmation", content),
            text_body=text,
            event_type="subscription",
            user_id=user_id,
            db=db,
        )

    def send_export_ready_email(
        self,
        to: str,
        export_type: str,
        download_url: str,
        expires_at: str | None = None,
        user_id: int | None = None,
        db: DBSession | None = None,
    ) -> dict[str, Any]:
        """Notify user that a forensic export artifact is ready for download."""
        subject = f"Your AttackSurface {export_type.upper()} Export is Ready"
        exp_info = f"This secure link will expire on {expires_at}." if expires_at else "Available in your Researcher Export Center."

        content = f"""
<p style="margin-top: 0;">Hello Researcher,</p>
<p>Your requested <strong>{export_type.upper()}</strong> export has been generated and validated with cryptographic checksums.</p>
<div style="margin: 24px 0; text-align: center;">
  <a href="{download_url}" style="background-color: #00f0ff; color: #030712; padding: 12px 28px; border-radius: 8px; font-weight: 700; font-size: 13px; text-decoration: none; display: inline-block; font-family: ui-monospace, monospace;">
    DOWNLOAD EXPORT &rarr;
  </a>
</div>
<p style="font-size: 12px; color: #94a3b8;">{exp_info}</p>
"""
        text = f"""Your AttackSurface {export_type.upper()} Export is Ready

Download link:
{download_url}

{exp_info}
"""
        return self.send_email(
            to=to,
            subject=subject,
            html_body=self._build_html_wrapper("Export Ready", content),
            text_body=text,
            event_type="export_ready",
            user_id=user_id,
            db=db,
        )


# Singleton instance
email_service = EmailService()
