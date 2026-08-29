from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.common import bad_request, not_found
from app.core.database import get_db
from app.models.models import Customer, Merchant, Payment, PaymentStatus
from app.schemas.schemas import PaymentCreate, PaymentRead

router = APIRouter(tags=["payments"])


@router.post("/payments", response_model=PaymentRead, status_code=201)
async def create_or_update_payment(
    payload: PaymentCreate, db: AsyncSession = Depends(get_db)
) -> Payment:
    """Idempotently ingest a payment using its Razorpay payment or order identifier."""
    customer = await db.get(Customer, payload.customer_id)
    if customer is None:
        raise not_found("Customer")
    if customer.merchant_id != payload.merchant_id:
        raise bad_request("Customer does not belong to the supplied merchant")
    if await db.get(Merchant, payload.merchant_id) is None:
        raise not_found("Merchant")
    if not payload.razorpay_payment_id and not payload.order_id:
        raise bad_request("Provide a Razorpay payment ID or order ID for idempotent ingestion")

    payment: Payment | None = None
    if payload.razorpay_payment_id:
        payment = (await db.execute(
            select(Payment).where(Payment.razorpay_payment_id == payload.razorpay_payment_id)
        )).scalar_one_or_none()
    if payment is None and payload.order_id:
        payment = (await db.execute(
            select(Payment)
            .where(Payment.merchant_id == payload.merchant_id)
            .where(Payment.order_id == payload.order_id)
        )).scalar_one_or_none()

    values = payload.model_dump()
    if payment is None:
        payment = Payment(**values)
        db.add(payment)
    else:
        if payment.merchant_id != payload.merchant_id or payment.customer_id != payload.customer_id:
            raise bad_request("External payment identifier is already owned by another merchant or customer")
        for field, value in values.items():
            setattr(payment, field, value)
    await db.flush()
    return payment


@router.get("/payments/{payment_id}", response_model=PaymentRead)
async def get_payment(payment_id: str, db: AsyncSession = Depends(get_db)) -> Payment:
    payment = await db.get(Payment, payment_id)
    if payment is None:
        raise not_found("Payment")
    return payment


@router.get("/recovery/opportunities", response_model=list[PaymentRead])
async def list_recovery_opportunities(
    merchant_id: str = Query(...), db: AsyncSession = Depends(get_db)
) -> list[Payment]:
    result = await db.execute(
        select(Payment)
        .where(Payment.merchant_id == merchant_id)
        .where(Payment.status.in_([PaymentStatus.FAILED, PaymentStatus.OVERDUE]))
        .order_by(Payment.amount.desc())
    )
    return list(result.scalars().all())
