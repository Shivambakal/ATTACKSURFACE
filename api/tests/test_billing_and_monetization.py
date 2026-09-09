"""Unit, integration, and security tests for Monetization and Billing."""
from __future__ import annotations

import hashlib
import hmac
import pytest
from app.config import settings
from app.models.billing import PaymentStatus, PaymentTransaction, Subscription, SubscriptionTier
from app.models.user import User
from app.services.billing_service import BillingService, PLANS_CATALOG


def test_plans_catalog_integrity(db_session):
    """Verify server-side plans catalog contains expected tiers, prices, and limits."""
    service = BillingService(db_session)
    plans_data = service.get_plans()

    assert plans_data["configured"] is True
    assert plans_data["currency"] == "INR"
    assert plans_data["has_yearly_billing"] is True
    tiers = {p["tier"] for p in plans_data["plans"]}
    assert "FREE" in tiers
    assert "RESEARCHER" in tiers
    assert "PRO" in tiers
    assert "ADVANCED" in tiers

    # Check Researcher plan price (exact ₹400/mo, ₹4000/yr, ₹800 savings)
    researcher_plan = next(p for p in plans_data["plans"] if p["tier"] == "RESEARCHER")
    assert researcher_plan["price_inr"] == 400
    assert researcher_plan["monthly_price_inr"] == 400
    assert researcher_plan["yearly_price_inr"] == 4000
    assert researcher_plan["savings_inr"] == 800

    # Check Pro and Advanced plan prices
    pro_plan = next(p for p in plans_data["plans"] if p["tier"] == "PRO")
    assert pro_plan["price_inr"] == 700
    assert pro_plan["yearly_price_inr"] == 7000
    assert pro_plan["savings_inr"] == 1400

    advanced_plan = next(p for p in plans_data["plans"] if p["tier"] == "ADVANCED")
    assert advanced_plan["price_inr"] == 900
    assert advanced_plan["yearly_price_inr"] == 9000
    assert advanced_plan["savings_inr"] == 1800


def _get_test_user(db_session, email="test_billing_isolated@example.com") -> User:
    user = db_session.query(User).filter_by(email=email).first()
    if not user:
        user = User(email=email, role="RESEARCHER")
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
    return user


def test_billing_configured_and_order_creation(db_session):
    """Verify that when Razorpay test keys are present, real test order is created."""
    service = BillingService(db_session)
    assert service.is_configured is True

    user = _get_test_user(db_session, "test_order_creation@example.com")

    # Monthly order
    order = service.create_order(user_id=user.id, plan_tier="RESEARCHER", interval="monthly")
    assert order["order_id"].startswith("order_")
    assert order["amount"] == 40000  # 400 * 100 paise
    assert order["currency"] == "INR"
    assert order["key_id"] == settings.razorpay_key_id
    assert order["plan_tier"] == "RESEARCHER"
    assert order["interval"] == "monthly"

    # Verify transaction logged in database
    tx = (
        db_session.query(PaymentTransaction)
        .filter_by(order_id=order["order_id"])
        .first()
    )
    assert tx is not None
    assert tx.user_id == user.id
    assert tx.amount_inr == 400
    assert tx.status == PaymentStatus.CREATED.value

    # Yearly order
    yearly_order = service.create_order(user_id=user.id, plan_tier="RESEARCHER", interval="yearly")
    assert yearly_order["amount"] == 400000  # 4000 * 100 paise
    assert yearly_order["interval"] == "yearly"


def test_unit_signature_verification_only():
    """UNIT TEST: Verify HMAC-SHA256 signature verification logic without database or entitlement side-effects."""
    order_id = "order_unit_test_12345"
    payment_id = "pay_unit_test_67890"
    secret = "test_secret_for_unit_hashing_99"

    msg = f"{order_id}|{payment_id}".encode("utf-8")
    valid_sig = hmac.new(secret.encode("utf-8"), msg, hashlib.sha256).hexdigest()

    # Valid signature returns True
    assert BillingService.verify_signature_only(order_id, payment_id, valid_sig, secret) is True

    # Tampered signature returns False
    assert BillingService.verify_signature_only(order_id, payment_id, "invalid_tampered_sig", secret) is False

    # Empty / None parameters return False
    assert BillingService.verify_signature_only("", payment_id, valid_sig, secret) is False
    assert BillingService.verify_signature_only(order_id, "", valid_sig, secret) is False
    assert BillingService.verify_signature_only(order_id, payment_id, "", secret) is False
    assert BillingService.verify_signature_only(order_id, payment_id, valid_sig, "") is False


