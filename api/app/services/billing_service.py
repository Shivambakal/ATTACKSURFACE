"""Monetization and Razorpay Billing Service.

Enforces server-side billing integrity:
- Server-side plan definitions and prices
- Razorpay order creation when credentials are valid
- HMAC-SHA256 signature verification on webhooks
- Replay and idempotency protection
- Explicit PAYMENTS NOT CONFIGURED status when unconfigured (ZERO fake checkout simulation)
"""
from __future__ import annotations

import hashlib
import hmac
import logging
from datetime import datetime, timezone, timedelta
from typing import Any
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..models.base import utcnow
from ..models.billing import (
    Subscription,
    SubscriptionTier,
    SubscriptionStatus,
    PaymentTransaction,
    PaymentStatus,
)

logger = logging.getLogger(__name__)

# Server-side authoritative plan definitions (in INR)
PLANS_CATALOG: dict[str, dict[str, Any]] = {
    SubscriptionTier.FREE.value: {
        "id": "free",
        "tier": SubscriptionTier.FREE.value,
        "name": "Community Researcher",
        "price_inr": 0,
        "monthly_price_inr": 0,
        "yearly_price_inr": 0,
        "savings_inr": 0,
        "currency": "INR",
        "billing_period": "forever",
        "active": True,
        "razorpay_plan_id": None,
        "features": [
            "Access to 50 Authorized Targets",
            "CISA KEV Public Intelligence",
            "Basic JSON & CSV Exports",
            "Community Support",
        ],
        "limits": {
            "max_targets": 50,
            "export_formats": ["JSON", "CSV"],
            "max_export_rows": 500,
            "research_limits": "Standard queue",
        },
    },
    SubscriptionTier.RESEARCHER.value: {
        "id": "researcher",
        "tier": SubscriptionTier.RESEARCHER.value,
        "name": "Researcher",
        "price_inr": 400,
        "monthly_price_inr": 400,
        "yearly_price_inr": 4000,
        "savings_inr": 800,
        "currency": "INR",
        "billing_period": "monthly",
        "active": True,
        "razorpay_plan_id": None,
        "features": [
            "Access to all 304 Canonical Companies",
            "Real-time CISA KEV Ingestion & Deltas",
            "Full Export Formats (JSON, CSV, NDJSON, ZIP)",
            "Priority Research Signals & Attack Surface Diffs",
            "Advanced Temporal Timeline Filters",
        ],
        "limits": {
            "max_targets": 500,
            "export_formats": ["JSON", "CSV", "NDJSON", "ZIP"],
            "max_export_rows": 25000,
            "research_limits": "Priority queue",
        },
    },
    SubscriptionTier.PRO.value: {
        "id": "pro",
        "tier": SubscriptionTier.PRO.value,
        "name": "Pro",
        "price_inr": 700,
        "monthly_price_inr": 700,
        "yearly_price_inr": 7000,
        "savings_inr": 1400,
        "currency": "INR",
        "billing_period": "monthly",
        "active": True,
        "razorpay_plan_id": None,
        "features": [
            "Complete Research & Intelligence Dataset",
            "Instant KEV Exploit Alerts",
            "Raw Source Snapshots with SHA-256 Hashes",
            "Unrestricted Export Rows & Evidence Packs",
            "Direct Vulnerability Cross-Verification",
        ],
        "limits": {
            "max_targets": 2000,
            "export_formats": ["JSON", "CSV", "NDJSON", "ZIP"],
            "max_export_rows": 100000,
            "research_limits": "Dedicated researcher concurrency",
        },
    },
    SubscriptionTier.ADVANCED.value: {
        "id": "advanced",
        "tier": SubscriptionTier.ADVANCED.value,
        "name": "Advanced",
        "price_inr": 900,
        "monthly_price_inr": 900,
        "yearly_price_inr": 9000,
        "savings_inr": 1800,
        "currency": "INR",
        "billing_period": "monthly",
        "active": True,
        "razorpay_plan_id": None,
        "features": [
            "All Pro Capabilities Included",
            "Multi-Source Consensus Matrix",
            "Custom Intelligence Feed Ingestion",
            "Automated Compliance & Scope Reporting",
            "Highest Priority Data Verification",
        ],
        "limits": {
            "max_targets": 10000,
            "export_formats": ["JSON", "CSV", "NDJSON", "ZIP"],
            "max_export_rows": 500000,
            "research_limits": "Unlimited research operations",
        },
    },
}


