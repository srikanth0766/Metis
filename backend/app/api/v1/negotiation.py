from __future__ import annotations

import json

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.common import bad_request, not_found
from app.core.database import get_db
from app.models.models import AgentRun, AgentRunStatus, CustomerInteraction, RecoveryCase
from app.schemas.schemas import NegotiationStart, NegotiationState, PaymentPlanCreate, PaymentPlanRead
from app.services.recovery_service import create_payment_plan_for_case

router = APIRouter(prefix="/recovery/cases", tags=["negotiation"])


@router.post("/{case_id}/negotiate", response_model=NegotiationState, status_code=201)
async def start_negotiation(case_id: str, payload: NegotiationStart, db: AsyncSession = Depends(get_db)) -> dict[str, object]:
    case = await db.get(RecoveryCase, case_id)
    if case is None:
        raise not_found("Recovery case")
    run = AgentRun(case_id=case_id, model_name="negotiation-workflow", status=AgentRunStatus.RUNNING, input_summary="[]")
    db.add(run)
    await db.flush()
    return {"case_id": case_id, "run_id": run.run_id, "status": run.status, "conversation": [], "attempts": 0, "current_offer": None}


@router.get("/{case_id}/negotiation", response_model=NegotiationState)
async def get_negotiation(case_id: str, db: AsyncSession = Depends(get_db)) -> dict[str, object]:
    if await db.get(RecoveryCase, case_id) is None:
        raise not_found("Recovery case")
    run = (await db.execute(select(AgentRun).where(AgentRun.case_id == case_id).order_by(AgentRun.started_at.desc()))).scalars().first()
    if run is None:
        raise not_found("Negotiation")
    interactions = list((await db.execute(select(CustomerInteraction).where(CustomerInteraction.case_id == case_id))).scalars().all())
    conversation = [{"role": "customer" if item.direction.value == "INBOUND" else "agent", "content": item.message} for item in interactions]
    return {"case_id": case_id, "run_id": run.run_id, "status": run.status, "conversation": conversation, "attempts": len(interactions), "current_offer": None}


@router.post("/{case_id}/payment-plan", response_model=PaymentPlanRead, status_code=201)
async def create_plan(case_id: str, payload: PaymentPlanCreate, db: AsyncSession = Depends(get_db)):
    if await db.get(RecoveryCase, case_id) is None:
        raise not_found("Recovery case")
    try:
        return await create_payment_plan_for_case(db, case_id, payload.installment_count, payload.frequency.value)
    except ValueError as exc:
        raise bad_request(str(exc)) from exc
