"""
Prediction service — runs ML inference for all interventions on a recovery case
and persists results to intervention_predictions.
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ml import registry as ml
from app.models.models import (
    Customer,
    FatigueLevel,
    InterventionPrediction,
    InterventionType,
    Payment,
    RecoveryCase,
)
from app.services.context_service import get_customer_context_data, get_payment_context_data

_ACTIONABLE_INTERVENTIONS = [
    InterventionType.RETRY,
    InterventionType.REMINDER,
    InterventionType.PAYMENT_LINK,
    InterventionType.PAYMENT_PLAN,
    InterventionType.NEGOTIATION,
]


async def run_predictions_for_case(
    db: AsyncSession,
    case: RecoveryCase,
) -> list[InterventionPrediction]:
    """
    Run ML inference for all intervention types on a recovery case.
    Persists InterventionPrediction rows and returns them.
    """
    customer_features = await get_customer_context_data(db, case.customer_id)
    payment_features = await get_payment_context_data(db, case.payment_id)

    features = {**customer_features, **payment_features}
    recoverable_amount = case.revenue_at_risk

    # Estimate contact fatigue
    result = await db.execute(
        select(RecoveryCase).where(RecoveryCase.case_id == case.case_id)
    )
    # Count interactions for fatigue
    from app.models.models import CustomerInteraction

    interactions_result = await db.execute(
        select(CustomerInteraction).where(CustomerInteraction.case_id == case.case_id)
    )
    interactions = interactions_result.scalars().all()
    features["contact_count"] = len(interactions)
    features["previous_no_response_count"] = sum(1 for i in interactions if not i.response)

    fatigue_level = ml.contact_fatigue(features)

    p_natural = ml.natural_recovery_probability(features)

    predictions: list[InterventionPrediction] = []

    for intervention_type in _ACTIONABLE_INTERVENTIONS:
        uplift = ml.model_registry.estimate_uplift(intervention_type.value, features, p_natural) if not ml._USING_STUBS else None
        p_with = ml.intervention_probability(intervention_type, features, p_natural)
        uplift = float(uplift) if uplift is not None else p_with - p_natural
        # A causal effect is authoritative. Keep probabilities and uplift coherent.
        p_with = max(0.0, min(1.0, p_natural + uplift))

        value_dict = ml.expected_net_value(
            intervention_type=intervention_type,
            uplift=uplift,
            recoverable_amount=recoverable_amount,
            fatigue_level=fatigue_level,
        )

        prediction = InterventionPrediction(
            case_id=case.case_id,
            intervention_type=intervention_type,
            probability_without_intervention=round(p_natural, 4),
            probability_with_intervention=round(p_with, 4),
            uplift=round(uplift, 4),
            expected_recovery=(Decimal(str(p_with)) * recoverable_amount).quantize(Decimal("0.01")),
            intervention_cost=value_dict["intervention_cost"],
            concession_cost=value_dict["concession_cost"],
            fatigue_cost=value_dict["fatigue_cost"],
            expected_net_value=value_dict["expected_net_value"],
            model_version="stub-v1" if ml._USING_STUBS else "trained-v1",
        )
        db.add(prediction)
        predictions.append(prediction)

    await db.flush()
    return predictions


async def get_all_predictions(
    db: AsyncSession,
    case_id: str,
) -> list[InterventionPrediction]:
    """Retrieve existing predictions for a case, or run them if absent."""
    result = await db.execute(
        select(InterventionPrediction)
        .where(InterventionPrediction.case_id == case_id)
        .order_by(InterventionPrediction.expected_net_value.desc())
    )
    existing = result.scalars().all()
    if existing:
        return list(existing)

    # Run fresh predictions
    case_result = await db.execute(select(RecoveryCase).where(RecoveryCase.case_id == case_id))
    case = case_result.scalar_one_or_none()
    if not case:
        return []
    return await run_predictions_for_case(db, case)
