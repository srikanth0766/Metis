"""
Razorpay integration with a deterministic local mock fallback.
"""
from __future__ import annotations

import asyncio
import base64
import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from urllib import request

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.models import AuditActorType, Payment, PaymentStatus, RecoveryCase
from app.services.audit_service import write_audit_log

settings = get_settings()


def _has_credentials() -> bool:
    return bool(settings.RAZORPAY_KEY_ID and settings.RAZORPAY_KEY_SECRET)


async def _post_json(url: str, payload: dict) -> dict:
    auth = base64.b64encode(
        f"{settings.RAZORPAY_KEY_ID}:{settings.RAZORPAY_KEY_SECRET}".encode("utf-8")
    ).decode("ascii")

    def _send() -> dict:
        req = request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Basic {auth}",
            },
            method="POST",
        )
        with request.urlopen(req, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))

    return await asyncio.to_thread(_send)


async def create_payment_link(
    db: AsyncSession,
    case_id: str,
    description: str | None = None,
    expiry_minutes: int = 1440,
) -> dict[str, object]:
    """Create a Razorpay payment link or a deterministic mock response."""
    result = await db.execute(select(RecoveryCase).where(RecoveryCase.case_id == case_id))
    case = result.scalar_one_or_none()
    if case is None:
        return {"error": "Case not found"}

    payment_result = await db.execute(select(Payment).where(Payment.payment_id == case.payment_id))
    payment = payment_result.scalar_one_or_none()
    if payment is None:
        return {"error": "Payment not found"}

    expires_at = datetime.now(timezone.utc) + timedelta(minutes=expiry_minutes)
    if not _has_credentials() or settings.RAZORPAY_KEY_ID.startswith("rzp_test_XXXX"):
        payment_link_id = f"mock_link_{case.case_id[:8]}"
        short_url = f"https://mock.razorpay.local/pay/{payment_link_id}"
        mode = "mock"
    else:
        try:
            response = await _post_json(
                "https://api.razorpay.com/v1/payment_links",
                {
                    "amount": int(Decimal(payment.amount) * 100),
                    "currency": payment.currency,
                    "description": description or f"Recover payment for case {case.case_id}",
                    "expire_by": int(expires_at.timestamp()),
                    "reference_id": case.case_id,
                    "customer": {},
                    "notify": {"sms": True, "email": True},
                },
            )
            payment_link_id = response["id"]
            short_url = response["short_url"]
            mode = "live"
        except Exception:
            payment_link_id = f"mock_link_{case.case_id[:8]}"
            short_url = f"https://mock.razorpay.local/pay/{payment_link_id}"
            mode = "mock"

    await write_audit_log(
        db,
        action="razorpay.payment_link_created",
        actor_type=AuditActorType.SYSTEM,
        merchant_id=case.merchant_id,
        case_id=case.case_id,
        after_state={"payment_link_id": payment_link_id, "mode": mode},
    )
    return {
        "payment_link_id": payment_link_id,
        "short_url": short_url,
        "amount": Decimal(payment.amount),
        "currency": payment.currency,
        "expires_at": expires_at.isoformat(),
        "mode": mode,
    }


async def verify_payment_status(db: AsyncSession, payment_id: str) -> dict[str, object]:
    """Return the current local payment status."""
    result = await db.execute(select(Payment).where(Payment.payment_id == payment_id))
    payment = result.scalar_one_or_none()
    if payment is None:
        return {"error": "Payment not found"}

    return {
        "payment_id": payment.payment_id,
        "status": payment.status.value,
        "amount": Decimal(payment.amount),
        "currency": payment.currency,
        "razorpay_payment_id": payment.razorpay_payment_id,
        "is_paid": payment.status == PaymentStatus.CAPTURED,
    }
