"""
Dashboard aggregation helpers.
"""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import (
    Customer,
    InterventionPrediction,
    Payment,
    RecoveryCase,
    RecoveryCaseStatus,
    RecoveryOutcome,
)


async def get_dashboard_overview(db: AsyncSession, merchant_id: str) -> dict[str, object]:
    """Aggregate top-level dashboard metrics for one merchant."""
    cases_result = await db.execute(
        select(RecoveryCase).where(RecoveryCase.merchant_id == merchant_id)
    )
    cases = list(cases_result.scalars().all())

    predictions_result = await db.execute(
        select(InterventionPrediction)
        .join(RecoveryCase, RecoveryCase.case_id == InterventionPrediction.case_id)
        .where(RecoveryCase.merchant_id == merchant_id)
    )
    predictions = list(predictions_result.scalars().all())

    outcomes_result = await db.execute(
        select(RecoveryOutcome)
        .join(RecoveryCase, RecoveryCase.case_id == RecoveryOutcome.case_id)
        .where(RecoveryCase.merchant_id == merchant_id)
    )
    outcomes = list(outcomes_result.scalars().all())

    revenue_at_risk = sum((Decimal(case.revenue_at_risk) for case in cases), Decimal("0.00"))
    # Predictions contain one row per intervention; dashboard totals must use one
    # counterfactual and one best incremental option per recovery case.
    predictions_by_case: dict[str, list[InterventionPrediction]] = {}
    for prediction in predictions:
        predictions_by_case.setdefault(prediction.case_id, []).append(prediction)
    expected_natural_recovery = sum(
        (
            Decimal(str(case_predictions[0].probability_without_intervention))
            * next(case.revenue_at_risk for case in cases if case.case_id == case_id)
            for case_id, case_predictions in predictions_by_case.items()
        ),
        Decimal("0.00"),
    )
    expected_incremental_recovery = sum(
        (
            max((Decimal(pred.expected_net_value) for pred in case_predictions), default=Decimal("0"))
            for case_predictions in predictions_by_case.values()
        ),
        Decimal("0.00"),
    )
    actual_recovered_revenue = sum(
        (Decimal(outcome.amount_recovered or 0) for outcome in outcomes),
        Decimal("0.00"),
    )

    return {
        "merchant_id": merchant_id,
        "revenue_at_risk": revenue_at_risk,
        "expected_natural_recovery": expected_natural_recovery.quantize(Decimal("0.01")),
        "expected_incremental_recovery": expected_incremental_recovery.quantize(Decimal("0.01")),
        "actual_recovered_revenue": actual_recovered_revenue.quantize(Decimal("0.01")),
        "open_cases": sum(1 for case in cases if case.status == RecoveryCaseStatus.OPEN),
        "in_progress_cases": sum(1 for case in cases if case.status == RecoveryCaseStatus.IN_PROGRESS),
        "recovered_cases": sum(1 for case in cases if case.status == RecoveryCaseStatus.RECOVERED),
        "escalated_cases": sum(1 for case in cases if case.status == RecoveryCaseStatus.ESCALATED),
    }


async def get_recovery_analytics(db: AsyncSession, merchant_id: str) -> dict[str, object]:
    """Aggregate analytics breakdowns for charting."""
    by_intervention_result = await db.execute(
        select(
            InterventionPrediction.intervention_type,
            func.count(InterventionPrediction.prediction_id),
            func.sum(InterventionPrediction.expected_net_value),
        )
        .join(RecoveryCase, RecoveryCase.case_id == InterventionPrediction.case_id)
        .where(RecoveryCase.merchant_id == merchant_id)
        .group_by(InterventionPrediction.intervention_type)
    )

    by_segment_result = await db.execute(
        select(Customer.segment, func.count(RecoveryCase.case_id))
        .join(RecoveryCase, RecoveryCase.customer_id == Customer.customer_id)
        .where(RecoveryCase.merchant_id == merchant_id)
        .group_by(Customer.segment)
    )

    by_payment_method_result = await db.execute(
        select(Payment.payment_method, func.count(Payment.payment_id))
        .where(Payment.merchant_id == merchant_id)
        .group_by(Payment.payment_method)
    )

    by_failure_reason_result = await db.execute(
        select(Payment.failure_reason, func.count(Payment.payment_id))
        .where(Payment.merchant_id == merchant_id)
        .where(Payment.failure_reason.is_not(None))
        .group_by(Payment.failure_reason)
    )

    return {
        "by_intervention": [
            {
                "intervention_type": intervention_type.value,
                "count": count,
                "expected_net_value": float(expected_net_value or 0),
            }
            for intervention_type, count, expected_net_value in by_intervention_result.all()
        ],
        "by_customer_segment": [
            {"segment": segment.value, "count": count}
            for segment, count in by_segment_result.all()
        ],
        "by_payment_method": [
            {"payment_method": payment_method or "UNKNOWN", "count": count}
            for payment_method, count in by_payment_method_result.all()
        ],
        "by_failure_reason": [
            {"failure_reason": failure_reason, "count": count}
            for failure_reason, count in by_failure_reason_result.all()
        ],
    }
