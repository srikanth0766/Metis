"""
Audit service for immutable write-only audit trail records.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import AuditActorType, AuditLog


async def write_audit_log(
    db: AsyncSession,
    *,
    action: str,
    actor_type: AuditActorType,
    actor_id: str | None = None,
    merchant_id: str | None = None,
    case_id: str | None = None,
    before_state: Any | None = None,
    after_state: Any | None = None,
) -> AuditLog:
    """Create a new immutable audit record."""
    log = AuditLog(
        merchant_id=merchant_id,
        case_id=case_id,
        actor_type=actor_type,
        actor_id=actor_id,
        action=action,
        before_state=before_state,
        after_state=after_state,
    )
    db.add(log)
    await db.flush()
    return log
