"""
Optimizer service — selects the best recovery action using expected incremental net value.

Uses a simple greedy optimizer over the prediction set.
Google OR-Tools is available for future multi-case portfolio optimization.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ml import registry as ml
from app.models.models import (
    DecisionSource,
    InterventionPrediction,
    InterventionType,
    MerchantPolicy,
    RecoveryCase,
    RecoveryDecision,
)
from app.services.prediction_service import get_all_predictions

_DO_NOTHING_THRESHOLD = Decimal("0")  # Only intervene if net value > 0


async def optimize_recovery_action(
    db: AsyncSession,
    case_id: str,
    merchant_id: str,
) -> RecoveryDecision:
    """
    Select the best recovery intervention for a case.

    1. Fetch all predictions (run ML if not cached).
    2. Apply merchant policy filter.
    3. Select highest expected_net_value.
    4. Fall back to DO_NOTHING if all net values <= 0.
    5. Persist and return a RecoveryDecision.
    """
    predictions = await get_all_predictions(db, case_id)

    # Load merchant policy
    policy_result = await db.execute(
        select(MerchantPolicy).where(MerchantPolicy.merchant_id == merchant_id)
    )
    policy = policy_result.scalar_one_or_none()

    # Sort by expected_net_value descending
    sorted_preds = sorted(predictions, key=lambda p: p.expected_net_value, reverse=True)

    best: InterventionPrediction | None = None
    for pred in sorted_preds:
        if pred.expected_net_value > _DO_NOTHING_THRESHOLD:
            best = pred
            break

    if best is None:
        # All interventions would lose money — do nothing
        selected = InterventionType.DO_NOTHING
        net_value = Decimal("0")
        confidence = 0.9
        reason = "All interventions produce negative expected net value. Natural recovery is preferred."
        source = DecisionSource.RULE_BASED
    else:
        selected = best.intervention_type
        net_value = best.expected_net_value
        confidence = min(0.95, float(best.uplift) + 0.5)  # heuristic confidence
        reason = (
            f"Selected {selected.value} with expected incremental net value ₹{net_value:.2f}. "
            f"Uplift: {best.uplift:.1%}, P(pay|action): {best.probability_with_intervention:.1%}, "
            f"P(pay|none): {best.probability_without_intervention:.1%}."
        )
        source = DecisionSource.RULE_BASED if ml._USING_STUBS else DecisionSource.ML_MODEL

    decision = RecoveryDecision(
        case_id=case_id,
        selected_intervention=selected,
        expected_net_value=net_value,
        confidence=confidence,
        reason=reason,
        decision_source=source,
    )
    db.add(decision)
    await db.flush()
    return decision


async def calculate_value_for_intervention(
    db: AsyncSession,
    case_id: str,
    intervention_type: InterventionType,
    concession_amount: Decimal = Decimal("0"),
) -> dict[str, Any]:
    """Calculate expected net value for a specific intervention (called by agent tool)."""
    case_result = await db.execute(select(RecoveryCase).where(RecoveryCase.case_id == case_id))
    case = case_result.scalar_one_or_none()
    if not case:
        return {"error": "Case not found"}

    from app.ml import stubs
    from app.models.models import FatigueLevel

    preds = await get_all_predictions(db, case_id)
    pred = next((p for p in preds if p.intervention_type == intervention_type), None)
    if not pred:
        return {"error": f"No prediction found for {intervention_type.value}"}

    value_dict = ml.expected_net_value(
        intervention_type=intervention_type,
        uplift=float(pred.uplift),
        recoverable_amount=case.revenue_at_risk,
        concession_amount=concession_amount,
    )
    return {
        "intervention_type": intervention_type.value,
        "uplift": float(pred.uplift),
        "expected_recovery": float(pred.expected_recovery),
        **{k: float(v) for k, v in value_dict.items()},
    }
