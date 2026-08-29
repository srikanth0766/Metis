"""
Recovery case lifecycle helpers.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import (
    AuditActorType,
    CustomerInteraction,
    InteractionChannel,
    InteractionDirection,
    Intervention,
    InterventionStatus,
    InterventionType,
    Payment,
    PaymentPlan,
    PaymentPlanFrequency,
    PaymentPlanStatus,
    PaymentStatus,
    RecoveryCase,
    RecoveryCaseStatus,
)
from app.policies.engine import validate_action
from app.services.audit_service import write_audit_log
from app.services.policy_service import get_policy_object


async def create_case_for_payment(db: AsyncSession, payment_id: str) -> RecoveryCase:
    """Create or return an open recovery case for a failed/overdue payment."""
    existing_result = await db.execute(
        select(RecoveryCase).where(RecoveryCase.payment_id == payment_id)
    )
    existing = existing_result.scalar_one_or_none()
    if existing is not None:
        return existing

    payment_result = await db.execute(select(Payment).where(Payment.payment_id == payment_id))
    payment = payment_result.scalar_one_or_none()
    if payment is None:
        raise ValueError("Payment not found")
    if payment.status not in {PaymentStatus.FAILED, PaymentStatus.OVERDUE}:
        raise ValueError("Recovery cases can only be created for failed or overdue payments")

    case = RecoveryCase(
        payment_id=payment.payment_id,
        customer_id=payment.customer_id,
        merchant_id=payment.merchant_id,
        status=RecoveryCaseStatus.OPEN,
        revenue_at_risk=payment.amount,
        priority_score=float(payment.amount),
    )
    db.add(case)
    await db.flush()

    await write_audit_log(
        db,
        action="recovery_case.created",
        actor_type=AuditActorType.SYSTEM,
        merchant_id=case.merchant_id,
        case_id=case.case_id,
        after_state={"payment_id": payment.payment_id, "status": case.status.value},
    )
    return case


async def update_case_status(
    db: AsyncSession,
    case_id: str,
    status: RecoveryCaseStatus,
    *,
    actor_type: AuditActorType = AuditActorType.SYSTEM,
    actor_id: str | None = None,
) -> RecoveryCase:
    """Update a recovery case status and close timestamps where appropriate."""
    result = await db.execute(select(RecoveryCase).where(RecoveryCase.case_id == case_id))
    case = result.scalar_one_or_none()
    if case is None:
        raise ValueError("Case not found")

    before_state = {"status": case.status.value, "closed_at": case.closed_at.isoformat() if case.closed_at else None}
    case.status = status
    case.closed_at = datetime.now(timezone.utc) if status in {
        RecoveryCaseStatus.RECOVERED,
        RecoveryCaseStatus.CLOSED,
    } else None
    await db.flush()

    await write_audit_log(
        db,
        action="recovery_case.status_updated",
        actor_type=actor_type,
        actor_id=actor_id,
        merchant_id=case.merchant_id,
        case_id=case.case_id,
        before_state=before_state,
        after_state={"status": case.status.value, "closed_at": case.closed_at.isoformat() if case.closed_at else None},
    )
    return case


async def create_payment_plan_for_case(
    db: AsyncSession,
    case_id: str,
    installment_count: int,
    frequency: str | PaymentPlanFrequency,
) -> PaymentPlan:
    """Create a policy-compliant payment plan for a case."""
    case_result = await db.execute(select(RecoveryCase).where(RecoveryCase.case_id == case_id))
    case = case_result.scalar_one_or_none()
    if case is None:
        raise ValueError("Case not found")

    plan_frequency = frequency if isinstance(frequency, PaymentPlanFrequency) else PaymentPlanFrequency(frequency)
    step_days = {
        PaymentPlanFrequency.WEEKLY: 7,
        PaymentPlanFrequency.BIWEEKLY: 14,
        PaymentPlanFrequency.MONTHLY: 30,
    }[plan_frequency]
    installment_amount = (
        Decimal(case.revenue_at_risk) / Decimal(installment_count)
    ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    policy = await get_policy_object(db, case.merchant_id)
    validation = validate_action(
        "CREATE_PAYMENT_PLAN",
        {
            "installment_count": installment_count,
            "period_days": step_days * installment_count,
            "installment_amount": installment_amount,
        },
        policy,
    )
    if not validation.allowed:
        raise ValueError(validation.reason or "Payment plan violates merchant policy")

    existing_result = await db.execute(
        select(PaymentPlan)
        .where(PaymentPlan.case_id == case_id)
        .where(PaymentPlan.status.in_([PaymentPlanStatus.PENDING, PaymentPlanStatus.ACTIVE]))
    )
    existing = existing_result.scalar_one_or_none()
    if existing is not None:
        return existing

    start_date = datetime.now(timezone.utc)
    end_date = start_date + timedelta(days=step_days * max(installment_count - 1, 0))
    plan = PaymentPlan(
        case_id=case.case_id,
        customer_id=case.customer_id,
        total_amount=case.revenue_at_risk,
        installment_count=installment_count,
        installment_amount=installment_amount,
        frequency=plan_frequency,
        start_date=start_date,
        end_date=end_date,
        status=PaymentPlanStatus.PENDING,
    )
    db.add(plan)

    intervention = Intervention(
        case_id=case.case_id,
        type=InterventionType.PAYMENT_PLAN,
        status=InterventionStatus.PENDING,
        cost=Decimal("0.00"),
        concession_amount=Decimal("0.00"),
    )
    db.add(intervention)
    case.status = RecoveryCaseStatus.IN_PROGRESS
    await db.flush()

    await write_audit_log(
        db,
        action="payment_plan.created",
        actor_type=AuditActorType.AGENT,
        merchant_id=case.merchant_id,
        case_id=case.case_id,
        after_state={
            "plan_id": plan.plan_id,
            "installment_count": installment_count,
            "installment_amount": float(plan.installment_amount),
            "frequency": plan.frequency.value,
        },
    )
    return plan


async def record_interaction(
    db: AsyncSession,
    case_id: str,
    customer_id: str,
    response_type: str,
    notes: str = "",
) -> CustomerInteraction:
    """Record a customer interaction or response event."""
    case_result = await db.execute(select(RecoveryCase).where(RecoveryCase.case_id == case_id))
    case = case_result.scalar_one_or_none()
    if case is None:
        raise ValueError("Case not found")

    interaction = CustomerInteraction(
        case_id=case_id,
        customer_id=customer_id,
        channel=InteractionChannel.IN_APP,
        direction=InteractionDirection.INBOUND,
        message=response_type,
        interaction_type=response_type,
        response=notes or None,
    )
    db.add(interaction)
    if case.status == RecoveryCaseStatus.OPEN:
        case.status = RecoveryCaseStatus.IN_PROGRESS
    await db.flush()

    await write_audit_log(
        db,
        action="customer_interaction.recorded",
        actor_type=AuditActorType.AGENT,
        merchant_id=case.merchant_id,
        case_id=case.case_id,
        after_state={"response_type": response_type, "notes": notes},
    )
    return interaction


async def escalate_case(db: AsyncSession, case_id: str, reason: str) -> RecoveryCase:
    """Escalate a case to human handling."""
    case = await update_case_status(
        db,
        case_id,
        RecoveryCaseStatus.ESCALATED,
        actor_type=AuditActorType.AGENT,
    )

    intervention = Intervention(
        case_id=case.case_id,
        type=InterventionType.ESCALATION,
        status=InterventionStatus.SUCCESS,
        completed_at=datetime.now(timezone.utc),
        cost=Decimal("0.00"),
        concession_amount=Decimal("0.00"),
    )
    db.add(intervention)
    await db.flush()

    await write_audit_log(
        db,
        action="recovery_case.escalated",
        actor_type=AuditActorType.AGENT,
        merchant_id=case.merchant_id,
        case_id=case.case_id,
        after_state={"reason": reason},
    )
    return case
