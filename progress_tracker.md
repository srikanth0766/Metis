# METIS — Progress Tracker
THIS FILE IS ONLY FOR KNOWING ABOUT THE PROGRESS OF PROJECT. ITS NOT A CHECKLIST. LOOK AT SOFTWARE REQUIREMENT SPECIFICATIONS
> Keep this file updated after every session. New agents must read this before touching any code.

---

## Last Updated
2026-09-05

---

## What Has Been Built

### Repository Structure
- `metis/` — root project directory created
- `metis/backend/app/{api/v1, core, models, schemas, services, ml, agent, policies}/` — all directories scaffolded
- `metis/backend/{alembic, tests}/` — created
- `metis/frontend/src/{app, components, lib, styles}/` — created
- `metis/ml_notebooks/` — created

### Config & Infrastructure
- `.env.example` — full environment variable template (DB, Redis, Razorpay, Groq, ML paths, MLflow)
- `docker-compose.yml` — orchestrates postgres:16, redis:7, backend (FastAPI), frontend (Next.js), mlflow

### Backend — Database Layer
- `backend/app/models/models.py` — **all 18 SQLAlchemy ORM models** as per SRS:
  - `Merchant`, `Customer`, `Payment`, `RecoveryCase`
  - `Intervention`, `InterventionPrediction`, `RecoveryDecision`
  - `MerchantPolicy`, `CustomerInteraction`, `PaymentPlan`
  - `Experiment`, `ExperimentAssignment`, `RecoveryOutcome`
  - `WebhookEvent` (with unique constraint on `razorpay_event_id` for idempotency)
  - `AgentRun`, `AgentToolCall`, `AuditLog`, `ModelVersion`
  - All enums defined: `InterventionType`, `RecoveryCaseStatus`, `PaymentStatus`, etc.
- `backend/app/models/__init__.py` — clean re-exports

### Backend — Core
- `backend/app/core/config.py` — Pydantic `Settings` class reading from `.env`; `use_ml_stubs` property auto-detects whether to use stubs
- `backend/app/core/database.py` — async SQLAlchemy engine + `AsyncSessionLocal` + `get_db()` FastAPI dependency
- `backend/app/core/security.py` — JWT creation/decoding, bcrypt password hashing

### Backend — Schemas
- `backend/app/schemas/schemas.py` — **all Pydantic request/response schemas** for every API endpoint:
  - Merchant, Customer, Payment, RecoveryCase (create + read + detail)
  - InterventionPrediction, RecoveryDecision, MerchantPolicy
  - PaymentPlan, Simulation, PolicySimulate
  - Agent (run, message request/response), Negotiation
  - Experiment, ExperimentAssign, ExperimentResults
  - Razorpay PaymentLink, Dashboard Overview, RecoveryAnalytics
  - AuditLog, CaseAuditTrail, OKResponse

### Backend — Policy Engine
- `backend/app/policies/engine.py` — **deterministic guardrail engine** (no LLM involvement):
  - `validate_action()` — validates DISCOUNT, CONTACT, NEGOTIATE, CREATE_PAYMENT_PLAN, CREATE_PAYMENT_LINK, RETRY, ESCALATE
  - `check_stopping_rules()` — evaluates merchant stopping rule configs
  - Returns `PolicyResult(allowed, reason)` — never raises silently

### Backend — ML Layer
- `backend/app/ml/stubs.py` — **rule-based ML stubs** (same interface as real models):
  - `predict_natural_recovery_probability()` — P(pay | no intervention), domain heuristics
  - `predict_intervention_probability()` — P(pay | each intervention type)
  - `predict_contact_fatigue()` — LOW / MEDIUM / HIGH fatigue level
  - `calculate_expected_net_value()` — full formula: uplift × amount − costs
- `backend/app/ml/registry.py` — model registry that tries to load real `.pkl` files at startup, silently falls back to stubs; all call sites use registry functions only

### Backend — AI Agent (Groq)
- `backend/app/agent/system_prompt.py` — structured system prompt constraining agent to merchant policy
- `backend/app/agent/tools.py` — **10 typed tool schemas** for the LLM + `ToolExecutor` class:
  - `get_customer_context`, `get_payment_context`, `get_recovery_options`
  - `get_merchant_policy`, `calculate_recovery_value`
  - `create_payment_plan` (calls policy engine before creating)
  - `create_payment_link`, `check_payment_status`
  - `record_customer_response`, `escalate_to_human`