def test_razorpay_gateway_verification_rejects_fabricated_payment(db_session):
    """GATEWAY TRUTH TEST: Verify that fabricated/invented payment IDs with local HMACs are REJECTED by Razorpay API.
    
    Ensures that local HMAC generation can NEVER grant subscription entitlements.
    """
    service = BillingService(db_session)

    user = _get_test_user(db_session, "test_gateway_rejection@example.com")

    # Ensure test user has FREE subscription baseline
    sub = db_session.query(Subscription).filter_by(user_id=user.id).first()
    if sub:
        sub.tier = "FREE"
        sub.is_verified_payment = False
        db_session.commit()

    # Create real Razorpay order
    order = service.create_order(user_id=user.id, plan_tier="RESEARCHER")
    order_id = order["order_id"]
    fake_payment_id = "pay_fabricated_fake_id_999"

    # Compute valid HMAC-SHA256 signature locally (simulating the flawed old test)
    msg = f"{order_id}|{fake_payment_id}".encode("utf-8")
    valid_local_sig = hmac.new(
        settings.razorpay_key_secret.encode("utf-8"),
        msg,
        hashlib.sha256,
    ).hexdigest()

    # Verify payment MUST FAIL because Razorpay API rejects fabricated payment ID
    with pytest.raises(ValueError, match="GATEWAY VERIFICATION REJECTED"):
        service.verify_payment(
            user_id=user.id,
            order_id=order_id,
            payment_id=fake_payment_id,
            signature=valid_local_sig,
        )

    # Verify subscription in DB was NOT upgraded to RESEARCHER
    db_session.expire_all()
    sub_after = db_session.query(Subscription).filter_by(user_id=user.id).first()
    if sub_after:
        assert sub_after.tier == "FREE"
        assert sub_after.is_verified_payment is False

    # Verify transaction in DB is marked FAILED and NOT gateway_verified
    tx = db_session.query(PaymentTransaction).filter_by(order_id=order_id).first()
    assert tx.status == PaymentStatus.FAILED.value
    assert tx.payment_state == PaymentStatus.FAILED.value
    assert tx.gateway_verified is False


def test_payment_verification_with_mocked_gateway_captured(db_session, monkeypatch):
    """INTEGRATION TEST: When Razorpay API officially confirms payment is captured, entitlement is granted."""
    service = BillingService(db_session)

    user = _get_test_user(db_session, "test_mock_captured@example.com")

    order = service.create_order(user_id=user.id, plan_tier="RESEARCHER")
    order_id = order["order_id"]
    payment_id = "pay_mock_verified_889900"

    msg = f"{order_id}|{payment_id}".encode("utf-8")
    valid_sig = hmac.new(
        settings.razorpay_key_secret.encode("utf-8"),
        msg,
        hashlib.sha256,
    ).hexdigest()

    # Mock official Razorpay Client.payment.fetch
    class MockRazorpayPayment:
        @staticmethod
        def fetch(pid):
            assert pid == payment_id
            return {
                "id": payment_id,
                "order_id": order_id,
                "status": "captured",
                "amount": 40000,
                "currency": "INR",
            }

    class MockRazorpayClient:
        def __init__(self, auth):
            self.payment = MockRazorpayPayment()

    import razorpay
    monkeypatch.setattr(razorpay, "Client", MockRazorpayClient)

    result = service.verify_payment(
        user_id=user.id,
        order_id=order_id,
        payment_id=payment_id,
        signature=valid_sig,
    )

    assert result["status"] == "success"
    assert result["tier"] == "RESEARCHER"
    assert result["payment_state"] == PaymentStatus.CAPTURED.value

    # Verify subscription in DB is legitimately upgraded
    sub = db_session.query(Subscription).filter_by(user_id=user.id).first()
    assert sub is not None
    assert sub.tier == "RESEARCHER"
    assert sub.status == "ACTIVE"
    assert sub.provider == "RAZORPAY"
    assert sub.is_verified_payment is True

    # Verify transaction in DB
    tx = db_session.query(PaymentTransaction).filter_by(order_id=order_id).first()
    assert tx.status == PaymentStatus.CAPTURED.value
    assert tx.payment_state == PaymentStatus.CAPTURED.value
    assert tx.gateway_verified is True


