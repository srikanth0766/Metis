import Link from "next/link";
import { Nav } from "../../components/nav";
import { getSystemHealth } from "../../lib/api";

export default async function AboutPage() {
  const health = await getSystemHealth();

  return (
    <>
      <Nav />
      <main>
        <p className="eyebrow">Project & Architecture</p>
        <h1>Intelligence, not noise.</h1>
        <p className="lede">
          <em>Razorpay recovers failed revenue.</em> METIS determines where recovery effort will actually create <em>incremental revenue</em>.
        </p>

        {/* System Health / Real Model Status */}
        <div className="card-sharp" style={{ marginBottom: "60px", display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "16px" }}>
          <div>
            <span style={{ fontSize: "10px", letterSpacing: "0.14em", textTransform: "uppercase", color: "var(--muted)", display: "block", marginBottom: "4px" }}>
              Active Causal Pipeline
            </span>
            <strong style={{ fontSize: "16px", fontFamily: "monospace" }}>
              {health?.service.toUpperCase()} · ML MODE: {health?.ml_mode.toUpperCase()}
            </strong>
          </div>
          <div style={{ display: "flex", gap: "16px", fontSize: "11px", fontFamily: "monospace", color: "var(--muted)" }}>
            <span>Propensity: {health?.models?.propensity ?? "Active"}</span>
            <span>Uplift: {health?.models?.uplift ?? "T-Learner"}</span>
            <span>Fatigue: {health?.models?.fatigue ?? "Multiclass"}</span>
          </div>
        </div>

        {/* Section 1: The Problem */}
        <section className="step-section" style={{ borderTop: "none", paddingTop: 0, marginTop: 0 }}>
          <p className="eyebrow">01 · The Problem</p>
          <h2>The illusion of recovery attribution.</h2>
          <p className="lede">
            When a transaction fails, conventional gateways trigger automatic retries, automated reminders, and payment links across every customer.
            Merchants celebrate recovered payments—ignoring a critical truth: <strong>a large portion of these customers would have paid on their own without any intervention</strong>.
          </p>
          <div className="card-sharp" style={{ background: "#050505", marginBottom: "30px" }}>
            <p style={{ margin: 0, fontSize: "14px", lineHeight: "1.7", color: "var(--muted)" }}>
              Contacting customers who have a 90% natural recovery propensity generates zero incremental revenue while incurring gateway fees, concession costs, and severe contact fatigue. Conversely, aggressively nudging high-fatigue customers drives churn. METIS replaces indiscriminate recovery spam with mathematically sound counterfactual intelligence.
            </p>
          </div>
        </section>

        {/* Section 2: Counterfactual Uplift & Economics */}
        <section className="step-section">
          <p className="eyebrow">02 · Mathematical Formulation</p>
          <h2>Causal uplift vs. predictive propensity.</h2>
          <p className="lede">
            Predicting whether someone will pay is useless if they were going to pay anyway. METIS measures the <em>treatment effect</em>:
          </p>

          <div style={{ border: "1px solid var(--line)", padding: "28px", background: "#080808", fontFamily: "monospace", fontSize: "14px", lineHeight: "1.8", marginBottom: "30px" }}>
            <div style={{ color: "var(--muted)", marginBottom: "8px" }}>// Causal Uplift (Individual Treatment Effect)</div>
            <div style={{ color: "var(--white)", fontSize: "16px", fontWeight: "bold" }}>
              Uplift(action) = P(pay | do(action)) - P(pay | do(control))
            </div>
            <div style={{ color: "var(--dim)", fontSize: "12px", marginTop: "4px" }}>
              Where P(pay | do(control)) = Natural Recovery Propensity
            </div>

            <div style={{ margin: "20px 0 8px", borderTop: "1px solid var(--line)", paddingTop: "16px", color: "var(--muted)" }}>
              // Expected Incremental Net Value
            </div>
            <div style={{ color: "var(--white)", fontSize: "16px", fontWeight: "bold" }}>
              E[Net Value] = (Uplift × Recoverable Amount) - Cost(intervention) - Cost(concession) - Cost(fatigue)
            </div>
            <div style={{ color: "var(--dim)", fontSize: "12px", marginTop: "4px" }}>
              If E[Net Value] ≤ 0 for all actions, METIS executes: DO NOTHING
            </div>
          </div>

          <div className="metric-readout">
            <div className="metric-item">
              <span>Propensity Model</span>
              <strong>LightGBM</strong>
              <small>Calibrated P(natural payment)</small>
            </div>
            <div className="metric-item">
              <span>Uplift Engine</span>
              <strong>T-Learner</strong>
              <small>Heterogeneous Treatment Effect</small>
            </div>
            <div className="metric-item">
              <span>Fatigue Model</span>
              <strong>Multiclass</strong>
              <small>Dynamic penalty for repeated contacts</small>
            </div>
            <div className="metric-item">
              <span>Optimizer</span>
              <strong>Constrained</strong>
              <small>Expected incremental value maximization</small>
            </div>
          </div>
        </section>

        {/* Section 3: The 6 Actions */}
        <section className="step-section">
          <p className="eyebrow">03 · Action Taxonomy</p>
          <h2>Six distinct recovery pathways.</h2>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))", gap: "16px", marginTop: "24px" }}>
            <div className="card-sharp">
              <span style={{ fontSize: "11px", letterSpacing: "0.12em", textTransform: "uppercase", color: "var(--muted)" }}>01</span>
              <h3 style={{ margin: "8px 0 8px" }}>DO NOTHING</h3>
              <p style={{ margin: 0, fontSize: "13px", color: "var(--muted)", lineHeight: "1.6" }}>
                Selected when natural recovery probability is high, or when intervention costs exceed expected lift. Prevents customer annoyance and unnecessary merchant costs.
              </p>
            </div>
            <div className="card-sharp">
              <span style={{ fontSize: "11px", letterSpacing: "0.12em", textTransform: "uppercase", color: "var(--muted)" }}>02</span>
              <h3 style={{ margin: "8px 0 8px" }}>RETRY</h3>
              <p style={{ margin: 0, fontSize: "13px", color: "var(--muted)", lineHeight: "1.6" }}>
                Autonomous background payment retry through Razorpay. Optimal for transient bank declines, network glitches, or temporary technical errors.
              </p>
            </div>
            <div className="card-sharp">
              <span style={{ fontSize: "11px", letterSpacing: "0.12em", textTransform: "uppercase", color: "var(--muted)" }}>03</span>
              <h3 style={{ margin: "8px 0 8px" }}>REMINDER</h3>
              <p style={{ margin: 0, fontSize: "13px", color: "var(--muted)", lineHeight: "1.6" }}>
                Low-friction WhatsApp/SMS notification. Effective for forgotten payments or expired cards without discounting or intrusive outreach.
              </p>
            </div>
            <div className="card-sharp">
              <span style={{ fontSize: "11px", letterSpacing: "0.12em", textTransform: "uppercase", color: "var(--muted)" }}>04</span>
              <h3 style={{ margin: "8px 0 8px" }}>PAYMENT LINK</h3>
              <p style={{ margin: 0, fontSize: "13px", color: "var(--muted)", lineHeight: "1.6" }}>
                Instant Razorpay checkout link with dynamic expiration. Allows the customer to complete payment using alternative UPI apps or credit cards.
              </p>
            </div>
            <div className="card-sharp">
              <span style={{ fontSize: "11px", letterSpacing: "0.12em", textTransform: "uppercase", color: "var(--muted)" }}>05</span>
              <h3 style={{ margin: "8px 0 8px" }}>PAYMENT PLAN</h3>
              <p style={{ margin: 0, fontSize: "13px", color: "var(--muted)", lineHeight: "1.6" }}>
                Structured multi-installment agreement (2–12 installments) calculated strictly within policy limits for large ticket sizes and insufficient funds.
              </p>
            </div>
            <div className="card-sharp">
              <span style={{ fontSize: "11px", letterSpacing: "0.12em", textTransform: "uppercase", color: "var(--muted)" }}>06</span>
              <h3 style={{ margin: "8px 0 8px" }}>NEGOTIATION</h3>
              <p style={{ margin: 0, fontSize: "13px", color: "var(--muted)", lineHeight: "1.6" }}>
                Autonomous LLM agent dialogue offering structured concessions, conditional waivers, or flexible terms strictly constrained by merchant policy.
              </p>
            </div>
          </div>
        </section>

        {/* Section 4: Policy Engine & Agent */}
        <section className="step-section">
          <p className="eyebrow">04 · Policy Engine & Autonomous Agent</p>
          <h2>Bounded autonomy. Zero hallucination.</h2>
          <p className="lede">
            In financial systems, LLMs cannot be given unbounded discretion. METIS strictly separates <strong>financial optimization</strong> from <strong>conversational execution</strong>.
          </p>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "24px" }}>
            <div className="card-sharp">
              <span style={{ fontSize: "10px", letterSpacing: "0.12em", textTransform: "uppercase", color: "var(--muted)", display: "block", marginBottom: "8px" }}>
                Deterministic Policy Engine
              </span>
              <p style={{ fontSize: "13px", color: "var(--muted)", lineHeight: "1.6", margin: 0 }}>
                Every action proposed by the agent or optimizer is validated against the merchant’s policy limits before execution: discount percentages, maximum contact attempts, minimum payment thresholds, and installment durations are checked in Python code, not prompts.
              </p>
            </div>
            <div className="card-sharp">
              <span style={{ fontSize: "10px", letterSpacing: "0.12em", textTransform: "uppercase", color: "var(--muted)", display: "block", marginBottom: "8px" }}>
                Grounded Tool Execution
              </span>
              <p style={{ fontSize: "13px", color: "var(--muted)", lineHeight: "1.6", margin: 0 }}>
                The Groq-backed AI Agent (Llama / GPT OSS) executes using 9 typed tools: <code>get_customer_context</code>, <code>get_payment_context</code>, <code>get_merchant_policy</code>, <code>get_recovery_options</code>, <code>calculate_recovery_value</code>, <code>create_payment_link</code>, <code>create_payment_plan</code>, and <code>escalate_to_human</code>.
              </p>
            </div>
          </div>
        </section>

        {/* Section 5: Razorpay & Webhooks */}
        <section className="step-section">
          <p className="eyebrow">05 · Razorpay & Event-Driven Webhooks</p>
          <h2>Native payment infrastructure.</h2>
          <p className="lede">
            METIS does not replace Razorpay; it augments it. Failures trigger webhook ingestion; recovery actions generate live Razorpay payment links; customer payments dispatch cryptographically verified webhooks that immediately reconcile cases in the audit ledger.
          </p>
          <div className="card-sharp" style={{ fontFamily: "monospace", fontSize: "12px", lineHeight: "1.8", color: "var(--muted)" }}>
            <div>[Razorpay Webhook: payment.failed] → Case Opened in METIS</div>
            <div>[METIS Causal Inference] → P(natural) vs Counterfactuals calculated</div>
            <div>[Policy Engine] → Guardrails verified for merchant</div>
            <div>[AI Agent / Tool] → Payment link / plan generated</div>
            <div>[Razorpay Webhook: payment.captured] → HMAC Signature verified → Case RECOVERED</div>
          </div>
        </section>

        {/* CTAs */}
        <div style={{ marginTop: "60px", paddingTop: "40px", borderTop: "1px solid var(--line)", display: "flex", gap: "20px", alignItems: "center" }}>
          <Link className="action" href="/">
            LAUNCH INTERACTIVE DEMO →
          </Link>
        </div>
      </main>
    </>
  );
}