- `backend/app/agent/agent.py` — `AgentRunner` class:
  - Groq-backed multi-turn tool loop (`llama-3.3-70b-versatile`)
  - `MAX_TOOL_ROUNDS = 8` safety cap
  - Persists every tool call to `agent_tool_calls` for audit trail
  - Auto-escalates on tool round overflow

### Backend — Services
- `backend/app/services/context_service.py` — assembles customer + payment feature dicts for ML and agent tools
- `backend/app/services/prediction_service.py` — runs full ML pipeline for all intervention types, persists to `intervention_predictions`
- `backend/app/services/optimizer_service.py` — selects best intervention by expected net value; falls back to `DO_NOTHING` if all net values ≤ 0
- `backend/app/services/policy_service.py` — default policy bootstrap, policy serialization, updates with audit logging
- `backend/app/services/recovery_service.py` — create case, status updates, payment plan creation, interaction logging, escalation flow
- `backend/app/services/razorpay_service.py` — payment-link creation with live Razorpay or mock fallback, local payment verification
- `backend/app/services/webhook_service.py` — signature verification, webhook idempotency, payment-captured dispatch into recovery outcomes
- `backend/app/services/experiment_service.py` — experiment group assignment and incremental lift metric aggregation
- `backend/app/services/audit_service.py` — immutable audit log writes
- `backend/app/services/dashboard_service.py` — dashboard overview + analytics aggregations

### Backend — API & Application
- `backend/app/api/v1/` — versioned FastAPI routes for customer/payment ingestion, recovery cases and simulation, policy validation/simulation, agent runs, negotiation/payment plans, Razorpay links/webhooks, experiments, dashboard metrics, and audit trails
- `POST /api/v1/payments` — idempotent payment ingestion keyed by Razorpay payment ID or merchant order ID, with merchant/customer ownership validation
- `backend/app/main.py` — FastAPI lifespan, schema bootstrap, CORS, request IDs, health endpoint, and conservative per-client rate limiting
- `backend/app/seed.py` — idempotent demo seed: merchant, 50 customers, 100 payments, recovery cases, predictions, decisions, outcomes, agent activity, and an experiment
- `backend/Dockerfile` and `backend/requirements.txt` — backend container and locked runtime/test dependency manifest
- `backend/alembic/` — initial schema migration covering all ORM models

### Frontend — Next.js + TypeScript
- `frontend/` — runnable Next.js project configuration and Dockerfile
- `/` — revenue-at-risk overview and active recovery value
- `/cases`, `/cases/[id]` — case queue, counterfactual predictions, explanation, and negotiation surface
- `/policies`, `/simulate` — merchant guardrails and policy impact simulator
- `/experiments`, `/audit/[case_id]` — lift measurement and immutable decision timeline
- `frontend/src/styles/globals.css` — Co-Star-inspired black/white editorial design system

### ML & Quality
- Four trained LightGBM/T-learner artifacts are present in `backend/models/`: propensity, intervention, uplift, and fatigue. `/health` reported `ml_mode: "trained"` with all model versions loaded on 2026-09-04.
- `model_metrics.json` documents semi-synthetic buildathon validation only; it is not production merchant performance.
- `metis_final_ml_architecture/` was reviewed on 2026-09-05. Its model artifacts are checksum-identical to `backend/models/`; they were not duplicated or overwritten.
- Active `backend/app/ml/registry.py` now supports the final architecture's 12-feature contract, negative uplift, and future EconML `CausalForestDML.effect()` artifacts, with the current T-learner as a compatible fallback.
- `backend/app/services/prediction_service.py` now uses the dedicated uplift estimate to keep counterfactual probabilities and expected net value coherent.
- `GET /api/v1/recovery/cases/{case_id}/explanation` provides best-effort, non-blocking SHAP explanations when SHAP is installed.
- `GET /api/v1/metrics` exposes Prometheus metrics; request timing/count instrumentation is included. `backend/requirements-ml-training.txt` holds optional heavyweight causal retraining dependencies.
- `backend/tests/` now includes causal uplift/feature-contract coverage. Verified on 2026-09-05: **9 tests passed**. Frontend production build also passed.

