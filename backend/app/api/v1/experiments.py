from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.common import not_found
from app.core.database import get_db
from app.models.models import Experiment
from app.schemas.schemas import ExperimentAssignRequest, ExperimentCreate, ExperimentRead, ExperimentResults
from app.services.experiment_service import assign_case_to_experiment, calculate_experiment_results

router = APIRouter(prefix="/experiments", tags=["experiments"])


@router.post("", response_model=ExperimentRead, status_code=201)
async def create_experiment(payload: ExperimentCreate, db: AsyncSession = Depends(get_db)) -> Experiment:
    experiment = Experiment(**payload.model_dump())
    db.add(experiment)
    await db.flush()
    return experiment


@router.get("", response_model=list[ExperimentRead])
async def list_experiments(merchant_id: str = Query(...), db: AsyncSession = Depends(get_db)) -> list[Experiment]:
    result = await db.execute(
        select(Experiment)
        .where(Experiment.merchant_id == merchant_id)
        .order_by(Experiment.created_at.desc())
    )
    return list(result.scalars().all())


@router.get("/{experiment_id}", response_model=ExperimentRead)
async def get_experiment(experiment_id: str, db: AsyncSession = Depends(get_db)) -> Experiment:
    experiment = await db.get(Experiment, experiment_id)
    if experiment is None:
        raise not_found("Experiment")
    return experiment


@router.post("/{experiment_id}/assign")
async def assign_experiment(
    experiment_id: str, payload: ExperimentAssignRequest, db: AsyncSession = Depends(get_db)
) -> dict[str, object]:
    if await db.get(Experiment, experiment_id) is None:
        raise not_found("Experiment")
    assignment = await assign_case_to_experiment(
        db, experiment_id, payload.case_id, group_name=payload.group_name, intervention_type=payload.intervention_type
    )
    return {"assignment_id": assignment.assignment_id, "group_name": assignment.group_name}


@router.get("/{experiment_id}/results", response_model=ExperimentResults)
async def experiment_results(experiment_id: str, db: AsyncSession = Depends(get_db)) -> dict[str, object]:
    if await db.get(Experiment, experiment_id) is None:
        raise not_found("Experiment")
    return await calculate_experiment_results(db, experiment_id)
