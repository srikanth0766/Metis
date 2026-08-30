from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.common import not_found
from app.core.database import get_db
from app.models.models import AgentRun, AgentToolCall, AuditLog, RecoveryCase
from app.schemas.schemas import CaseAuditTrail

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("/recovery/{case_id}", response_model=CaseAuditTrail)
async def recovery_audit(case_id: str, db: AsyncSession = Depends(get_db)) -> dict[str, object]:
    if await db.get(RecoveryCase, case_id) is None:
        raise not_found("Recovery case")
    logs = list((await db.execute(select(AuditLog).where(AuditLog.case_id == case_id).order_by(AuditLog.timestamp))).scalars().all())
    return {"case_id": case_id, "logs": logs}


@router.get("/agent/{run_id}")
async def agent_audit(run_id: str, db: AsyncSession = Depends(get_db)) -> list[dict[str, object]]:
    if await db.get(AgentRun, run_id) is None:
        raise not_found("Agent run")
    calls = list((await db.execute(select(AgentToolCall).where(AgentToolCall.run_id == run_id).order_by(AgentToolCall.executed_at))).scalars().all())
    return [{"tool_call_id": call.tool_call_id, "tool_name": call.tool_name, "arguments": call.arguments, "result": call.result, "policy_status": call.policy_status, "executed_at": call.executed_at} for call in calls]
