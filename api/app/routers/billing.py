"""Billing and Monetization API Router."""
from __future__ import annotations

import json
from typing import Any
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..db import get_db
from ..models.user import User
from ..routers.deps import get_current_user
from ..services.billing_service import BillingService

router = APIRouter(
    prefix="/api/v1/billing",
    tags=["Monetization & Billing"],
)


class CreateOrderRequest(BaseModel):
    plan_tier: str
    interval: str = "monthly"


class VerifyPaymentRequest(BaseModel):
    order_id: str
    payment_id: str
    signature: str


@router.get("/plans")
def get_plans(db: Session = Depends(get_db)) -> dict[str, Any]:
    """Returns official subscription plans, prices, and gateway availability."""
    service = BillingService(db)
    return service.get_plans()


@router.get("/subscription")
def get_current_subscription(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Retrieves current authenticated researcher subscription and entitlement."""
    service = BillingService(db)
    return service.get_user_subscription(current_user.id)


@router.get("/history")
def get_billing_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    """Retrieves user's payment transaction history."""
    service = BillingService(db)
    return service.get_payment_history(current_user.id)


@router.post("/cancel")
def cancel_subscription(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Cancels auto-renewal at period end."""
    service = BillingService(db)
    try:
        return service.cancel_subscription(current_user.id)
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err))


@router.post("/create-order")
def create_subscription_order(
    payload: CreateOrderRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Initializes server-side Razorpay order.

    Fails cleanly if payment gateway is unconfigured (Zero fake simulation).
    """
    service = BillingService(db)
    if not service.is_configured:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="PAYMENTS NOT CONFIGURED: Razorpay gateway credentials are not configured on this instance.",
        )

    try:
        order = service.create_order(
            user_id=current_user.id,
            plan_tier=payload.plan_tier,
            interval=payload.interval,
        )
        return order
    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/verify-payment")
def verify_payment_checkout(
    payload: VerifyPaymentRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Verifies Razorpay checkout completion callback and activates subscription."""
    service = BillingService(db)
    if not service.is_configured:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="PAYMENTS NOT CONFIGURED: Razorpay gateway credentials are not configured on this instance.",
        )

    try:
        result = service.verify_payment(
            user_id=current_user.id,
            order_id=payload.order_id,
            payment_id=payload.payment_id,
            signature=payload.signature,
        )
        return result
    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/webhook")
async def razorpay_webhook(
    request: Request,
    x_razorpay_signature: str | None = Header(None),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Processes verified Razorpay webhook notifications."""
    body_bytes = await request.body()
    service = BillingService(db)

    if not service.verify_webhook(body_bytes, x_razorpay_signature):
        raise HTTPException(status_code=400, detail="Invalid webhook signature.")

    try:
        event_data = json.loads(body_bytes.decode("utf-8"))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload.")

    result = service.process_webhook_event(event_data)
    return result
