"""
ML inference registry.

At startup, attempts to load trained model files from disk.
Falls back to rule-based stubs if model files are not found.

Call sites import from this module — never directly from stubs.py or real model wrappers.
"""
from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, Optional

import joblib
import numpy as np

from app.ml import stubs
from app.models.models import FatigueLevel, InterventionType


MODEL_DIR = Path(__file__).resolve().parents[2] / "models"

PROPENSITY_PATH = MODEL_DIR / "propensity_model.pkl"
INTERVENTION_PATH = MODEL_DIR / "intervention_model.pkl"
UPLIFT_PATH = MODEL_DIR / "uplift_model.pkl"
FATIGUE_PATH = MODEL_DIR / "fatigue_model.pkl"


class ModelRegistry:
    """
    Central registry for METIS ML models.

    Loads:
      - propensity_model.pkl
      - intervention_model.pkl
      - uplift_model.pkl
      - fatigue_model.pkl

    All model artifacts are expected to contain LightGBM/sklearn
    estimators plus metadata such as feature_names and model_version.
    """

    def __init__(self) -> None:
        self._propensity_bundle: Optional[Dict[str, Any]] = None
        self._intervention_bundle: Optional[Dict[str, Any]] = None
        self._uplift_bundle: Optional[Dict[str, Any]] = None
        self._fatigue_bundle: Optional[Dict[str, Any]] = None

        self.initialized = False

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    def initialize(self) -> None:
        """Load all available model artifacts."""
        self._propensity_bundle = self._load_bundle(PROPENSITY_PATH)
        self._intervention_bundle = self._load_bundle(INTERVENTION_PATH)
        self._uplift_bundle = self._load_bundle(UPLIFT_PATH)
        self._fatigue_bundle = self._load_bundle(FATIGUE_PATH)

        self.initialized = True

    @staticmethod
    def _load_bundle(path: Path) -> Optional[Dict[str, Any]]:
        """Load a model bundle if it exists."""
        if not path.exists():
            return None

        bundle = joblib.load(path)

        if not isinstance(bundle, dict):
            raise ValueError(
                f"Invalid model artifact format: {path}. "
                "Expected a dictionary bundle."
            )

        return bundle

    # ------------------------------------------------------------------
    # Status / metadata
    # ------------------------------------------------------------------

    @property
    def ml_mode(self) -> str:
        """
        Returns the current ML execution mode.

        production -> all required models available
        partial    -> some models available
        stubs      -> no trained models available
        """
        loaded = [
            self._propensity_bundle,
            self._intervention_bundle,
            self._uplift_bundle,
            self._fatigue_bundle,
        ]

        count = sum(bundle is not None for bundle in loaded)

        if count == 4:
            return "production"

        if count > 0:
            return "partial"

        return "stubs"

    def model_versions(self) -> Dict[str, Optional[str]]:
        """Return model versions from the loaded artifacts."""
        return {
            "propensity": self._get_version(self._propensity_bundle),
            "intervention": self._get_version(self._intervention_bundle),
            "uplift": self._get_version(self._uplift_bundle),
            "fatigue": self._get_version(self._fatigue_bundle),
        }

    @staticmethod
    def _get_version(bundle: Optional[Dict[str, Any]]) -> Optional[str]:
        if bundle is None:
            return None

        return bundle.get("model_version")

    # ------------------------------------------------------------------
    # Feature preparation
    # ------------------------------------------------------------------

    @staticmethod
    def _build_features(
        context: Dict[str, Any],
        feature_names: list[str],
    ) -> np.ndarray:
        """
        Convert the backend context dictionary into the exact feature
        ordering expected by the trained model.
        """
        segment = str(context.get("segment", "REGULAR")).upper()
        reason = str(context.get("failure_reason", "")).lower()
        method = str(context.get("payment_method", "")).lower().replace(" ", "_")
        derived = {
            "segment_high_value": float(segment == "HIGH_VALUE"),
            "segment_at_risk": float(segment == "AT_RISK"),
            "failure_insufficient_funds": float("insufficient" in reason),
            "payment_method_card": float(method == "card"),
            "payment_method_upi": float(method == "upi"),
            "payment_method_netbanking": float(method in {"netbanking", "net_banking"}),
        }
        values = []

        for feature in feature_names:
            value = derived.get(feature, context.get(feature, 0))

            if value is None:
                value = 0

            # Convert booleans cleanly to numeric values.
            if isinstance(value, bool):
                value = int(value)

            # Handle categorical strings used by the simulator/models.
            if isinstance(value, str):
                value = ModelRegistry._encode_categorical(feature, value)

            values.append(float(value))

        return np.asarray([values], dtype=np.float64)

    @staticmethod
    def _encode_categorical(feature: str, value: str) -> float:
        """
        Encode categorical values used by the trained models.

        The training pipeline uses these numeric encodings, so the backend
        must reproduce the same mapping.
        """
        normalized = value.strip().lower()

        mappings = {
            "segment": {
                "normal": 0.0,
                "at_risk": 1.0,
                "high_value": 2.0,
                "high-value": 2.0,
            },
            "failure_reason": {
                "unknown": 0.0,
                "insufficient_funds": 1.0,
                "insufficient funds": 1.0,
                "expired_card": 2.0,
                "expired card": 2.0,
                "bank_decline": 3.0,
                "bank decline": 3.0,
                "network_error": 4.0,
                "network error": 4.0,
                "authentication_failed": 5.0,
                "authentication failed": 5.0,
            },
            "payment_method": {
                "unknown": 0.0,
                "card": 1.0,
                "upi": 2.0,
                "netbanking": 3.0,
                "net banking": 3.0,
                "wallet": 4.0,
            },
        }

        mapping = mappings.get(feature)

        if mapping is None:
            return 0.0

        return mapping.get(normalized, 0.0)

    # ------------------------------------------------------------------
    # Generic probability inference
    # ------------------------------------------------------------------

    @staticmethod
    def _predict_probability(
        model: Any,
        features: np.ndarray,
    ) -> float:
        """Run predict_proba and return P(y=1)."""
        if hasattr(model, "predict_proba"):
            probabilities = model.predict_proba(features)

            if probabilities.ndim != 2 or probabilities.shape[1] < 2:
                raise ValueError("Model returned invalid probability shape.")

            probability = float(probabilities[0, 1])

        elif hasattr(model, "predict"):
            prediction = model.predict(features)
            probability = float(prediction[0])

        else:
            raise TypeError(
                "Loaded model does not support predict_proba or predict."
            )

        return float(np.clip(probability, 0.0, 1.0))

    # ------------------------------------------------------------------
    # Propensity / natural recovery
    # ------------------------------------------------------------------

    def propensity(self, context: Dict[str, Any]) -> float:
        """
        Predict natural probability of payment without intervention.
        """
        if self._propensity_bundle is None:
            raise RuntimeError("Propensity model is not loaded.")

        model = self._propensity_bundle["model"]
        feature_names = self._propensity_bundle["feature_names"]

        features = self._build_features(context, feature_names)

        return self._predict_probability(model, features)

    # ------------------------------------------------------------------
    # Intervention models
    # ------------------------------------------------------------------

    def intervention_probability(
        self,
        action: str,
        context: Dict[str, Any],
    ) -> float:
        """
        Predict probability of payment under a specific intervention.

        IMPORTANT:
        This does NOT force the intervention probability to be above the
        natural probability. An intervention can have negative uplift.
        """
        if self._intervention_bundle is None:
            raise RuntimeError("Intervention model is not loaded.")

        models = self._intervention_bundle["models"]

        action_model = models.get(action)

        if action_model is None:
            raise ValueError(
                f"No intervention model found for action: {action}"
            )

        feature_names = self._intervention_bundle["feature_names"]

        features = self._build_features(context, feature_names)

        return self._predict_probability(action_model, features)

    # ------------------------------------------------------------------
    # Uplift model
    # ------------------------------------------------------------------

    def estimate_uplift(
        self,
        action: str,
        context: Dict[str, Any],
        natural_probability: Optional[float] = None,
    ) -> float:
        """
        Estimate incremental payment probability for an intervention.

        Preferred path:
            dedicated uplift T-learner

        Fallback:
            intervention probability - natural probability

        Negative uplift is intentionally allowed.
        """
        if natural_probability is None:
            natural_probability = self.propensity(context)

        # Preferred: causal effect estimator for heterogeneous treatment effects.
        if self._uplift_bundle is not None:
            feature_names = self._uplift_bundle.get("feature_names")
            causal_model = self._uplift_bundle.get("causal_models", {}).get(action)
            if causal_model is not None and feature_names is not None and hasattr(causal_model, "effect"):
                features = self._build_features(context, feature_names)
                effect = np.asarray(causal_model.effect(features)).reshape(-1)
                return float(np.clip(effect[0], -1.0, 1.0))

            # Compatible fallback for the current T-learner artifact.
            treatment_models = self._uplift_bundle.get("treatment_models", {})
            control_model = self._uplift_bundle.get("control_model")

            treatment_model = treatment_models.get(action)

            if (
                treatment_model is not None
                and control_model is not None
                and feature_names is not None
            ):
                features = self._build_features(context, feature_names)

                p_control = self._predict_probability(
                    control_model,
                    features,
                )

                p_treatment = self._predict_probability(
                    treatment_model,
                    features,
                )

                # Dedicated model's control estimate is authoritative
                # for uplift inference.
                return float(np.clip(p_treatment - p_control, -1.0, 1.0))

        # Safe fallback.
        p_with_intervention = self.intervention_probability(
            action,
            context,
        )

        return float(p_with_intervention - natural_probability)

    # ------------------------------------------------------------------
    # Fatigue
    # ------------------------------------------------------------------

    def contact_fatigue(self, context: Dict[str, Any]) -> float:
        """
        Return the probability that the customer is fatigued by contact.

        The multiclass fatigue model predicts:

            0 = low
            1 = medium
            2 = high

        We convert that into a continuous fatigue score in [0, 1].
        """
        if self._fatigue_bundle is None:
            raise RuntimeError("Fatigue model is not loaded.")

        model = self._fatigue_bundle["model"]
        feature_names = self._fatigue_bundle["feature_names"]

        features = self._build_features(context, feature_names)

        if not hasattr(model, "predict_proba"):
            raise TypeError(
                "Fatigue model must support predict_proba."
            )

        probabilities = model.predict_proba(features)

        if probabilities.ndim != 2:
            raise ValueError("Invalid fatigue probability output.")

        # Expected class index:
        # low    -> 0
        # medium -> 1
        # high   -> 2
        classes = getattr(model, "classes_", np.arange(probabilities.shape[1]))

        fatigue_score = 0.0

        for probability, class_label in zip(
            probabilities[0],
            classes,
        ):
            class_value = {"LOW": 0, "MEDIUM": 1, "HIGH": 2}.get(str(class_label).upper())
            if class_value is None:
                try:
                    class_value = int(class_label)
                except (TypeError, ValueError):
                    continue

            if class_value == 0:
                fatigue_score += float(probability) * 0.0
            elif class_value == 1:
                fatigue_score += float(probability) * 0.5
            elif class_value == 2:
                fatigue_score += float(probability) * 1.0

        return float(np.clip(fatigue_score, 0.0, 1.0))

    # ------------------------------------------------------------------
    # Expected net value
    # ------------------------------------------------------------------

    @staticmethod
    def expected_net_value(
        amount: float,
        uplift: float,
        intervention_cost: float = 0.0,
        success_fee_rate: float = 0.0,
    ) -> float:
        """
        Calculate incremental expected net revenue.

        Expected incremental revenue:
            amount * uplift

        Less:
            direct intervention cost
            success-based fee
        """
        gross_incremental_revenue = float(amount) * float(uplift)

        success_fee = (
            float(amount)
            * max(float(uplift), 0.0)
            * float(success_fee_rate)
        )

        net_value = (
            gross_incremental_revenue
            - float(intervention_cost)
            - success_fee
        )

        return float(net_value)


