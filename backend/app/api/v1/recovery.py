from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.common import bad_request, not_found
from app.core.database import get_db
from app.models.models import InterventionPrediction, RecoveryCase, RecoveryDecision
from app.schemas.schemas import (
    CasePredictionsResponse, RecoveryCaseCreate, RecoveryCaseDetail, RecoveryCaseRead,
    RecoveryDecisionRead, SimulateRequest, SimulateResponse, SimulateResult,
)
from app.services.optimizer_service import optimize_recovery_action
from app.services.prediction_service import get_all_predictions
from app.services.recovery_service import create_case_for_payment, record_interaction
from app.services.explain_service import explain_case

router = APIRouter(prefix="/recovery", tags=["recovery"])


async def _case(db: AsyncSession, case_id: str, details: bool = False) -> RecoveryCase:
    statement = select(RecoveryCase).where(RecoveryCase.case_id == case_id)
    if details:
        statement = statement.options(selectinload(RecoveryCase.payment), selectinload(RecoveryCase.customer))
    case = (await db.execute(statement)).scalar_one_or_none()
    if case is None:
        raise not_found("Recovery case")
    return case


@router.post("/cases", response_model=RecoveryCaseRead, status_code=201)
async def create_case(payload: RecoveryCaseCreate, db: AsyncSession = Depends(get_db)) -> RecoveryCase:
    try:
        return await create_case_for_payment(db, payload.payment_id)
    except ValueError as exc:
        raise bad_request(str(exc)) from exc


@router.get("/cases", response_model=list[RecoveryCaseDetail])
async def list_cases(merchant_id: str = Query(...), db: AsyncSession = Depends(get_db)) -> list[RecoveryCase]:
    result = await db.execute(
        select(RecoveryCase)
        .where(RecoveryCase.merchant_id == merchant_id)
        .options(selectinload(RecoveryCase.payment), selectinload(RecoveryCase.customer))
        .order_by(RecoveryCase.updated_at.desc())
    )
    return list(result.scalars().all())


@router.get("/cases/{case_id}", response_model=RecoveryCaseDetail)
async def get_case(case_id: str, db: AsyncSession = Depends(get_db)) -> RecoveryCase:
    return await _case(db, case_id, details=True)


@router.get("/cases/{case_id}/explanation")
async def get_case_explanation(case_id: str, db: AsyncSession = Depends(get_db)) -> dict[str, object]:
    return await explain_case(db, await _case(db, case_id))


@router.get("/cases/{case_id}/predictions", response_model=CasePredictionsResponse)
async def get_predictions(case_id: str, db: AsyncSession = Depends(get_db)) -> dict[str, object]:
    await _case(db, case_id)
    return {"case_id": case_id, "predictions": await get_all_predictions(db, case_id)}


@router.get("/cases/{case_id}/recommendation", response_model=RecoveryDecisionRead)
async def get_recommendation(case_id: str, db: AsyncSession = Depends(get_db)) -> RecoveryDecision:
    await _case(db, case_id)
    decision = (await db.execute(
        select(RecoveryDecision).where(RecoveryDecision.case_id == case_id).order_by(RecoveryDecision.created_at.desc())
    )).scalars().first()
    if decision is None:
        raise not_found("Recovery recommendation")
    return decision


@router.post("/cases/{case_id}/optimize", response_model=RecoveryDecisionRead)
async def optimize_case(case_id: str, db: AsyncSession = Depends(get_db)) -> RecoveryDecision:
    case = await _case(db, case_id)
    return await optimize_recovery_action(db, case_id, case.merchant_id)


@router.post("/simulate", response_model=SimulateResponse)
async def simulate(payload: SimulateRequest, db: AsyncSession = Depends(get_db)) -> dict[str, object]:
    predictions = await get_all_predictions(db, payload.case_id)
    allowed = set(payload.interventions or [])
    results = [
        SimulateResult(
            intervention_type=prediction.intervention_type,
            probability_with_intervention=prediction.probability_with_intervention,
            uplift=prediction.uplift,
            expected_recovery=prediction.expected_recovery,
            expected_net_value=prediction.expected_net_value,
        )
        for prediction in predictions
        if not allowed or prediction.intervention_type in allowed
    ]
    return {"case_id": payload.case_id, "results": results}


@router.post("/cases/{case_id}/interactions", status_code=201)
async def add_interaction(case_id: str, payload: dict, db: AsyncSession = Depends(get_db)) -> dict[str, object]:
    case = await _case(db, case_id)
    interaction = await record_interaction(
        db,
        case_id=case_id,
        customer_id=case.customer_id,
        response_type=payload.get("response_type", "REMINDER"),
        notes=payload.get("notes", "")
    )
    return {"interaction_id": interaction.interaction_id, "status": "recorded"}
