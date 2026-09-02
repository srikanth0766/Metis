# METIS — AGENTS.md

## Purpose

This file defines how AI coding agents must work on METIS.

METIS's product specification, requirements, features, user stories, architecture, database design, API design, and technology choices are documented separately.

Before doing any work, agents must read the main project specification and use it as the source of truth for what METIS is.

This file defines **how the agent should work**, not what the product should contain.

---

## 1. Start by Understanding the Repository

Before writing or modifying code:

1. Read the project specification.
2. Read `AGENTS.md`.
3. Read `PROGRESS.md` if it exists.
4. Inspect the repository structure.
5. Identify the existing implementation related to the requested task.
6. Read the relevant files before modifying them.
7. Check existing tests and documentation.

Do not start coding immediately after seeing the task.

Understand the existing implementation first.

---

## 2. Never Assume Something Is Missing

Before implementing a feature:

- Search the repository.
- Check existing services.
- Check existing utilities.
- Check existing database models.
- Check existing API endpoints.
- Check existing tests.

Reuse existing functionality when appropriate.

Do not create duplicate implementations.

---

## 3. Follow the Existing Project Design

The separate project specification is the source of truth.

Do not independently redesign:

- Architecture
- Database
- APIs
- ML pipeline
- Agent workflow
- Product behavior
- Technology stack

If a change to the existing design is genuinely necessary:

1. Identify why.
2. Evaluate the impact.
3. Make the smallest required change.
4. Document the decision in `PROGRESS.md`.

Never silently change finalized design decisions.

---

## 4. Production-Quality Mindset

METIS is intended to be production-level fintech software.

Write code that is:

- Correct
- Precise
- Secure
- Maintainable
- Testable
- Observable
- Robust
- Easy to understand

Do not write hackathon-style throwaway code.

Avoid:

- Quick hacks
- Excessive abstraction
- Duplicate logic
- Dead code
- Hard-coded business logic
- Unnecessary dependencies
- Unnecessary services
- Unnecessary files
- Debug code left in production paths

---

## 5. Keep Implementations Simple

Use the simplest architecture that correctly solves the problem.

Do not add technology because it sounds impressive.

For example, do not introduce:

- Kafka when Redis is sufficient
- Kubernetes when Docker is sufficient
- Multiple databases when PostgreSQL is sufficient
- Multiple agent frameworks when Python orchestration is sufficient
- Deep learning when a strong tree-based model is sufficient

Complexity must have a measurable purpose.

---

## 6. Code Before Comments

Prefer clear code over excessive comments.

Comments should explain:

- Why something unusual is necessary
- Important business constraints
- Non-obvious technical decisions
- Safety-critical behavior

Do not write comments that merely repeat what the code already says.

---

## 7. Type Everything Important

Use strong typing wherever practical.

Backend code should use:

- Python type hints
- Pydantic models
- Explicit return types
- Typed tool schemas

Frontend code should use:

- TypeScript types/interfaces
- Explicit API response types

Avoid unnecessary `Any`.

---

## 8. Error Handling

Never silently ignore failures.

Handle:

- Invalid input
- Missing resources
- Database errors
- External API failures
- Webhook failures
- Timeouts
- Rate limits
- Model failures
- Agent failures
- Tool failures
- Unexpected responses

Errors must be:

- Explicit
- Logged appropriately
- Safe for users
- Useful for developers

Do not expose:

- Stack traces
- API keys
- Internal secrets
- Sensitive customer information

to end users.

Do not use broad exception handling unless there is a clear reason.

---

## 9. Financial Operations Are High Risk

Any operation involving money must be treated as safety-critical.

The execution flow should remain:

```text
Agent request
    ↓
Schema validation
    ↓
Business validation
    ↓
Merchant policy validation
    ↓
Case/state validation
    ↓
Idempotency check
    ↓
Financial action
    ↓
Result verification
    ↓
Audit record

if you have to implement any ml or dl model, i would like to train it in kaggle and save the model file here you have to use it. so make sure u dont run anything related to model without teling me cuz itd take soo much time to run.

if you have to install anything make sure u install it in the .env file.

this is a buildathon project so make sure that we can show the demo as well.