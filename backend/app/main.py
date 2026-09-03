from __future__ import annotations

import logging
import time
import uuid
from collections import defaultdict, deque
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1 import agent, audit, customers, dashboard, experiments, merchants, metrics, negotiation, payments, policies, razorpay, recovery, webhooks
from app.core.observability import observe_request
from app.core.database import engine
from app.ml import registry
from app.models import Base

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    registry.initialize()
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(title="METIS API", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_requests: dict[str, deque[float]] = defaultdict(deque)


@app.middleware("http")
async def request_context_and_rate_limit(request: Request, call_next):
    client = request.client.host if request.client else "unknown"
    now = time.monotonic()
    window = _requests[client]
    while window and now - window[0] > 60:
        window.popleft()
    if len(window) >= 120:
        return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded. Try again shortly."})
    window.append(now)
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    started = time.perf_counter()
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    observe_request(request.method, request.url.path, response.status_code, time.perf_counter() - started)
    return response


@app.get("/health", tags=["system"])
async def health() -> dict[str, object]:
    return {"ok": True, "service": "metis", "ml_mode": "stubs" if registry._USING_STUBS else "trained", "models": registry.model_registry.model_versions()}


for api_router in (
    merchants.router, customers.router, payments.router, recovery.router, policies.router, agent.router,
    negotiation.router, razorpay.router, webhooks.router, experiments.router,
    dashboard.router, audit.router, metrics.router,
):
    app.include_router(api_router, prefix="/api/v1")
