"""
Experiment assignment and results helpers.
"""
from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import (
    AuditActorType,
    Experiment,
    ExperimentAssignment,
    InterventionType,
    RecoveryOutcome,
)
from app.services.audit_service import write_audit_log


async def assign_case_to_experiment(
    db: AsyncSession,
    experiment_id: str,
    case_id: str,
    *,
    group_name: str | None = None,
    intervention_type: InterventionType | None = None,
) -> ExperimentAssignment:
    """Assign a case to an experiment group, deterministically if group missing."""
    existing_result = await db.execute(
        select(ExperimentAssignment)
        .where(ExperimentAssignment.experiment_id == experiment_id)
        .where(ExperimentAssignment.case_id == case_id)
    )
    existing = existing_result.scalar_one_or_none()
    if existing is not None:
        return existing

    if group_name is None:
        groups = ["CONTROL", "RETRY", "REMINDER", "PAYMENT_PLAN", "NEGOTIATION"]
        group_name = groups[sum(ord(ch) for ch in case_id) % len(groups)]

    assignment = ExperimentAssignment(
        experiment_id=experiment_id,
        case_id=case_id,
        group_name=group_name,
        intervention_type=intervention_type,
    )
    db.add(assignment)
    await db.flush()

    experiment_result = await db.execute(
        select(Experiment).where(Experiment.experiment_id == experiment_id)
    )
    experiment = experiment_result.scalar_one_or_none()

    await write_audit_log(
        db,
        action="experiment.case_assigned",
        actor_type=AuditActorType.SYSTEM,
        merchant_id=experiment.merchant_id if experiment is not None else None,
        case_id=case_id,
        after_state={"experiment_id": experiment_id, "group_name": group_name},
    )
    return assignment


async def calculate_experiment_results(db: AsyncSession, experiment_id: str) -> dict[str, object]:
    """Calculate simple incremental lift metrics from experiment outcomes."""
    result = await db.execute(
        select(ExperimentAssignment, RecoveryOutcome)
        .outerjoin(RecoveryOutcome, RecoveryOutcome.case_id == ExperimentAssignment.case_id)
        .where(ExperimentAssignment.experiment_id == experiment_id)
    )
    rows = result.all()
    if not rows:
        return {
            "experiment_id": experiment_id,
            "groups": [],
            "total_recovery_rate": 0.0,
            "incremental_lift": 0.0,
            "incremental_revenue": Decimal("0.00"),
            "net_recovery": Decimal("0.00"),
            "intervention_cost": Decimal("0.00"),
            "concession_cost": Decimal("0.00"),
        }

    grouped: dict[str, dict[str, object]] = defaultdict(
        lambda: {
            "group_name": "",
            "assigned_cases": 0,
            "recovered_cases": 0,
            "recovery_rate": 0.0,
            "recovered_amount": Decimal("0.00"),
            "intervention_cost": Decimal("0.00"),
            "concession_cost": Decimal("0.00"),
            "net_recovery": Decimal("0.00"),
        }
    )

    total_cases = 0
    total_recovered = 0
    total_revenue = Decimal("0.00")
    total_intervention_cost = Decimal("0.00")
    total_concession_cost = Decimal("0.00")

    for assignment, outcome in rows:
        bucket = grouped[assignment.group_name]
        bucket["group_name"] = assignment.group_name
        bucket["assigned_cases"] = int(bucket["assigned_cases"]) + 1
        total_cases += 1

        if outcome is not None and outcome.amount_recovered:
            recovered_amount = Decimal(outcome.amount_recovered)
            bucket["recovered_cases"] = int(bucket["recovered_cases"]) + 1
            bucket["recovered_amount"] = Decimal(bucket["recovered_amount"]) + recovered_amount
            bucket["intervention_cost"] = Decimal(bucket["intervention_cost"]) + Decimal(outcome.intervention_cost or 0)
            bucket["concession_cost"] = Decimal(bucket["concession_cost"]) + Decimal(outcome.concession_cost or 0)
            total_recovered += 1
            total_revenue += recovered_amount
            total_intervention_cost += Decimal(outcome.intervention_cost or 0)
            total_concession_cost += Decimal(outcome.concession_cost or 0)

    for bucket in grouped.values():
        assigned_cases = int(bucket["assigned_cases"])
        recovered_cases = int(bucket["recovered_cases"])
        recovered_amount = Decimal(bucket["recovered_amount"])
        intervention_cost = Decimal(bucket["intervention_cost"])
        concession_cost = Decimal(bucket["concession_cost"])
        bucket["recovery_rate"] = recovered_cases / assigned_cases if assigned_cases else 0.0
        bucket["net_recovery"] = recovered_amount - intervention_cost - concession_cost

    control_rate = float(grouped["CONTROL"]["recovery_rate"]) if "CONTROL" in grouped else 0.0
    best_treatment_rate = max(
        (
            float(bucket["recovery_rate"])
            for name, bucket in grouped.items()
            if name != "CONTROL"
        ),
        default=0.0,
    )

    return {
        "experiment_id": experiment_id,
        "groups": list(grouped.values()),
        "total_recovery_rate": total_recovered / total_cases if total_cases else 0.0,
        "incremental_lift": best_treatment_rate - control_rate,
        "incremental_revenue": total_revenue,
        "net_recovery": total_revenue - total_intervention_cost - total_concession_cost,
        "intervention_cost": total_intervention_cost,
        "concession_cost": total_concession_cost,
    }