def test_payment_verification_invalid_signature_rejected(db_session):
    """Verify tampered/invalid signature is rejected with ValueError."""
    service = BillingService(db_session)

    user = db_session.query(User).first()
    order = service.create_order(user_id=user.id, plan_tier="RESEARCHER")
    order_id = order["order_id"]

    with pytest.raises(ValueError, match="Invalid payment signature"):
        service.verify_payment(
            user_id=user.id,
            order_id=order_id,
            payment_id="pay_fake_tampered_123",
            signature="tampered_hmac_hex_string_that_does_not_match",
        )


def test_payments_unconfigured_safeguard(db_session):
    """Verify that if credentials are removed, server-side fail-safe is triggered."""
    orig_key_id = settings.razorpay_key_id
    orig_secret = settings.razorpay_key_secret

    try:
        settings.razorpay_key_id = None
        settings.razorpay_key_secret = None
        service = BillingService(db_session)
        assert service.is_configured is False

        user = db_session.query(User).first()
        with pytest.raises(RuntimeError, match="PAYMENTS NOT CONFIGURED"):
            service.create_order(user_id=user.id, plan_tier="RESEARCHER")
    finally:
        settings.razorpay_key_id = orig_key_id
        settings.razorpay_key_secret = orig_secret


def test_webhook_signature_verification(db_session):
    """Verify webhook HMAC signature verification logic."""
    service = BillingService(db_session)
    payload_bytes = b'{"event":"payment.captured","payload":{}}'

    # Valid signature
    secret = settings.razorpay_webhook_secret
    expected_sig = hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()

    assert service.verify_webhook(payload_bytes, expected_sig) is True
    assert service.verify_webhook(payload_bytes, "wrong_sig_value") is False
    assert service.verify_webhook(payload_bytes, None) is False


def test_tampered_amount_rejected(db_session, monkeypatch):
    """SECURITY TEST: Gateway reporting different amount than expected paisa raises ValueError."""
    service = BillingService(db_session)
    user = _get_test_user(db_session, "test_tampered_amount@example.com")
    order = service.create_order(user_id=user.id, plan_tier="RESEARCHER", interval="monthly")
    order_id = order["order_id"]
    payment_id = "pay_tampered_amount_9988"

    msg = f"{order_id}|{payment_id}".encode("utf-8")
    valid_sig = hmac.new(settings.razorpay_key_secret.encode("utf-8"), msg, hashlib.sha256).hexdigest()

    # Tampered gateway returns 100 paisa (₹1) instead of 40000 paisa (₹400)
    class MockRazorpayPayment:
        @staticmethod
        def fetch(pid):
            return {
                "id": payment_id,
                "order_id": order_id,
                "status": "captured",
                "amount": 100,  # TAMPERED
                "currency": "INR",
            }

    class MockRazorpayClient:
        def __init__(self, auth):
            self.payment = MockRazorpayPayment()

    import razorpay
    monkeypatch.setattr(razorpay, "Client", MockRazorpayClient)

    with pytest.raises(ValueError, match="AMOUNT TAMPERING DETECTED"):
        service.verify_payment(user_id=user.id, order_id=order_id, payment_id=payment_id, signature=valid_sig)


