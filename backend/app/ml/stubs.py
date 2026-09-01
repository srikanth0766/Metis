"""
ML inference layer — rule-based stubs.

Used when trained model files are not present.
All functions return deterministic, explainable outputs based on domain heuristics.
These stubs match the same interface as the real model wrappers so they can be
swapped without changing call sites.
"""
from __future__ import annotations

import math
from decimal import Decimal
from typing import Any

from app.models.models import FatigueLevel, InterventionType


# ─── Propensity Stub ─────────────────────────────────────────────────────────


def predict_natural_recovery_probability(features: dict[str, Any]) -> float:
    """
    Estimate P(customer pays | no intervention).

    Key features used:
    - days_overdue: the longer overdue, the less likely natural recovery
    - historical_payment_rate: fraction of past payments completed on time
    - previous_failed_count: more failures → less likely
    - amount: large amounts harder to recover naturally
    """
    days_overdue: int = features.get("days_overdue", 0)
    hist_rate: float = features.get("historical_payment_rate", 0.7)
    prev_failed: int = features.get("previous_failed_count", 0)
    amount: float = float(features.get("amount", 5000))

    # Base probability from history
    base = hist_rate

    # Penalty for days overdue (logarithmic decay)
    overdue_penalty = min(0.5, math.log1p(days_overdue) * 0.06)

    # Penalty for previous failures
    failure_penalty = min(0.3, prev_failed * 0.07)

    # Slight penalty for large amounts
    amount_penalty = min(0.1, math.log10(max(amount, 1)) * 0.02)

    prob = base - overdue_penalty - failure_penalty - amount_penalty
    return max(0.02, min(0.95, prob))


# ─── Intervention Response Stubs ─────────────────────────────────────────────


_INTERVENTION_BASE_LIFT: dict[InterventionType, float] = {
    InterventionType.RETRY: 0.08,
    InterventionType.REMINDER: 0.14,
    InterventionType.PAYMENT_LINK: 0.18,
    InterventionType.PAYMENT_PLAN: 0.28,
    InterventionType.NEGOTIATION: 0.32,
    InterventionType.ESCALATION: 0.12,
    InterventionType.DO_NOTHING: 0.0,
}

_INTERVENTION_COST: dict[InterventionType, float] = {
    InterventionType.RETRY: 50,
    InterventionType.REMINDER: 20,
    InterventionType.PAYMENT_LINK: 30,
    InterventionType.PAYMENT_PLAN: 100,
    InterventionType.NEGOTIATION: 200,
    InterventionType.ESCALATION: 500,
    InterventionType.DO_NOTHING: 0,
}


def predict_intervention_probability(
    intervention_type: InterventionType,
    features: dict[str, Any],
    p_natural: float,
) -> float:
    """
    Estimate P(customer pays | intervention).

    Returns a probability clipped to [p_natural, 0.97].
    Interventions can only help, not hurt (stub assumption).
    """
    base_lift = _INTERVENTION_BASE_LIFT.get(intervention_type, 0.0)

    # Adjust lift based on customer segment
    segment = features.get("segment", "REGULAR")
    segment_mult = {"HIGH_VALUE": 1.15, "REGULAR": 1.0, "AT_RISK": 0.85, "DORMANT": 0.7}.get(segment, 1.0)

    # Adjust for failure reason
    failure_reason = features.get("failure_reason", "")
    if "insufficient" in failure_reason.lower():
        if intervention_type in (InterventionType.PAYMENT_PLAN, InterventionType.NEGOTIATION):
            segment_mult *= 1.2  # payment plans especially effective for cash-flow issues

    adjusted_lift = base_lift * segment_mult
    prob = p_natural + adjusted_lift
    return min(0.97, prob)


# ─── Uplift / Counterfactual ──────────────────────────────────────────────────


def estimate_uplift(
    intervention_type: InterventionType,
    p_natural: float,
    p_with_intervention: float,
) -> float:
    """Incremental impact = P(pay|action) - P(pay|no action)."""
    return max(0.0, p_with_intervention - p_natural)


# ─── Fatigue Model Stub ───────────────────────────────────────────────────────


def predict_contact_fatigue(features: dict[str, Any]) -> FatigueLevel:
    """
    Estimates customer contact fatigue.

    Inputs:
    - contact_count: how many times contacted so far
    - days_since_last_contact: days since last outreach
    - previous_no_response_count: how many messages went unanswered
    - channel_variety: number of distinct channels used
    """
    contact_count: int = features.get("contact_count", 0)
    no_response: int = features.get("previous_no_response_count", 0)
    days_since: int = features.get("days_since_last_contact", 999)

    score = contact_count * 0.3 + no_response * 0.5 - min(days_since, 30) * 0.02
    score = max(0.0, score)

    if score < 0.5:
        return FatigueLevel.LOW
    elif score < 1.5:
        return FatigueLevel.MEDIUM
    else:
        return FatigueLevel.HIGH


# ─── Recovery Value Engine ────────────────────────────────────────────────────


_FATIGUE_COST: dict[FatigueLevel, float] = {
    FatigueLevel.LOW: 0,
    FatigueLevel.MEDIUM: 100,
    FatigueLevel.HIGH: 300,
}


def calculate_expected_net_value(
    intervention_type: InterventionType,
    uplift: float,
    recoverable_amount: Decimal,
    concession_amount: Decimal = Decimal("0"),
    fatigue_level: FatigueLevel = FatigueLevel.LOW,
) -> dict[str, Decimal]:
    """
    Expected Incremental Net Revenue formula:

        Expected Incremental Revenue = uplift × recoverable_amount
        Expected Net Value = Incremental Revenue - intervention_cost - concession_cost - fatigue_cost
    """
    intervention_cost = Decimal(str(_INTERVENTION_COST.get(intervention_type, 0)))
    fatigue_cost = Decimal(str(_FATIGUE_COST.get(fatigue_level, 0)))

    incremental_revenue = Decimal(str(uplift)) * recoverable_amount
    net_value = incremental_revenue - intervention_cost - concession_amount - fatigue_cost

    return {
        "incremental_revenue": incremental_revenue.quantize(Decimal("0.01")),
        "intervention_cost": intervention_cost,
        "concession_cost": concession_amount,
        "fatigue_cost": fatigue_cost,
        "expected_net_value": net_value.quantize(Decimal("0.01")),
    }
