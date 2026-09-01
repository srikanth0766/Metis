from __future__ import annotations

import numpy as np

from app.ml.registry import ModelRegistry


class BinaryModel:
    def predict_proba(self, features):
        return np.asarray([[0.3, 0.7]])


class FatigueModel:
    classes_ = np.asarray(["LOW", "MEDIUM", "HIGH"])

    def predict_proba(self, features):
        return np.asarray([[0.1, 0.3, 0.6]])


def test_registry_supports_string_fatigue_classes_and_uplift_models():
    registry = ModelRegistry()
    features = ["amount"]
    registry._propensity_bundle = {"model": BinaryModel(), "feature_names": features}
    registry._intervention_bundle = {"models": {"RETRY": BinaryModel()}, "feature_names": features}
    registry._uplift_bundle = {"control_model": BinaryModel(), "treatment_models": {"RETRY": BinaryModel()}, "feature_names": features}
    registry._fatigue_bundle = {"model": FatigueModel(), "feature_names": features}

    assert registry.propensity({"amount": 500}) == 0.7
    assert registry.estimate_uplift("RETRY", {"amount": 500}) == 0.0
    assert registry.contact_fatigue({"amount": 500}) == 0.75
    assert registry.ml_mode == "production"
