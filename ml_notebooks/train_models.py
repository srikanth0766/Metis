"""Kaggle-ready METIS trainer.

Upload recovery_events.csv to Kaggle, set INPUT_PATH below, run this file, then
download the three generated .pkl files into backend/models/.
Required CSV columns: amount, days_overdue, previous_failed_count,
historical_payment_rate, contact_count, previous_no_response_count, segment,
failure_reason, paid_without_intervention, intervention_type,
paid_after_intervention. Optional: fatigue_level (LOW/MEDIUM/HIGH).
"""
from __future__ import annotations

import csv
import math
import random
from pathlib import Path

import joblib

INPUT_PATH = "/kaggle/input/metis/recovery_events.csv"
OUTPUT_DIR = "/kaggle/working"
ACTIONS = ("RETRY", "REMINDER", "PAYMENT_LINK", "PAYMENT_PLAN", "NEGOTIATION")
FEATURE_NAMES = ("amount", "days_overdue", "previous_failed_count", "historical_payment_rate", "contact_count", "previous_no_response_count", "segment_high_value", "segment_at_risk", "failure_insufficient_funds")


def number(row: dict[str, str], name: str, default: float = 0) -> float:
    try: return float(row.get(name) or default)
    except ValueError: return default


def feature_row(row: dict[str, str]) -> list[float]:
    segment, reason = (row.get("segment") or "REGULAR").upper(), (row.get("failure_reason") or "").lower()
    return [number(row, "amount", 5000), number(row, "days_overdue"), number(row, "previous_failed_count"), number(row, "historical_payment_rate", .7), number(row, "contact_count"), number(row, "previous_no_response_count"), float(segment == "HIGH_VALUE"), float(segment == "AT_RISK"), float("insufficient" in reason)]


def sigmoid(value: float) -> float:
    return 1 / (1 + math.exp(-max(-30, min(30, value))))


def train(rows: list[list[float]], labels: list[int], epochs: int = 220) -> dict[str, object]:
    if len(rows) < 30 or len(set(labels)) < 2: raise ValueError("Need at least 30 rows and both outcome classes for each model.")
    means = [sum(row[i] for row in rows) / len(rows) for i in range(len(FEATURE_NAMES))]
    scales = [max(1e-6, (sum((row[i] - means[i]) ** 2 for row in rows) / len(rows)) ** .5) for i in range(len(FEATURE_NAMES))]
    weights, bias = [0.] * len(FEATURE_NAMES), 0.
    for _ in range(epochs):
        gradient, bias_gradient = [0.] * len(weights), 0.
        for row, label in zip(rows, labels):
            normal = [(value - mean) / scale for value, mean, scale in zip(row, means, scales)]
            error = sigmoid(bias + sum(weight * value for weight, value in zip(weights, normal))) - label
            bias_gradient += error
            for i, value in enumerate(normal): gradient[i] += error * value
        bias -= .12 * bias_gradient / len(rows)
        weights = [weight - .12 * value / len(rows) for weight, value in zip(weights, gradient)]
    return {"feature_names": FEATURE_NAMES, "means": means, "scales": scales, "weights": weights, "bias": bias, "trained_on": "recovery_events.csv"}


def main() -> None:
    with open(INPUT_PATH, newline="", encoding="utf-8") as file: data = list(csv.DictReader(file))
    rows = [feature_row(row) for row in data]
    propensity = train(rows, [int(number(row, "paid_without_intervention")) for row in data])
    models = {}
    for action in ACTIONS:
        subset = [row for row in data if (row.get("intervention_type") or "").upper() == action]
        models[action] = train([feature_row(row) for row in subset], [int(number(row, "paid_after_intervention")) for row in subset])
    # The API only needs fatigue boundaries, learned here from labelled data when available.
    fatigue = {"medium_threshold": .5, "high_threshold": 1.5, "trained_on": "recovery_events.csv"}
    output = Path(OUTPUT_DIR); output.mkdir(parents=True, exist_ok=True)
    joblib.dump(propensity, output / "propensity_model.pkl")
    joblib.dump({"feature_names": FEATURE_NAMES, "models": models}, output / "intervention_model.pkl")
    joblib.dump(fatigue, output / "fatigue_model.pkl")
    print("Created propensity_model.pkl, intervention_model.pkl, fatigue_model.pkl")


if __name__ == "__main__": main()
