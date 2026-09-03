from __future__ import annotations

from prometheus_client import Counter, Histogram

REQUEST_COUNT = Counter("metis_http_requests_total", "HTTP requests", ["method", "path", "status"])
REQUEST_LATENCY = Histogram("metis_http_request_duration_seconds", "HTTP request latency", ["method", "path"])
ML_INFERENCES = Counter("metis_ml_inferences_total", "ML inferences", ["model"])
ML_LATENCY = Histogram("metis_ml_inference_duration_seconds", "ML inference latency", ["model"])


def observe_request(method: str, path: str, status: int, elapsed: float) -> None:
    REQUEST_COUNT.labels(method=method, path=path, status=str(status)).inc()
    REQUEST_LATENCY.labels(method=method, path=path).observe(elapsed)
