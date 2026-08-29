"""
Context service — assembles customer and payment feature dicts for ML inference.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.models import Customer, Payment, PaymentStatus, RecoveryCase


async def get_customer_context_data(db: AsyncSession, customer_id: str) -> dict[str, Any]:
    result = await db.execute(
        select(Customer)
        .where(Customer.customer_id == customer_id)
        .options(selectinload(Customer.payments))
    )
    customer = result.scalar_one_or_none()
    if not customer:
        return {"error": "Customer not found"}

    payments = customer.payments or []
    completed = [p for p in payments if p.status.value == "CAPTURED"]
    failed = [p for p in payments if p.status.value == "FAILED"]
    historical_rate = len(completed) / len(payments) if payments else 0.7

    return {
        "customer_id": customer_id,
        "name": customer.name,
        "email": customer.email,
        "phone": customer.phone,
        "segment": customer.segment.value,
        "total_payments": len(payments),
        "completed_payments": len(completed),
        "failed_payments": len(failed),
        "historical_payment_rate": historical_rate,
        "previous_failed_count": len(failed),
    }


async def get_payment_context_data(db: AsyncSession, payment_id: str) -> dict[str, Any]:
    result = await db.execute(
        select(Payment).where(Payment.payment_id == payment_id)
    )
    payment = result.scalar_one_or_none()
    if not payment:
        return {"error": "Payment not found"}

    days_overdue = 0
    if payment.failed_at:
        days_overdue = (datetime.now(timezone.utc) - payment.failed_at.replace(tzinfo=timezone.utc)).days

    return {
        "payment_id": payment_id,
        "amount": float(payment.amount),
        "currency": payment.currency,
        "payment_method": payment.payment_method,
        "status": payment.status.value,
        "failure_reason": payment.failure_reason or "",
        "days_overdue": days_overdue,
        "failed_at": payment.failed_at.isoformat() if payment.failed_at else None,
    }