def test_tampered_currency_rejected(db_session, monkeypatch):
    """SECURITY TEST: Gateway reporting currency other than INR is rejected."""
    service = BillingService(db_session)
    user = _get_test_user(db_session, "test_tampered_curr@example.com")
    order = service.create_order(user_id=user.id, plan_tier="RESEARCHER", interval="monthly")
    order_id = order["order_id"]
    payment_id = "pay_tampered_curr_9988"

    msg = f"{order_id}|{payment_id}".encode("utf-8")
    valid_sig = hmac.new(settings.razorpay_key_secret.encode("utf-8"), msg, hashlib.sha256).hexdigest()

    class MockRazorpayPayment:
        @staticmethod
        def fetch(pid):
            return {
                "id": payment_id,
                "order_id": order_id,
                "status": "captured",
                "amount": 40000,
                "currency": "USD",  # TAMPERED
            }

    class MockRazorpayClient:
        def __init__(self, auth):
            self.payment = MockRazorpayPayment()

    import razorpay
    monkeypatch.setattr(razorpay, "Client", MockRazorpayClient)

    with pytest.raises(ValueError, match="CURRENCY MISMATCH"):
        service.verify_payment(user_id=user.id, order_id=order_id, payment_id=payment_id, signature=valid_sig)


def test_cross_user_order_access_rejected(db_session):
    """SECURITY TEST: User B cannot verify or claim an order belonging to User A."""
    service = BillingService(db_session)
    user_a = _get_test_user(db_session, "user_a_owner@example.com")
    user_b = _get_test_user(db_session, "user_b_attacker@example.com")

    order = service.create_order(user_id=user_a.id, plan_tier="RESEARCHER")
    order_id = order["order_id"]
    payment_id = "pay_cross_user_123"

    msg = f"{order_id}|{payment_id}".encode("utf-8")
    valid_sig = hmac.new(settings.razorpay_key_secret.encode("utf-8"), msg, hashlib.sha256).hexdigest()

    with pytest.raises(PermissionError, match="Cross-user order access denied"):
        service.verify_payment(user_id=user_b.id, order_id=order_id, payment_id=payment_id, signature=valid_sig)


def test_invalid_interval_rejected(db_session):
    """VALIDATION TEST: Non-monthly/yearly intervals must be rejected with HTTP 400/ValueError."""
    service = BillingService(db_session)
    user = _get_test_user(db_session, "test_interval_val@example.com")

    for bad_interval in ["weekly", "lifetime", "biweekly", "invalid", "", "quarterly"]:
        with pytest.raises(ValueError, match="Invalid billing interval"):
            service.create_order(user_id=user.id, plan_tier="RESEARCHER", interval=bad_interval)


def test_invalid_plan_tier_rejected(db_session):
    """VALIDATION TEST: Non-existent plan tiers must be rejected with ValueError."""
    service = BillingService(db_session)
    user = _get_test_user(db_session, "test_plan_val@example.com")

    with pytest.raises(ValueError, match="Invalid plan tier"):
        service.create_order(user_id=user.id, plan_tier="SUPER_VIP_TIER")


def test_authorized_pending_capture_does_not_grant_entitlement(db_session, monkeypatch):
    """GATEWAY TRUTH: AUTHORIZED state does NOT grant entitlement."""
    service = BillingService(db_session)
    user = _get_test_user(db_session, "test_auth_only@example.com")

    # Set baseline FREE
    sub = db_session.query(Subscription).filter_by(user_id=user.id).first()
    if sub:
        sub.tier = "FREE"
        sub.is_verified_payment = False
        db_session.commit()

    order = service.create_order(user_id=user.id, plan_tier="RESEARCHER")
    order_id = order["order_id"]
    payment_id = "pay_auth_only_9988"

    msg = f"{order_id}|{payment_id}".encode("utf-8")
    valid_sig = hmac.new(settings.razorpay_key_secret.encode("utf-8"), msg, hashlib.sha256).hexdigest()

    class MockRazorpayPayment:
        @staticmethod
        def fetch(pid):
            return {
                "id": payment_id,
                "order_id": order_id,
                "status": "authorized",  # NOT CAPTURED
                "amount": 40000,
                "currency": "INR",
            }

    class MockRazorpayClient:
        def __init__(self, auth):
            self.payment = MockRazorpayPayment()

    import razorpay
    monkeypatch.setattr(razorpay, "Client", MockRazorpayClient)

    res = service.verify_payment(user_id=user.id, order_id=order_id, payment_id=payment_id, signature=valid_sig)
    assert res["status"] == "AUTHORIZED_PENDING_CAPTURE"

    # User MUST remain on FREE tier
    db_session.expire_all()
    sub_after = db_session.query(Subscription).filter_by(user_id=user.id).first()
    if sub_after:
        assert sub_after.tier == "FREE"
        assert sub_after.is_verified_payment is False