---

## Remaining External Inputs

- Run `docker compose up -d --build` after the latest ML-observability change so the Docker image installs `prometheus-client` and activates `/api/v1/metrics`. The previous rebuild was still downloading dependencies when the session ended.
- Future causal retraining requires `pip install -r backend/requirements-ml-training.txt`, then run `metis_final_ml_architecture/ml_training/train_metis_models_causal.py`. Its supplied CSV is semi-synthetic buildathon data, not Razorpay production data.
- Razorpay and Groq credentials must be added to `.env` to use live payment links, verified webhooks, and live AI negotiation. The demo remains usable without them.
- Persistent public deployment/Tunnel setup still requires the account owner's Cloudflare/hosting credentials and domain decision.

### METIS Naming & Webhook Setup
- Project-facing names, Docker container/database defaults, API metadata, seed data, frontend wordmark, notebooks, and documentation now use `METIS` rather than the prior project name.
- Razorpay webhook route: `POST /api/v1/webhooks/razorpay` on FastAPI port `8000`.
- Webhook verification uses `RAZORPAY_WEBHOOK_SECRET` and HMAC-SHA256; the secret is never logged or committed.
- Idempotency uses Razorpay's `X-Razorpay-Event-Id` header when provided, with a SHA-256 payload hash fallback.
- Cloudflare Quick Tunnel is active for the current local session: `https://destinations-stop-drink-boring.trycloudflare.com/api/v1/webhooks/razorpay`.
- Configure Razorpay Test Mode webhook events: `payment.captured` and `order.paid`. The shared secret must match `RAZORPAY_WEBHOOK_SECRET` in `.env`.
- Verified end-to-end through the tunnel on 2026-09-04: signed event accepted, a seeded payment moved to `CAPTURED`, and the duplicate event returned `idempotent: true` without repeating the financial update.
- Verified with Razorpay Test Mode on 2026-09-04: `payment.captured` and `order.paid` were signature-verified, persisted, and marked processed. Their Razorpay payment ID was not present in METIS's local payment data, so no recovery case was changed; live recovery updates require payment/order ingestion before the provider event arrives.
- Webhook matching now checks Razorpay payment ID and order ID. On order-ID match, the captured Razorpay payment ID is recorded locally; repeated `payment.captured`/`order.paid` events do not create duplicate recovery outcomes.
- Verified on 2026-09-04 through the live Cloudflare Tunnel: ingested payment → recovery case → `payment.captured` → `CAPTURED` payment + `RECOVERED` case; subsequent `order.paid` left recovery outcomes at one record.
- Restart local webhook setup: run `docker compose up -d postgres backend`, then `cloudflared tunnel --url http://127.0.0.1:8000 --no-autoupdate`. A Quick Tunnel URL changes on each restart, so update the Razorpay webhook URL each time.
- Local PostgreSQL is published as `localhost:15432` because ports `5432` and `5433` are occupied by unrelated services. Docker-internal connections remain `postgres:5432`.
- The original credential-bound local PostgreSQL volume was preserved. METIS now uses the fresh `metis_metis_postgres_data_v2` development volume, initialized with the `metis` database identity.
- Verified on 2026-09-04: `GET http://localhost:8000/health` returns `200` with `{"ok": true, "service": "metis"}`.

---

## Key Decisions Recorded

| Decision | Choice |
|---|---|
| AI Agent LLM | Groq API — `llama-3.3-70b-versatile` (no GPU needed) |
| ML models | Trained LightGBM/T-learner artifacts active; causal-EconML artifacts supported for a future retrain |
| Infrastructure | Docker Compose (postgres + redis + backend + frontend + mlflow) |
| Razorpay | Real test credentials — user adds to `.env` |
| Seed data | Yes — rich synthetic demo data |
| Frontend design | Co-Star style — pure black/white, no shadows/gradients, pill CTAs |
| DB | PostgreSQL async (asyncpg) + Redis |
| ORM | SQLAlchemy async + Alembic migrations |
