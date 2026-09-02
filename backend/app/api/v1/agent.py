from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.agent import AgentRunner
from app.api.v1.common import bad_request, not_found
from app.core.config import get_settings
from app.core.database import get_db
from app.models.models import AgentRun, AgentRunStatus, AgentToolCall, RecoveryCase
from app.schemas.schemas import AgentMessageRequest, AgentMessageResponse, AgentRunCreate, AgentRunRead

router = APIRouter(prefix="/agent", tags=["agent"])
settings = get_settings()


async def _run_context(db: AsyncSession, run: AgentRun) -> dict[str, object]:
    case = await db.get(RecoveryCase, run.case_id)
    if case is None:
        raise not_found("Recovery case")
    return {
        "case_id": case.case_id,
        "merchant_id": case.merchant_id,
        "customer_id": case.customer_id,
        "payment_id": case.payment_id,
        "amount": case.revenue_at_risk,
    }


@router.post("/runs", response_model=AgentRunRead, status_code=201)
async def create_run(payload: AgentRunCreate, db: AsyncSession = Depends(get_db)) -> AgentRun:
    if await db.get(RecoveryCase, payload.case_id) is None:
        raise not_found("Recovery case")
    run = AgentRun(case_id=payload.case_id, model_name=settings.GROQ_MODEL, status=AgentRunStatus.RUNNING, input_summary="[]")
    db.add(run)
    await db.flush()
    return run


@router.get("/runs/{run_id}", response_model=AgentRunRead)
async def get_run(run_id: str, db: AsyncSession = Depends(get_db)) -> AgentRun:
    run = await db.get(AgentRun, run_id)
    if run is None:
        raise not_found("Agent run")
    return run


@router.get("/runs/{run_id}/tools")
async def get_tool_calls(run_id: str, db: AsyncSession = Depends(get_db)) -> list[dict[str, object]]:
    if await db.get(AgentRun, run_id) is None:
        raise not_found("Agent run")
    calls = list((await db.execute(select(AgentToolCall).where(AgentToolCall.run_id == run_id))).scalars().all())
    return [{"tool_name": call.tool_name, "arguments": call.arguments, "result": call.result, "policy_status": call.policy_status, "executed_at": call.executed_at} for call in calls]


@router.post("/runs/{run_id}/messages", response_model=AgentMessageResponse)
async def send_message(
    run_id: str, payload: AgentMessageRequest, db: AsyncSession = Depends(get_db)
) -> dict[str, object]:
    run = await db.get(AgentRun, run_id)
    if run is None:
        raise not_found("Agent run")
    if run.status in {AgentRunStatus.COMPLETED, AgentRunStatus.FAILED, AgentRunStatus.ESCALATED}:
        raise bad_request("This agent run is no longer active")
    try:
        history = json.loads(run.input_summary or "[]")
        context = await _run_context(db, run)
        if not settings.GROQ_API_KEY:
            reply = "I can help arrange an approved payment plan or send a secure payment link. Which would work best for you?"
            status = AgentRunStatus.RUNNING
        else:
            reply, status = await AgentRunner(db, run_id, context, history).step(payload.message)
        history.extend([{"role": "user", "content": payload.message}, {"role": "assistant", "content": reply}])
        run.input_summary = json.dumps(history)
        run.output_summary = reply
        run.status = status
        if status in {AgentRunStatus.ESCALATED, AgentRunStatus.COMPLETED}:
            run.completed_at = datetime.now(timezone.utc)
        await db.flush()
        count = len((await db.execute(select(AgentToolCall).where(AgentToolCall.run_id == run_id))).scalars().all())
        return {"run_id": run_id, "reply": reply, "status": status, "tool_calls_made": count}
    except Exception as exc:
        run.status = AgentRunStatus.FAILED
        run.completed_at = datetime.now(timezone.utc)
        await db.flush()
        raise bad_request("Agent could not process this message") from exc
