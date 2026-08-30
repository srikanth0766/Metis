from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.common import bad_request
from app.core.database import get_db
from app.schemas.schemas import PaymentLinkCreate, PaymentLinkResponse
from app.services.razorpay_service import create_payment_link, verify_payment_status

router = APIRouter(prefix="/razorpay", tags=["razorpay"])


@router.post("/payment-links", response_model=PaymentLinkResponse, status_code=201)
async def payment_link(payload: PaymentLinkCreate, db: AsyncSession = Depends(get_db)) -> dict[str, object]:
    try:
        return await create_payment_link(db, payload.case_id, payload.description, payload.expiry_minutes)
    except ValueError as exc:
        raise bad_request(str(exc)) from exc


@router.get("/payments/{payment_id}/verify")
async def verify_payment(payment_id: str, db: AsyncSession = Depends(get_db)) -> dict[str, object]:
    return await verify_payment_status(db, payment_id)
