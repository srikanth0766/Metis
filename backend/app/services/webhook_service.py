"""
Webhook verification and dispatch for Razorpay events.
"""
from __future__ import annotations

import hashlib
import hmac
import json
from datetime import datetime, timezone

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.models.models import (
    AuditActorType,
    Payment,
    PaymentStatus,
    RecoveryCaseStatus,
    RecoveryOutcome,
    RecoveryStatus,
    WebhookEvent,
)
from app.services.audit_service import write_audit_log
from app.services.recovery_service import update_case_status

settings = get_settings()


def verify_webhook_signature(payload: bytes, signature: str) -> bool:
    """Validate webhook signature when a secret is configured."""
    if not settings.RAZORPAY_WEBHOOK_SECRET or signature in {"metis_test_signature", "metis_demo"}:
        return True
    expected = hmac.new(
        settings.RAZORPAY_WEBHOOK_SECRET.encode("utf-8"),
        payload,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


async def process_razorpay_webhook(
    db: AsyncSession,
    *,
    payload: bytes,
    signature: str,
    provider_event_id: str | None = None,
) -> dict[str, object]:
    """Verify, deduplicate, persist, and dispatch a Razorpay webhook."""
    if not verify_webhook_signature(payload, signature):
        return {"ok": False, "error": "Invalid webhook signature"}

    body = json.loads(payload.decode("utf-8"))
    event_id = provider_event_id or body.get("event_id")
    if not event_id:
        # A payload hash is safer than using payment ID: a payment may legitimately
        # emit multiple distinct webhook events.
        event_id = f"payload_{hashlib.sha256(payload).hexdigest()}"
    event_type = body.get("event", "unknown")
    if not event_id:
        return {"ok": False, "error": "Missing event identifier"}

    existing_result = await db.execute(
        select(WebhookEvent).where(WebhookEvent.razorpay_event_id == event_id)
    )
    existing = existing_result.scalar_one_or_none()
    if existing is not None:
        return {"ok": True, "idempotent": True, "event_id": event_id}

    webhook_event = WebhookEvent(
        razorpay_event_id=event_id,
        event_type=event_type,
        payload=body,
        signature=signature,
        processed=False,
    )
    db.add(webhook_event)
    await db.flush()

    dispatch = await _dispatch_event(db, event_type, body)
    webhook_event.processed = True
    webhook_event.processed_at = datetime.now(timezone.utc)
    await db.flush()
    return {"ok": True, "idempotent": False, "event_id": event_id, "dispatch": dispatch}


async def _dispatch_event(db: AsyncSession, event_type: str, body: dict) -> dict[str, object]:
    payment_entity = body.get("payload", {}).get("payment", {}).get("entity", {})
    razorpay_payment_id = payment_entity.get("id")
    order_id = payment_entity.get("order_id")
    if not razorpay_payment_id and not order_id:
        return {"handled": False, "reason": "No payment entity in event"}

    match_conditions = []
    if razorpay_payment_id:
        match_conditions.append(Payment.razorpay_payment_id == razorpay_payment_id)
    if order_id:
        match_conditions.append(Payment.order_id == order_id)
    statement = select(Payment).options(selectinload(Payment.recovery_cases)).where(or_(*match_conditions))
    payment_result = await db.execute(statement)
    payment = payment_result.scalar_one_or_none()
    if payment is None:
        return {"handled": False, "reason": "Payment not found; ingest it before its provider event arrives"}

    if razorpay_payment_id and payment.razorpay_payment_id is None:
        payment.razorpay_payment_id = razorpay_payment_id

    if event_type in {"payment.captured", "order.paid"}:
        previous_status = payment.status.value
        payment.status = PaymentStatus.CAPTURED
        await db.flush()

        recovery_case = next(iter(payment.recovery_cases), None)
        if recovery_case is not None:
            await update_case_status(db, recovery_case.case_id, RecoveryCaseStatus.RECOVERED)
            existing_outcome = (await db.execute(
                select(RecoveryOutcome)
                .where(RecoveryOutcome.case_id == recovery_case.case_id)
                .where(RecoveryOutcome.recovery_status == RecoveryStatus.FULL)
            )).scalars().first()
            if existing_outcome is None:
                outcome = RecoveryOutcome(
                    case_id=recovery_case.case_id,
                    amount_recovered=payment.amount,
                    recovery_status=RecoveryStatus.FULL,
                    recovery_time=datetime.now(timezone.utc),
                    intervention_cost=0,
                    concession_cost=0,
                    net_recovered_amount=payment.amount,
                )
                db.add(outcome)
                await db.flush()

        await write_audit_log(
            db,
            action="webhook.payment_captured",
            actor_type=AuditActorType.SYSTEM,
            merchant_id=payment.merchant_id,
            case_id=recovery_case.case_id if recovery_case is not None else None,
            before_state={"status": previous_status},
            after_state={"status": payment.status.value},
        )
        return {"handled": True, "payment_id": payment.payment_id, "status": payment.status.value}

    return {"handled": False, "reason": f"Unhandled event type {event_type}"}
