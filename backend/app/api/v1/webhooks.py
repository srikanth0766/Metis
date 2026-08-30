from __future__ import annotations

from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.common import bad_request
from app.core.database import get_db
from app.services.webhook_service import process_razorpay_webhook

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/razorpay")
async def razorpay_webhook(
    request: Request,
    x_razorpay_signature: str | None = Header(default=None),
    x_razorpay_event_id: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> dict[str, object]:
    try:
        return await process_razorpay_webhook(
            db,
            payload=await request.body(),
            signature=x_razorpay_signature or "",
            provider_event_id=x_razorpay_event_id,
        )
    except ValueError as exc:
        raise bad_request(str(exc)) from exc
