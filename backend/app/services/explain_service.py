from __future__ import annotations

from typing import Any

from app.ml import registry
from app.ml.explain import explain_tree_model
from app.services.context_service import get_customer_context_data, get_payment_context_data


async def explain_case(db: Any, case: Any) -> dict[str, Any]:
    """Return available local feature explanations without affecting decisioning."""
    if registry._USING_STUBS:
        return {"mode": "stubs", "propensity": [], "interventions": {}}
    features = {**(await get_customer_context_data(db, case.customer_id)), **(await get_payment_context_data(db, case.payment_id))}
    result: dict[str, Any] = {"mode": "trained", "propensity": [], "interventions": {}}
    propensity = registry.model_registry._propensity_bundle
    intervention = registry.model_registry._intervention_bundle
    if propensity:
        names = propensity.get("feature_names", [])
        result["propensity"] = explain_tree_model(propensity["model"], registry.model_registry._build_features(features, names), names)
    if intervention:
        names = intervention.get("feature_names", [])
        row = registry.model_registry._build_features(features, names)
        result["interventions"] = {action: explain_tree_model(model, row, names) for action, model in intervention.get("models", {}).items()}
    return result