# Singleton registry used by the application.
model_registry = ModelRegistry()
_USING_STUBS = True


def initialize() -> None:
    """Initialize during FastAPI startup while retaining the existing ML API."""
    global _USING_STUBS
    try:
        model_registry.initialize()
        _USING_STUBS = model_registry.ml_mode != "production"
    except Exception:
        _USING_STUBS = True


def natural_recovery_probability(features: Dict[str, Any]) -> float:
    return stubs.predict_natural_recovery_probability(features) if _USING_STUBS else model_registry.propensity(features)


def intervention_probability(intervention_type: InterventionType, features: Dict[str, Any], p_natural: float) -> float:
    if _USING_STUBS:
        return stubs.predict_intervention_probability(intervention_type, features, p_natural)
    uplift = model_registry.estimate_uplift(intervention_type.value, features, p_natural)
    return float(np.clip(p_natural + uplift, 0.0, 1.0))


def contact_fatigue(features: Dict[str, Any]) -> FatigueLevel:
    if _USING_STUBS:
        return stubs.predict_contact_fatigue(features)
    score = model_registry.contact_fatigue(features)
    return FatigueLevel.LOW if score < .34 else FatigueLevel.MEDIUM if score < .67 else FatigueLevel.HIGH


def expected_net_value(
    intervention_type: InterventionType,
    uplift: float,
    recoverable_amount: Decimal,
    concession_amount: Decimal = Decimal("0"),
    fatigue_level: FatigueLevel = FatigueLevel.LOW,
) -> Dict[str, Decimal]:
    return stubs.calculate_expected_net_value(intervention_type, uplift, recoverable_amount, concession_amount, fatigue_level)


def get_model_registry() -> ModelRegistry:
    """Return the application-wide model registry."""
    return model_registry
