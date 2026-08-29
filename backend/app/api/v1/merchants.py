from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.models import Merchant
from app.schemas.schemas import MerchantRead

router = APIRouter(prefix="/merchants", tags=["merchants"])


@router.get("", response_model=list[MerchantRead])
async def list_merchants(db: AsyncSession = Depends(get_db)) -> list[Merchant]:
    result = await db.execute(select(Merchant).order_by(Merchant.created_at))
    return list(result.scalars().all())
