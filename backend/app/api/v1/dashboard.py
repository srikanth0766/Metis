from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.models import AgentRun, AgentRunStatus, RecoveryCase
from app.schemas.schemas import DashboardOverview, RecoveryAnalytics
from app.services.dashboard_service import get_dashboard_overview, get_recovery_analytics

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/recovery", response_model=DashboardOverview)
async def recovery_overview(merchant_id: str = Query(...), db: AsyncSession = Depends(get_db)) -> dict[str, object]:
    return await get_dashboard_overview(db, merchant_id)


@router.get("/analytics", response_model=RecoveryAnalytics)
async def recovery_analytics(merchant_id: str = Query(...), db: AsyncSession = Depends(get_db)) -> dict[str, object]:
    return await get_recovery_analytics(db, merchant_id)


@router.get("/agent-activity")
async def agent_activity(merchant_id: str = Query(...), db: AsyncSession = Depends(get_db)) -> list[dict[str, object]]:
    result = await db.execute(
        select(AgentRun, RecoveryCase)
        .join(RecoveryCase, RecoveryCase.case_id == AgentRun.case_id)
        .where(RecoveryCase.merchant_id == merchant_id)
        .where(AgentRun.status == AgentRunStatus.RUNNING)
        .order_by(AgentRun.started_at.desc())
    )
    return [{"run_id": run.run_id, "case_id": case.case_id, "status": run.status, "started_at": run.started_at, "summary": run.output_summary} for run, case in result.all()]
