"""Best-effort model explanations; never part of financial decision execution."""
from __future__ import annotations

from typing import Any

import numpy as np


def explain_tree_model(model: Any, row: np.ndarray, feature_names: list[str], top_k: int = 5) -> list[dict[str, Any]]:
    try:
        import shap

        values = shap.TreeExplainer(model).shap_values(row)
        if isinstance(values, list):
            values = values[1] if len(values) > 1 else values[0]
        values = np.asarray(values)
        if values.ndim == 2:
            values = values[0]
        ranked = sorted(zip(feature_names, values.astype(float)), key=lambda item: abs(item[1]), reverse=True)[:top_k]
        return [{"feature": name, "impact": round(value, 6), "direction": "positive" if value >= 0 else "negative"} for name, value in ranked]
    except Exception:
        return []