def test_idempotency_duplicate_verification(db_session, monkeypatch):
    """IDEMPOTENCY: Repeated verify_payment calls return ALREADY_PROCESSED and do not extend period."""
    service = BillingService(db_session)
    user = _get_test_user(db_session, "test_idempotency_flow@example.com")

    order = service.create_order(user_id=user.id, plan_tier="RESEARCHER")
    order_id = order["order_id"]
    payment_id = "pay_idempotency_captured_11"

    msg = f"{order_id}|{payment_id}".encode("utf-8")
    valid_sig = hmac.new(settings.razorpay_key_secret.encode("utf-8"), msg, hashlib.sha256).hexdigest()

    class MockRazorpayPayment:
        @staticmethod
        def fetch(pid):
            return {
                "id": payment_id,
                "order_id": order_id,
                "status": "captured",
                "amount": 40000,
                "currency": "INR",
            }

    class MockRazorpayClient:
        def __init__(self, auth):
            self.payment = MockRazorpayPayment()

    import razorpay
    monkeypatch.setattr(razorpay, "Client", MockRazorpayClient)

    res1 = service.verify_payment(user_id=user.id, order_id=order_id, payment_id=payment_id, signature=valid_sig)
    assert res1["status"] == "success"

    sub = db_session.query(Subscription).filter_by(user_id=user.id).first()
    original_end = sub.current_period_end

    # Second call
    res2 = service.verify_payment(user_id=user.id, order_id=order_id, payment_id=payment_id, signature=valid_sig)
    assert res2["status"] == "ALREADY_PROCESSED"

    # Period end was not modified/extended
    db_session.expire_all()
    sub_after = db_session.query(Subscription).filter_by(user_id=user.id).first()
    assert sub_after.current_period_end == original_end


def test_webhook_idempotency_and_replay(db_session):
    """IDEMPOTENCY: Webhook replaying payment.captured returns ALREADY_PROCESSED without double extension."""
    service = BillingService(db_session)
    user = _get_test_user(db_session, "test_webhook_replay@example.com")

    order = service.create_order(user_id=user.id, plan_tier="PRO", interval="monthly")
    order_id = order["order_id"]
    payment_id = "pay_webhook_replay_7766"

    event_payload = {
        "event": "payment.captured",
        "payload": {
            "payment": {
                "entity": {
                    "id": payment_id,
                    "order_id": order_id,
                    "amount": 70000,
                    "currency": "INR",
                    "status": "captured",
                }
            }
        },
    }

    # First event: processes and upgrades
    res1 = service.process_webhook_event(event_payload)
    assert res1["status"] == "success"
    assert res1["tier"] == "PRO"

    sub = db_session.query(Subscription).filter_by(user_id=user.id).first()
    assert sub.tier == "PRO"
    period_end = sub.current_period_end

    # Second replayed event: returns ALREADY_PROCESSED
    res2 = service.process_webhook_event(event_payload)
    assert res2["status"] == "ALREADY_PROCESSED"

    db_session.expire_all()
    sub_after = db_session.query(Subscription).filter_by(user_id=user.id).first()
    assert sub_after.current_period_end == period_end


def test_cancel_subscription_flow(db_session):
    """CANCEL: Canceling one-time order subscription marks cancel_at_period_end without fake gateway status."""
    service = BillingService(db_session)
    user = _get_test_user(db_session, "test_cancel_flow@example.com")

    # Set active subscription
    sub = db_session.query(Subscription).filter_by(user_id=user.id).first()
    if not sub:
        sub = Subscription(user_id=user.id, tier="RESEARCHER", status="ACTIVE", provider="RAZORPAY")
        db_session.add(sub)
    else:
        sub.tier = "RESEARCHER"
        sub.status = "ACTIVE"
        sub.cancel_at_period_end = False
    db_session.commit()

    res = service.cancel_subscription(user.id)
    assert res["status"] == "success"
    assert res["gateway_cancellation"] is False

    db_session.expire_all()
    sub_after = db_session.query(Subscription).filter_by(user_id=user.id).first()
    assert sub_after.cancel_at_period_end is True
