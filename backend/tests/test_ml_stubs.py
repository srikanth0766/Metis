from decimal import Decimal

from app.ml.stubs import calculate_expected_net_value, predict_intervention_probability, predict_natural_recovery_probability
from app.models.models import FatigueLevel, InterventionType


def test_intervention_probability_is_at_least_natural_probability():
    features = {"amount": 5000, "days_overdue": 3, "historical_payment_rate": 0.7, "contact_count": 0}
    natural = predict_natural_recovery_probability(features)
    assert predict_intervention_probability(InterventionType.PAYMENT_PLAN, features, natural) >= natural


def test_value_engine_includes_all_costs():
    value = calculate_expected_net_value(InterventionType.PAYMENT_LINK, 0.2, Decimal("10000"), fatigue_level=FatigueLevel.LOW)
    assert value["expected_net_value"] < Decimal("2000")
    assert value["intervention_cost"] > 0
