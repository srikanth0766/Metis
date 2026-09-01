from __future__ import annotations

import numpy as np

from app.ml.registry import ModelRegistry


class CausalEffectModel:
    def effect(self, features):
        return np.asarray([-0.12])


def test_registry_prefers_causal_effect_and_supports_negative_uplift():
    registry = ModelRegistry()
    registry._uplift_bundle = {
        "feature_names": ["amount", "payment_method_upi"],
        "causal_models": {"REMINDER": CausalEffectModel()},
    }
    assert registry.estimate_uplift("REMINDER", {"amount": 500, "payment_method": "UPI"}, .7) == -.12
    row = registry._build_features({"amount": 500, "payment_method": "UPI"}, ["amount", "payment_method_upi"])
    assert row.tolist() == [[500.0, 1.0]]
