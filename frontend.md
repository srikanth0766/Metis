Yes. You’re right. I kept turning a frontend design document into a full product specification.

The file should stay focused on two things: the visual design system and the concise frontend behavior. For your agent, this is enough:

```markdown
# Frontend Design Guide — METIS

Follow this document for the visual design of the METIS frontend.

## Design Philosophy

- Stark, high-contrast, monochrome-first.
- Almost entirely black and white.
- Minimal, confident, editorial; closer to a poster/zine than a typical SaaS dashboard.
- Typography-led, not decoration-led.
- Generous negative space.
- No gradients, shadows, glassmorphism, skeuomorphism.
- Hairline borders instead of shadows.
- Black/white sections may alternate.
- Primary CTAs: pill-shaped.
- Secondary elements/cards: sharp corners.
- No generic 4–12px rounded corners.
- Thin monochrome line icons only.
- No colorful success/error UI.
- Fast, subtle motion: fades and small position shifts.
- Do not implement the animated Co-Star star-grid.

## Colors

- Background: `#000000` / `#0A0A0A`
- Primary text: `#FFFFFF` / `#F5F5F5`
- Secondary text: `#A3A3A3`
- Disabled text: `#5C5C5C`
- Dividers: `#2A2A2A` on black, `#E5E5E5` on white
- One muted accent only when necessary.

## Typography

- Display: bold condensed sans-serif or high-contrast serif.
- Body/UI: Inter / Helvetica Neue / system sans-serif.
- Large, tight headlines.
- All-caps labels may use increased letter spacing.
- Important numerical readouts may use monospace.
- Use regular + bold weights only.

## Shape & Motion

- Pills for primary buttons.
- Sharp corners for cards/secondary elements.
- 1px borders.
- No shadows.
- 200–350ms transitions.
- No bouncy animation or heavy parallax.

# METIS Frontend

Exactly 2 pages:

`/` — interactive demo  
`/about` — project + architecture explanation

## Main Demo

The main page should be one continuous recovery story:

Merchant
→ Customer
→ Simulate Payment Failure
→ Razorpay/Webhook
→ Customer Context
→ Natural Recovery
→ Counterfactuals
→ Incremental Uplift
→ Incremental Revenue
→ Best Action / DO NOTHING
→ Policy Check
→ AI Agent
→ Razorpay
→ Payment Outcome
→ Audit / Experiment

Use the existing backend APIs and real results. Do not duplicate backend logic or hardcode ML predictions, uplift, recommendations, or revenue.

Use `recovery_events.csv` to create realistic demo merchants/customers with existing payment histories.

Different customers must produce different decisions, including:
- DO NOTHING
- RETRY
- REMINDER
- PAYMENT LINK
- PAYMENT PLAN
- NEGOTIATION

## Counterfactual Hero

This is the main focus of the demo.

Show:

`DO NOTHING | RETRY | REMINDER | PAYMENT LINK | PAYMENT PLAN | NEGOTIATION`

For each show:
- recovery probability
- uplift vs natural recovery
- expected incremental ₹
- net value where available

Also show:

`Natural recovery = probability of paying without intervention`

Then clearly show why METIS selected the action.

DO NOTHING must be a genuine possible outcome.

Example:

Natural recovery: 91%  
Best intervention: 92%  
Incremental value: ₹120  
Decision: DO NOTHING

## Decision Explanation

Show:
- natural recovery
- selected-action recovery
- uplift
- expected incremental revenue
- expected net value
- confidence
- SHAP explanation where available
- key decision factors

## Policy + Agent

Show policy validation before execution.

Then show the AI agent's actual tool actions.

The agent executes the selected action; it does not decide the financial strategy or bypass policy.

## Razorpay

Initial failure can be simulated.

Use the existing Razorpay integration for recovery actions.

Provide a reliable simulated customer payment flow.

After payment, show the webhook/outcome returning to METIS.

## Final Result

Do NOT use a generic “With METIS / Without METIS” comparison.

Show the actual economics:

- payment amount
- natural recovery probability
- expected natural recovery ₹
- selected action
- intervention recovery probability
- uplift
- expected incremental revenue
- intervention/concession cost
- expected net value
- actual recovered amount
- actual incremental impact where available

Then show the audit timeline:

`Failure → Prediction → Counterfactuals → Decision → Policy → Agent → Razorpay → Outcome`

## About Page

Explain briefly:
- METIS problem
- Razorpay recovery vs METIS
- counterfactual intelligence
- uplift
- incremental net revenue
- policy engine
- AI agent
- Razorpay/webhooks
- experiments
- audit
- ML/causal architecture

Use the actual architecture already implemented.

## Important

Read the SRS, AGENTS.md, PROGRESS.md, existing frontend, backend APIs, and this document before coding.

Keep the existing visual language.

Do not create unnecessary pages.

The demo should make one idea immediately obvious:

“Razorpay recovers failed revenue. METIS determines where recovery effort will actually create incremental revenue.”
```

