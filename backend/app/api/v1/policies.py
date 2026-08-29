from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.models import InterventionPrediction, RecoveryCase
from app.policies.engine import validate_action
from app.schemas.schemas import (
    MerchantPolicyRead, MerchantPolicyUpdate, PolicySimulateRequest, PolicySimulateResult,
    PolicyValidateRequest, PolicyValidateResponse,
)
from app.services.policy_service import get_policy_object, update_policy

router = APIRouter(tags=["policies"])


@router.get("/merchants/{merchant_id}/policy", response_model=MerchantPolicyRead)
async def get_policy(merchant_id: str, db: AsyncSession = Depends(get_db)):
    return await get_policy_object(db, merchant_id)


@router.put("/merchants/{merchant_id}/policy", response_model=MerchantPolicyRead)
async def put_policy(
    merchant_id: str, payload: MerchantPolicyUpdate, db: AsyncSession = Depends(get_db)
):
    return await update_policy(db, merchant_id, payload)


@router.post("/policies/validate", response_model=PolicyValidateResponse)
async def validate_policy_action(
    payload: PolicyValidateRequest, db: AsyncSession = Depends(get_db)
) -> dict[str, object]:
    policy = await get_policy_object(db, payload.merchant_id)
    result = validate_action(payload.action, payload.parameters, policy)
    return {"allowed": result.allowed, "reason": result.reason}


@router.post("/policies/simulate", response_model=PolicySimulateResult)
async def simulate_policy(
    payload: PolicySimulateRequest, db: AsyncSession = Depends(get_db)
) -> dict[str, object]:
    current = await get_policy_object(db, payload.merchant_id)
    predictions = list((await db.execute(
        select(InterventionPrediction)
        .join(RecoveryCase, RecoveryCase.case_id == InterventionPrediction.case_id)
        .where(RecoveryCase.merchant_id == payload.merchant_id)
    )).scalars().all())
    current_value = sum((Decimal(item.expected_net_value) for item in predictions if item.expected_net_value > 0), Decimal("0"))
    proposed = payload.proposed_policy
    discount_factor = Decimal("1")
    if proposed.max_discount_percent is not None and proposed.max_discount_percent > current.max_discount_percent:
        discount_factor += Decimal(str(proposed.max_discount_percent - current.max_discount_percent)) / Decimal("100")
    contact_factor = Decimal("1")
    if proposed.max_contacts is not None and proposed.max_contacts < current.max_contacts:
        contact_factor = Decimal(str(proposed.max_contacts)) / Decimal(str(current.max_contacts))
    proposed_value = (current_value * discount_factor * contact_factor).quantize(Decimal("0.01"))
    return {
        "current_expected_recovery": current_value.quantize(Decimal("0.01")),
        "proposed_expected_recovery": proposed_value,
        "delta": proposed_value - current_value,
        "breakdown": {"cases_modelled": len(predictions), "note": "Estimate based on cached intervention predictions."},
    }