class BillingService:
    """Manages subscription lifecycles, Razorpay order dispatch, and webhook verification."""

    def __init__(self, db: Session):
        self.db = db

    @property
    def is_configured(self) -> bool:
        """Indicates whether real Razorpay credentials are present."""
        return settings.razorpay_configured

    def get_plans(self) -> dict[str, Any]:
        """Returns catalog of subscription plans and gateway status."""
        return {
            "configured": self.is_configured,
            "environment": settings.razorpay_environment,
            "status_label": settings.razorpay_status_label,
            "currency": "INR",
            "has_yearly_billing": True,
            "plans": list(PLANS_CATALOG.values()),
        }

    def get_user_subscription(self, user_id: int) -> dict[str, Any]:
        """Retrieves or provisions the default active subscription for a user."""
        sub = self.db.scalars(
            select(Subscription).where(Subscription.user_id == user_id)
        ).first()

        if not sub:
            # Provision free tier default
            sub = Subscription(
                user_id=user_id,
                tier=SubscriptionTier.FREE.value,
                status=SubscriptionStatus.ACTIVE.value,
                provider="INTERNAL",
                is_verified_payment=False,
            )
            self.db.add(sub)
            self.db.commit()
            self.db.refresh(sub)

        plan_info = PLANS_CATALOG.get(sub.tier, PLANS_CATALOG[SubscriptionTier.FREE.value])

        return {
            "id": sub.id,
            "tier": sub.tier,
            "status": sub.status,
            "provider": sub.provider,
            "is_verified_payment": getattr(sub, "is_verified_payment", False),
            "current_period_start": sub.current_period_start.isoformat() if sub.current_period_start else None,
            "current_period_end": sub.current_period_end.isoformat() if sub.current_period_end else None,
            "cancel_at_period_end": sub.cancel_at_period_end,
            "plan": plan_info,
        }

    def create_order(self, user_id: int, plan_tier: str, interval: str = "monthly") -> dict[str, Any]:
        """Creates a verified Razorpay order server-side.

        FAIL-SAFE: Fails cleanly with PAYMENTS NOT CONFIGURED if keys are absent.
        """
        if not self.is_configured:
            raise RuntimeError("PAYMENTS NOT CONFIGURED: Razorpay keys are not configured on this server.")

        # Alias TEAM to ADVANCED if passed
        normalized_tier = plan_tier.upper() if plan_tier else ""
        if normalized_tier == "TEAM":
            normalized_tier = SubscriptionTier.ADVANCED.value

        if normalized_tier not in PLANS_CATALOG:
            raise ValueError(f"Invalid plan tier '{plan_tier}'. Configured plans: {list(PLANS_CATALOG.keys())}")

        # Strict interval validation: MUST be 'monthly' or 'yearly'
        if not isinstance(interval, str) or interval.lower() not in ("monthly", "yearly"):
            raise ValueError("Invalid billing interval: must be 'monthly' or 'yearly'.")
        interval_clean = interval.lower().strip()

        plan = PLANS_CATALOG[normalized_tier]

        # Explicit yearly price validation — do not invent or calculate automatically
        if interval_clean == "yearly":
            yearly_price = plan.get("yearly_price_inr")
            if not yearly_price or yearly_price <= 0:
                raise ValueError(f"Yearly billing is not configured for plan '{plan_tier}'.")
            price_inr = yearly_price
        else:
            price_inr = plan["monthly_price_inr"]

        amount_paisa = price_inr * 100
        receipt = f"rcpt_{user_id}_{int(utcnow().timestamp())}"

        try:
            import razorpay  # type: ignore
            client = razorpay.Client(auth=(settings.razorpay_key_id, settings.razorpay_key_secret))
            order_data = {
                "amount": amount_paisa,
                "currency": "INR",
                "receipt": receipt,
                "notes": {
                    "user_id": str(user_id),
                    "plan_tier": normalized_tier,
                    "interval": interval_clean,
                },
            }
            rzp_order = client.order.create(data=order_data)
            order_id = rzp_order["id"]
        except Exception as exc:
            logger.error("Failed to create Razorpay order: %s", exc)
            raise RuntimeError(f"Payment gateway error: {exc}") from exc

        # Environment determination
        env_label = "TEST" if (settings.razorpay_key_id or "").startswith("rzp_test_") else "LIVE"

        # Log transaction with strict state tracking and expected paisa
        tx = PaymentTransaction(
            user_id=user_id,
            order_id=order_id,
            plan_tier=normalized_tier,
            billing_interval=interval_clean,
            amount_inr=price_inr,
            expected_amount_paisa=amount_paisa,
            currency="INR",
            status=PaymentStatus.CREATED.value,
            payment_state=PaymentStatus.CREATED.value,
            environment=env_label,
            gateway_verified=False,
            receipt=receipt,
            created_at=utcnow(),
        )
        self.db.add(tx)
        self.db.commit()

        return {
            "order_id": order_id,
            "amount": amount_paisa,
            "currency": "INR",
            "key_id": settings.razorpay_key_id,
            "plan_tier": normalized_tier,
            "plan_name": plan["name"],
            "interval": interval_clean,
            "price_inr": price_inr,
            "environment": env_label,
        }

    def verify_webhook(self, body_bytes: bytes, signature: str | None) -> bool:
        """Verifies webhook signature using HMAC-SHA256."""
        secret = settings.razorpay_webhook_secret
        if not secret or not signature:
            return False
        expected = hmac.new(secret.encode("utf-8"), body_bytes, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)

    def process_webhook_event(self, event_data: dict[str, Any]) -> dict[str, Any]:
        """Processes verified webhook events with replay protection and strict idempotency."""
        event_name = event_data.get("event")
        payload = event_data.get("payload", {})
        payment_entity = payload.get("payment", {}).get("entity", {})
        order_id = payment_entity.get("order_id")
        payment_id = payment_entity.get("id")

        if not order_id:
            return {"status": "ignored", "reason": "no_order_id"}

        # Lookup transaction
        tx = self.db.scalars(
            select(PaymentTransaction).where(PaymentTransaction.order_id == order_id)
        ).first()

        if not tx:
            return {"status": "ignored", "reason": "unknown_order"}

        # Idempotency check: Repeated webhook event must produce exactly one entitlement
        if tx.payment_state == PaymentStatus.CAPTURED.value and tx.gateway_verified:
            return {"status": "ALREADY_PROCESSED", "reason": "payment_already_captured_and_entitled"}

        # Validate amount & currency match stored transaction
        pay_amount = payment_entity.get("amount")
        if pay_amount is not None and pay_amount != tx.expected_amount_paisa:
            tx.failure_reason = f"Webhook amount mismatch: got {pay_amount}, expected {tx.expected_amount_paisa}"
            self.db.commit()
            return {"status": "rejected", "reason": "amount_mismatch"}

        pay_curr = payment_entity.get("currency")
        if pay_curr and pay_curr.upper() != tx.currency.upper():
            tx.failure_reason = f"Webhook currency mismatch: got {pay_curr}, expected {tx.currency}"
            self.db.commit()
            return {"status": "rejected", "reason": "currency_mismatch"}

        if event_name == "payment.captured":
            raw_status = (payment_entity.get("status") or "captured").upper()
            tx.status = PaymentStatus.CAPTURED.value
            tx.payment_state = PaymentStatus.CAPTURED.value
            tx.gateway_status = raw_status
            tx.payment_id = payment_id
            tx.gateway_verified = True
            now = utcnow()
            tx.completed_at = now

            # Entitlement source is STRICTLY the stored transaction record
            target_tier = tx.plan_tier
            target_interval = tx.billing_interval
            period_days = 365 if target_interval == "yearly" else 30

            sub = self.db.scalars(
                select(Subscription).where(Subscription.user_id == tx.user_id)
            ).first()

            if sub:
                sub.tier = target_tier
                sub.status = SubscriptionStatus.ACTIVE.value
                sub.provider = "RAZORPAY"
                sub.is_verified_payment = True
                sub.provider_subscription_id = payment_id
                sub.current_period_start = now
                sub.current_period_end = now + timedelta(days=period_days)
                sub.cancel_at_period_end = False
            else:
                sub = Subscription(
                    user_id=tx.user_id,
                    tier=target_tier,
                    status=SubscriptionStatus.ACTIVE.value,
                    provider="RAZORPAY",
                    is_verified_payment=True,
                    provider_subscription_id=payment_id,
                    current_period_start=now,
                    current_period_end=now + timedelta(days=period_days),
                    cancel_at_period_end=False,
                )
                self.db.add(sub)

            self.db.commit()

            # Dispatch subscription confirmation email via Resend
            try:
                from app.models.user import User
                from app.services.email import email_service
                user_rec = self.db.get(User, tx.user_id)
                if user_rec and user_rec.email:
                    email_service.send_subscription_email(
                        to=user_rec.email,
                        plan_name=target_tier,
                        status="ACTIVE",
                        amount_inr=tx.expected_amount_paisa // 100 if tx.expected_amount_paisa else 0,
                        interval=target_interval,
                        next_billing_date=sub.current_period_end.strftime("%Y-%m-%d") if sub.current_period_end else None,
                        user_id=tx.user_id,
                        db=self.db,
                    )
            except Exception as exc:
                logger.warning("Failed to dispatch subscription confirmation email on webhook: %s", exc)

            return {
                "status": "success",
                "tier": target_tier,
                "interval": target_interval,
                "user_id": tx.user_id,
                "payment_state": PaymentStatus.CAPTURED.value,
            }

        elif event_name == "payment.authorized":
            # Authorized only — do NOT grant entitlement
            tx.status = PaymentStatus.AUTHORIZED.value
            tx.payment_state = PaymentStatus.AUTHORIZED.value
            tx.gateway_status = "AUTHORIZED"
            tx.payment_id = payment_id
            self.db.commit()
            return {"status": "authorized", "user_id": tx.user_id, "payment_state": PaymentStatus.AUTHORIZED.value}

        elif event_name == "payment.failed":
            tx.status = PaymentStatus.FAILED.value
            tx.payment_state = PaymentStatus.FAILED.value
            tx.gateway_status = "FAILED"
            tx.failure_reason = "payment.failed webhook event"
            self.db.commit()
            return {"status": "failed", "user_id": tx.user_id, "payment_state": PaymentStatus.FAILED.value}

        return {"status": "ignored", "event": event_name}

    @staticmethod
    def verify_signature_only(order_id: str, payment_id: str, signature: str, secret: str) -> bool:
        """UNIT TEST ONLY: Pure cryptographic signature verification.
        
        NEVER grants subscription entitlement or updates database records.
        """
        if not secret or not signature or not order_id or not payment_id:
            return False
        msg = f"{order_id}|{payment_id}".encode("utf-8")
        expected = hmac.new(secret.encode("utf-8"), msg, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)

    def verify_payment(
        self, user_id: int, order_id: str, payment_id: str, signature: str
    ) -> dict[str, Any]:
        """Verifies direct payment completion against official Razorpay API and activates subscription.

        DATA-TRUTH REQUIREMENT:
        - Validates order ownership.
        - NEVER infers plan_tier or interval from payment amount or frontend.
        - Entitlement source is strictly stored transaction.plan_tier and transaction.billing_interval.
        - Only CAPTURED payments grant entitlement.
        """
        if not self.is_configured:
            raise RuntimeError("PAYMENTS NOT CONFIGURED: Razorpay keys are not configured.")

        secret = settings.razorpay_key_secret
        if not secret:
            raise RuntimeError("Razorpay key secret is not configured.")

        # 1. Fetch PaymentTransaction by order_id
        tx = self.db.scalars(
            select(PaymentTransaction).where(PaymentTransaction.order_id == order_id)
        ).first()

        if not tx:
            raise ValueError(f"Transaction not found for order '{order_id}'.")

        # Cross-user order ownership check
        if tx.user_id != user_id:
            raise PermissionError("Cross-user order access denied: authenticated user does not own this order.")

        # Idempotency check: Reject/Report if transaction already completed
        if tx.payment_state == PaymentStatus.CAPTURED.value and tx.gateway_verified:
            return {
                "status": "ALREADY_PROCESSED",
                "message": "Payment has already been confirmed and processed.",
                "order_id": order_id,
                "payment_id": tx.payment_id or payment_id,
                "payment_state": tx.payment_state,
                "tier": tx.plan_tier,
                "interval": tx.billing_interval,
            }

        # 2. Cryptographic HMAC signature validation
        if not self.verify_signature_only(order_id, payment_id, signature, secret):
            logger.warning("Razorpay payment signature mismatch for order %s", order_id)
            tx.failure_reason = "Cryptographic signature mismatch"
            self.db.commit()
            raise ValueError("Invalid payment signature.")

        # 3. REAL GATEWAY VERIFICATION: Contact Razorpay API to confirm payment exists and is legitimate
        try:
            import razorpay
            client = razorpay.Client(auth=(settings.razorpay_key_id, settings.razorpay_key_secret))
            rzp_payment = client.payment.fetch(payment_id)
        except Exception as exc:
            logger.error("Razorpay API verification failed for payment %s: %s", payment_id, exc)
            tx.status = PaymentStatus.FAILED.value
            tx.payment_state = PaymentStatus.FAILED.value
            tx.failure_reason = f"Gateway fetch failure: {exc}"
            self.db.commit()
            raise ValueError(
                f"GATEWAY VERIFICATION REJECTED: Payment ID '{payment_id}' was not confirmed by Razorpay. "
                f"Fabricated payment IDs cannot grant subscription entitlement ({exc})."
            ) from exc

        # 4. Verify payment properties match server order
        rzp_payment_id = rzp_payment.get("id")
        if rzp_payment_id != payment_id:
            raise ValueError(f"PAYMENT ID MISMATCH: Gateway reports ID '{rzp_payment_id}', expected '{payment_id}'.")

        rzp_order_id = rzp_payment.get("order_id")
        if rzp_order_id != order_id:
            raise ValueError(f"ORDER MISMATCH: Razorpay reports order '{rzp_order_id}', expected '{order_id}'.")

        rzp_amount = rzp_payment.get("amount", 0)
        if rzp_amount != tx.expected_amount_paisa:
            raise ValueError(
                f"AMOUNT TAMPERING DETECTED: Gateway reports {rzp_amount} paisa, expected {tx.expected_amount_paisa} paisa."
            )

        rzp_currency = (rzp_payment.get("currency") or "").upper()
        if rzp_currency != tx.currency.upper():
            raise ValueError(f"CURRENCY MISMATCH: Gateway reports '{rzp_currency}', expected '{tx.currency}'.")

        raw_status = (rzp_payment.get("status") or "").upper()
        tx.gateway_status = raw_status

        # 5. Gateway Status Check: Only CAPTURED grants entitlement
        if raw_status == "AUTHORIZED":
            tx.status = PaymentStatus.AUTHORIZED.value
            tx.payment_state = PaymentStatus.AUTHORIZED.value
            tx.payment_id = payment_id
            tx.signature = signature
            self.db.commit()
            return {
                "status": "AUTHORIZED_PENDING_CAPTURE",
                "message": "Payment authorized but not yet captured by gateway. Entitlement is granted only upon capture.",
                "order_id": order_id,
                "payment_id": payment_id,
                "payment_state": PaymentStatus.AUTHORIZED.value,
            }

        if raw_status != "CAPTURED":
            tx.status = PaymentStatus.FAILED.value
            tx.payment_state = PaymentStatus.FAILED.value
            tx.failure_reason = f"Gateway status '{raw_status}' is not CAPTURED"
            self.db.commit()
            raise ValueError(f"PAYMENT NOT COMPLETED: Gateway status is '{raw_status}'. Only CAPTURED payments grant entitlement.")

        # 6. Gateway verification passed: Record true gateway state
        now = utcnow()
        tx.payment_id = payment_id
        tx.signature = signature
        tx.status = PaymentStatus.CAPTURED.value
        tx.payment_state = PaymentStatus.CAPTURED.value
        tx.gateway_verified = True
        tx.completed_at = now
        tx.failure_reason = None

        # Authoritative entitlement strictly from stored transaction
        target_tier = tx.plan_tier
        target_interval = tx.billing_interval
        period_days = 365 if target_interval == "yearly" else 30

        # Upgrade user subscription
        sub = self.db.scalars(
            select(Subscription).where(Subscription.user_id == user_id)
        ).first()

        if sub:
            sub.tier = target_tier
            sub.status = SubscriptionStatus.ACTIVE.value
            sub.provider = "RAZORPAY"
            sub.is_verified_payment = True
            sub.provider_subscription_id = payment_id
            sub.current_period_start = now
            sub.current_period_end = now + timedelta(days=period_days)
            sub.cancel_at_period_end = False
        else:
            sub = Subscription(
                user_id=user_id,
                tier=target_tier,
                status=SubscriptionStatus.ACTIVE.value,
                provider="RAZORPAY",
                is_verified_payment=True,
                provider_subscription_id=payment_id,
                current_period_start=now,
                current_period_end=now + timedelta(days=period_days),
                cancel_at_period_end=False,
            )
            self.db.add(sub)

        self.db.commit()

        # Dispatch subscription confirmation email via Resend
        try:
            from app.models.user import User
            from app.services.email import email_service
            user_rec = self.db.get(User, user_id)
            if user_rec and user_rec.email:
                email_service.send_subscription_email(
                    to=user_rec.email,
                    plan_name=target_tier,
                    status="ACTIVE",
                    amount_inr=tx.expected_amount_paisa // 100 if tx.expected_amount_paisa else 0,
                    interval=target_interval,
                    next_billing_date=sub.current_period_end.strftime("%Y-%m-%d") if sub.current_period_end else None,
                    user_id=user_id,
                    db=self.db,
                )
        except Exception as exc:
            logger.warning("Failed to dispatch subscription confirmation email on payment verify: %s", exc)

        return {
            "status": "success",
            "tier": target_tier,
            "interval": target_interval,
            "order_id": order_id,
            "payment_id": payment_id,
            "payment_state": PaymentStatus.CAPTURED.value,
            "environment": tx.environment,
            "gateway_verified": True,
            "current_period_end": sub.current_period_end.isoformat() if sub.current_period_end else None,
            "message": f"Successfully verified by Razorpay and upgraded to {target_tier.title()} ({target_interval.title()}) subscription!",
        }

    def get_payment_history(self, user_id: int) -> list[dict[str, Any]]:
        """Returns chronological list of user's payment transactions."""
        txs = self.db.scalars(
            select(PaymentTransaction)
            .where(PaymentTransaction.user_id == user_id)
            .order_by(PaymentTransaction.created_at.desc())
        ).all()
        return [
            {
                "id": t.id,
                "order_id": t.order_id,
                "payment_id": t.payment_id,
                "plan_tier": t.plan_tier,
                "billing_interval": t.billing_interval,
                "amount_inr": t.amount_inr,
                "expected_amount_paisa": t.expected_amount_paisa,
                "currency": t.currency,
                "status": t.status,
                "payment_state": t.payment_state,
                "gateway_status": t.gateway_status,
                "environment": t.environment,
                "receipt": t.receipt,
                "failure_reason": t.failure_reason,
                "created_at": t.created_at.isoformat() if t.created_at else None,
                "completed_at": t.completed_at.isoformat() if t.completed_at else None,
            }
            for t in txs
        ]

    def cancel_subscription(self, user_id: int) -> dict[str, Any]:
        """Cancels recurring subscription on gateway or marks fixed-term subscription as non-renewing."""
        sub = self.db.scalars(
            select(Subscription).where(Subscription.user_id == user_id)
        ).first()
        if not sub:
            raise ValueError("No active subscription found.")

        # Check if active recurring Razorpay subscription
        is_recurring = (
            sub.provider == "RAZORPAY_SUBSCRIPTION"
            and sub.provider_subscription_id
            and sub.provider_subscription_id.startswith("sub_")
        )

        if is_recurring:
            try:
                import razorpay
                client = razorpay.Client(auth=(settings.razorpay_key_id, settings.razorpay_key_secret))
                client.subscription.cancel(sub.provider_subscription_id, {"cancel_at_cycle_end": 1})
                sub.cancel_at_period_end = True
                self.db.commit()
                return {
                    "status": "success",
                    "gateway_cancellation": True,
                    "message": "Official gateway recurring subscription canceled at cycle end.",
                    "current_period_end": sub.current_period_end.isoformat() if sub.current_period_end else None,
                }
            except Exception as exc:
                logger.error("Failed to cancel Razorpay recurring subscription: %s", exc)
                raise RuntimeError(f"Gateway subscription cancellation failed: {exc}") from exc
        else:
            # One-time order payment or manual billing: fixed term, non-renewing
            sub.cancel_at_period_end = True
            self.db.commit()
            return {
                "status": "success",
                "gateway_cancellation": False,
                "message": "Fixed-term subscription marked as non-renewing (no active recurring mandate).",
                "current_period_end": sub.current_period_end.isoformat() if sub.current_period_end else None,
            }
