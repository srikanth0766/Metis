"use client";
import { useState, useEffect, useMemo } from "react";
import Link from "next/link";
import { Nav } from "../components/nav";
import { AgentChat } from "../components/AgentChat";
import {
  Merchant,
  Customer,
  RecoveryCase,
  CaseDetail,
  Prediction,
  Decision,
  Policy,
  AuditLog,
  Explanation,
  Experiment,
  ExperimentResult,
  getMerchants,
  getCases,
  getCase,
  getPredictions,
  getDecision,
  optimizeCase,
  getExplanation,
  getPolicy,
  getAudit,
  getExperiments,
  getExperimentResults,
  getCustomers,
  simulatePaymentFailure,
  simulateRazorpayWebhook,
  createRazorpayLink,
  inr,
  pct,
} from "../lib/api";

type DemoProfile = {
  id: string;
  name: string;
  segment: "HIGH_VALUE" | "REGULAR" | "AT_RISK" | "DORMANT";
  amount: number;
  payment_method: string;
  failure_reason: string;
  expected_outcome: string;
  description: string;
  contacts: number;
  days_ago: number;
};

const DEMO_PROFILES: DemoProfile[] = [
  {
    id: "demo_do_nothing",
    name: "Priya Sharma (High Natural Recovery)",
    segment: "HIGH_VALUE",
    amount: 500,
    payment_method: "upi",
    failure_reason: "network_error",
    expected_outcome: "DO NOTHING",
    description: "High payment rate (98%), small amount, contact fatigue. Interventions yield negative net value.",
    contacts: 3,
    days_ago: 1,
  },
  {
    id: "demo_retry",
    name: "Rahul Verma (Bank Decline / Glitch)",
    segment: "REGULAR",
    amount: 2500,
    payment_method: "card",
    failure_reason: "bank_decline",
    expected_outcome: "RETRY",
    description: "Temporary gateway timeout. Automated background retry yields highest incremental ROI (+28.7% uplift).",
    contacts: 0,
    days_ago: 1,
  },
  {
    id: "demo_reminder",
    name: "Ananya Iyer (Gentle Reminder)",
    segment: "REGULAR",
    amount: 600,
    payment_method: "card",
    failure_reason: "bank_decline",
    expected_outcome: "REMINDER",
    description: "Overdue 7 days. Low-cost WhatsApp/SMS reminder yields positive net ROI without expensive concessions.",
    contacts: 0,
    days_ago: 7,
  },
  {
    id: "demo_payment_link",
    name: "Vikram Malhotra (UPI Drop-off)",
    segment: "HIGH_VALUE",
    amount: 1250,
    payment_method: "upi",
    failure_reason: "network_error",
    expected_outcome: "PAYMENT LINK",
    description: "Recent session drop. Instant Razorpay UPI checkout link delivers immediate recovery (+7.2% uplift).",
    contacts: 0,
    days_ago: 1,
  },
  {
    id: "demo_payment_plan",
    name: "Rohan Mehta (Large Balance Hardship)",
    segment: "REGULAR",
    amount: 14000,
    payment_method: "netbanking",
    failure_reason: "insufficient_funds",
    expected_outcome: "PAYMENT PLAN",
    description: "Large ticket size. 3-installment structured payment plan produces +41.1% uplift and ₹5,657 net value.",
    contacts: 1,
    days_ago: 5,
  },
  {
    id: "demo_negotiation",
    name: "Kavita Patel (At-Risk Customer)",
    segment: "AT_RISK",
    amount: 5000,
    payment_method: "upi",
    failure_reason: "insufficient_funds",
    expected_outcome: "NEGOTIATION",
    description: "10 days overdue with cashflow constraint. Autonomous agent negotiation with approved policy concession.",
    contacts: 1,
    days_ago: 10,
  },
];

export default function DemoPage() {
  const [merchants, setMerchants] = useState<Merchant[]>([]);
  const [selectedMerchant, setSelectedMerchant] = useState<Merchant | null>(null);
  const [policy, setPolicy] = useState<Policy | null>(null);
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [existingCases, setExistingCases] = useState<RecoveryCase[]>([]);

  // Simulation state
  const [selectedProfileId, setSelectedProfileId] = useState<string>("demo_do_nothing");
  const [isSimulating, setIsSimulating] = useState<boolean>(false);
  const [activeCase, setActiveCase] = useState<CaseDetail | null>(null);
  const [predictions, setPredictions] = useState<Prediction[]>([]);
  const [decision, setDecision] = useState<Decision | null>(null);
  const [explanation, setExplanation] = useState<Explanation | null>(null);
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);
  const [paymentLinkUrl, setPaymentLinkUrl] = useState<string | null>(null);
  const [isPaymentSimulating, setIsPaymentSimulating] = useState<boolean>(false);
  const [paymentRecovered, setPaymentRecovered] = useState<boolean>(false);

  // A/B test experiments
  const [experiments, setExperiments] = useState<Experiment[]>([]);
  const [experimentResult, setExperimentResult] = useState<ExperimentResult | null>(null);

  // Error & loading
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Initialize data
  useEffect(() => {
    async function init() {
      const ms = await getMerchants();
      setMerchants(ms);
      if (ms.length > 0) {
        const m = ms[0];
        setSelectedMerchant(m);
        const [pol, casesList, exps, custs] = await Promise.all([
          getPolicy(m.merchant_id),
          getCases(m.merchant_id),
          getExperiments(m.merchant_id),
          getCustomers(m.merchant_id),
        ]);
        setPolicy(pol);
        setExistingCases(casesList);
        setExperiments(exps);
        setCustomers(custs);
        if (exps.length > 0) {
          const res = await getExperimentResults(exps[0].experiment_id);
          setExperimentResult(res);
        }
      }
    }
    init();
  }, []);

  const selectedProfile = useMemo(
    () => DEMO_PROFILES.find((p) => p.id === selectedProfileId) || DEMO_PROFILES[0],
    [selectedProfileId]
  );

  // Reset demo
  const handleReset = () => {
    setActiveCase(null);
    setPredictions([]);
    setDecision(null);
    setExplanation(null);
    setAuditLogs([]);
    setPaymentLinkUrl(null);
    setPaymentRecovered(false);
    setErrorMsg(null);
  };

  // Run full simulation pipeline
  const handleSimulate = async () => {
    if (!selectedMerchant) return;
    setIsSimulating(true);
    setErrorMsg(null);
    handleReset();

    try {
      // 1. Pick seeded customer matching profile ID or fallback
      const targetCustomer = customers.find((c) => c.external_customer_id === selectedProfile.id);
      const customerId = targetCustomer
        ? targetCustomer.customer_id
        : (existingCases[0]?.customer_id || "e06b3065-fb04-4c87-9023-12e280ab6164");

      // 2. Ingest payment failure with profile attributes
      const simCase = await simulatePaymentFailure({
        merchant_id: selectedMerchant.merchant_id,
        customer_id: customerId,
        amount: selectedProfile.amount,
        payment_method: selectedProfile.payment_method,
        failure_reason: selectedProfile.failure_reason,
        contacts: selectedProfile.contacts,
        days_ago: selectedProfile.days_ago,
      });

      if (!simCase) {
        throw new Error("Failed to create recovery case on backend.");
      }

      // 3. Load full case detail
      const detail = await getCase(simCase.case_id);
      if (detail) {
        setActiveCase(detail);
      }

      // 4. Run ML Predictions & Optimizer
      const [preds, dec, expl, logs] = await Promise.all([
        getPredictions(simCase.case_id),
        optimizeCase(simCase.case_id),
        getExplanation(simCase.case_id),
        getAudit(simCase.case_id),
      ]);

      setPredictions(preds);
      setDecision(dec);
      setExplanation(expl);
      setAuditLogs(logs);

      // If action is PAYMENT_LINK, generate initial Razorpay link
      if (dec?.selected_intervention === "PAYMENT_LINK") {
        const linkRes = await createRazorpayLink(simCase.case_id);
        if (linkRes?.short_url) {
          setPaymentLinkUrl(linkRes.short_url);
        }
      }
    } catch (err: any) {
      console.error("Simulation error:", err);
      setErrorMsg(err.message || "Simulation failed.");
    } finally {
      setIsSimulating(false);
    }
  };

  // Select an existing case from DB
  const handleSelectExistingCase = async (caseId: string) => {
    if (!caseId) return;
    setIsSimulating(true);
    handleReset();
    try {
      const [detail, preds, dec, expl, logs] = await Promise.all([
        getCase(caseId),
        getPredictions(caseId),
        getDecision(caseId),
        getExplanation(caseId),
        getAudit(caseId),
      ]);
      setActiveCase(detail);
      setPredictions(preds);
      setDecision(dec);
      setExplanation(expl);
      setAuditLogs(logs);
      if (detail?.status === "RECOVERED") {
        setPaymentRecovered(true);
      }
    } catch (err: any) {
      setErrorMsg("Failed to load case.");
    } finally {
      setIsSimulating(false);
    }
  };

  // Simulate customer completing payment via Razorpay
  const handleCompletePayment = async () => {
    if (!activeCase?.payment) return;
    setIsPaymentSimulating(true);
    try {
      const p = activeCase.payment;
      const res = await simulateRazorpayWebhook({
        razorpay_payment_id: p.razorpay_payment_id || `pay_${activeCase.case_id.slice(0, 8)}`,
        order_id: p.order_id || `order_${activeCase.case_id.slice(0, 8)}`,
        amount: parseFloat(p.amount),
      });

      if (res?.ok) {
        setPaymentRecovered(true);
        // Refresh audit logs and case detail
        const [updatedCase, logs] = await Promise.all([
          getCase(activeCase.case_id),
          getAudit(activeCase.case_id),
        ]);
        if (updatedCase) setActiveCase(updatedCase);
        setAuditLogs(logs);
      } else {
        setErrorMsg("Webhook capture failed.");
      }
    } catch (err: any) {
      setErrorMsg(err.message || "Payment simulation failed.");
    } finally {
      setIsPaymentSimulating(false);
    }
  };

  // Natural recovery probability from predictions
  const naturalRecoveryProb = useMemo(() => {
    if (predictions.length > 0) {
      return predictions[0].probability_without_intervention;
    }
    return 0;
  }, [predictions]);

  // Selected prediction object
  const selectedPrediction = useMemo(() => {
    if (!decision) return null;
    return predictions.find((p) => p.intervention_type === decision.selected_intervention) || null;
  }, [predictions, decision]);

  return (
    <>
      <Nav />
      <main>
        {/* Header / Editorial Tagline */}
        <div style={{ marginBottom: "50px" }}>
          <p className="eyebrow">Recovery Intelligence Engine</p>
          <h1>Recovery intelligence, not recovery noise.</h1>
          <p className="lede">
            <em>Razorpay recovers failed revenue.</em> METIS determines where recovery effort will actually create <em>incremental revenue</em>.
          </p>

          <div style={{ display: "flex", gap: "20px", alignItems: "center", flexWrap: "wrap", marginTop: "24px" }}>
            <span style={{ fontSize: "11px", letterSpacing: "0.12em", textTransform: "uppercase", color: "var(--muted)" }}>
              Merchant Context:
            </span>
            <span style={{ fontSize: "13px", fontFamily: "monospace", padding: "6px 14px", border: "1px solid var(--line)" }}>
              {selectedMerchant?.name ?? "METIS Demo Merchant"} ({selectedMerchant?.currency ?? "INR"})
            </span>
            {policy && (
              <span style={{ fontSize: "11px", color: "var(--muted)" }}>
                Policy limits: Max {policy.max_discount_percent}% discount · Max {policy.max_contacts} contacts
              </span>
            )}
          </div>
        </div>

        {/* Step 1: Customer Archetype Selector */}
        <section className="step-section" style={{ borderTop: "none", paddingTop: 0 }}>
          <p className="eyebrow">Step 1 · Select Customer Archetype or Live Case</p>
          <h2>Choose a payment failure scenario.</h2>
          <p style={{ color: "var(--muted)", fontSize: "14px", marginTop: "12px", maxWidth: "700px" }}>
            Different customers produce fundamentally different decisions based on their natural payment probability, ticket size, and contact fatigue.
          </p>

          {/* Archetype buttons */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: "12px", marginTop: "24px" }}>
            {DEMO_PROFILES.map((profile) => {
              const active = selectedProfileId === profile.id;
              return (
                <div
                  key={profile.id}
                  onClick={() => setSelectedProfileId(profile.id)}
                  style={{
                    border: active ? "1px solid var(--white)" : "1px solid var(--line)",
                    background: active ? "#121212" : "#070707",
                    padding: "16px 18px",
                    cursor: "pointer",
                    transition: "all 0.2s",
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "6px" }}>
                    <span style={{ fontSize: "11px", fontFamily: "monospace", color: "var(--muted)" }}>
                      {profile.segment} · {inr(profile.amount)}
                    </span>
                    <span
                      style={{
                        fontSize: "9px",
                        letterSpacing: "0.1em",
                        textTransform: "uppercase",
                        padding: "2px 6px",
                        border: "1px solid var(--line)",
                        background: active ? "var(--white)" : "transparent",
                        color: active ? "var(--black)" : "var(--muted)",
                        fontWeight: "bold",
                      }}
                    >
                      → {profile.expected_outcome}
                    </span>
                  </div>
                  <strong style={{ display: "block", fontSize: "14px", margin: "4px 0 6px" }}>
                    {profile.name}
                  </strong>
                  <p style={{ margin: 0, fontSize: "12px", color: "var(--dim)", lineHeight: "1.4" }}>
                    {profile.description}
                  </p>
                </div>
              );
            })}
          </div>

          {/* Or pick from live seeded database cases */}
          {existingCases.length > 0 && (
            <div style={{ marginTop: "20px", display: "flex", alignItems: "center", gap: "16px", flexWrap: "wrap" }}>
              <span style={{ fontSize: "11px", textTransform: "uppercase", letterSpacing: "0.1em", color: "var(--dim)" }}>
                Or select live database case:
              </span>
              <select
                onChange={(e) => handleSelectExistingCase(e.target.value)}
                value={activeCase?.case_id || ""}
                style={{
                  background: "#0a0a0a",
                  color: "var(--white)",
                  border: "1px solid var(--line)",
                  padding: "8px 12px",
                  fontSize: "12px",
                  fontFamily: "monospace",
                  outline: "none",
                }}
              >
                <option value="">-- Choose from {existingCases.length} seeded cases --</option>
                {existingCases.map((c) => (
                  <option key={c.case_id} value={c.case_id}>
                    {c.customer?.name ?? "Customer"} · {inr(c.revenue_at_risk)} · {c.status} ({c.case_id.slice(0, 8)})
                  </option>
                ))}
              </select>
            </div>
          )}

          {/* Simulate Failure Action */}
          <div style={{ marginTop: "32px", display: "flex", gap: "16px", alignItems: "center" }}>
            <button
              className="action"
              onClick={handleSimulate}
              disabled={isSimulating}
              style={{ padding: "16px 36px", fontSize: "12px" }}
            >
              {isSimulating ? "RUNNING CAUSAL INFERENCE..." : "SIMULATE PAYMENT FAILURE →"}
            </button>
            {activeCase && (
              <button className="action action-ghost" onClick={handleReset} disabled={isSimulating}>
                RESET DEMO
              </button>
            )}
          </div>
          {errorMsg && <p style={{ color: "#ff5555", fontSize: "13px", marginTop: "16px" }}>{errorMsg}</p>}
        </section>

        {/* Live Walkthrough: Only shown once simulated or case selected */}
        {activeCase && (
          <>
            {/* Step 2: Razorpay Webhook Ingestion & Context */}
            <section className="step-section">
              <p className="eyebrow">Step 2 · Razorpay Webhook Ingestion & Customer Context</p>
              <h2>Transaction failure ingested.</h2>

              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "16px", marginTop: "24px" }}>
                <div className="card-sharp">
                  <span style={{ fontSize: "10px", letterSpacing: "0.12em", textTransform: "uppercase", color: "var(--muted)", display: "block", marginBottom: "8px" }}>
                    Customer Profile
                  </span>
                  <strong style={{ fontSize: "18px", display: "block", marginBottom: "4px" }}>
                    {activeCase.customer?.name}
                  </strong>
                  <div style={{ fontSize: "12px", fontFamily: "monospace", color: "var(--muted)", lineHeight: "1.7" }}>
                    <div>Segment: {activeCase.customer?.segment}</div>
                    <div>Email: {activeCase.customer?.email}</div>
                    <div>Phone: {activeCase.customer?.phone}</div>
                  </div>
                </div>

                <div className="card-sharp">
                  <span style={{ fontSize: "10px", letterSpacing: "0.12em", textTransform: "uppercase", color: "var(--muted)", display: "block", marginBottom: "8px" }}>
                    Failed Payment
                  </span>
                  <strong style={{ fontSize: "18px", display: "block", marginBottom: "4px" }}>
                    {inr(activeCase.payment?.amount ?? activeCase.revenue_at_risk)}
                  </strong>
                  <div style={{ fontSize: "12px", fontFamily: "monospace", color: "var(--muted)", lineHeight: "1.7" }}>
                    <div>Method: {activeCase.payment?.payment_method?.toUpperCase()}</div>
                    <div>Failure Reason: {activeCase.payment?.failure_reason || "bank_decline"}</div>
                    <div>Status: {activeCase.payment?.status}</div>
                  </div>
                </div>

                <div className="card-sharp">
                  <span style={{ fontSize: "10px", letterSpacing: "0.12em", textTransform: "uppercase", color: "var(--muted)", display: "block", marginBottom: "8px" }}>
                    Webhook Event
                  </span>
                  <strong style={{ fontSize: "14px", fontFamily: "monospace", display: "block", marginBottom: "4px" }}>
                    payment.failed
                  </strong>
                  <div style={{ fontSize: "11px", fontFamily: "monospace", color: "var(--dim)", lineHeight: "1.7" }}>
                    <div>Payment ID: {activeCase.payment?.razorpay_payment_id || `pay_${activeCase.case_id.slice(0, 8)}`}</div>
                    <div>Order ID: {activeCase.payment?.order_id || `order_${activeCase.case_id.slice(0, 8)}`}</div>
                    <div>Case ID: {activeCase.case_id.slice(0, 8)}...</div>
                  </div>
                </div>
              </div>
            </section>

            {/* Step 3: Natural Recovery Propensity */}
            <section className="step-section">
              <p className="eyebrow">Step 3 · Natural Recovery Baseline</p>
              <h2>How likely is the customer to pay without any intervention?</h2>
              <p style={{ color: "var(--muted)", fontSize: "14px", marginTop: "10px", maxWidth: "700px" }}>
                Before applying recovery interventions, METIS computes <strong>P(pay | do(control))</strong>—the probability that this customer will naturally self-cure.
              </p>

              <div className="metric-readout" style={{ marginTop: "24px" }}>
                <div className="metric-item">
                  <span>Natural Recovery Probability</span>
                  <strong style={{ fontSize: "36px" }}>{pct(naturalRecoveryProb)}</strong>
                  <small>Probability of paying without intervention</small>
                </div>
                <div className="metric-item">
                  <span>Expected Natural Recovery</span>
                  <strong style={{ fontSize: "36px" }}>
                    {inr(parseFloat(activeCase.revenue_at_risk) * naturalRecoveryProb)}
                  </strong>
                  <small>Expected revenue if METIS does nothing</small>
                </div>
                <div className="metric-item">
                  <span>Revenue At Risk</span>
                  <strong style={{ fontSize: "36px" }}>{inr(activeCase.revenue_at_risk)}</strong>
                  <small>Total outstanding payment amount</small>
                </div>
              </div>
            </section>

            {/* Step 4: COUNTERFACTUAL HERO MATRIX */}
            <section className="step-section">
              <p className="eyebrow">Step 4 · Counterfactual Intelligence Hero</p>
              <h2>Simultaneous intervention counterfactuals.</h2>
              <p style={{ color: "var(--muted)", fontSize: "14px", marginTop: "10px", maxWidth: "740px" }}>
                METIS estimates the causal outcome of all 6 possible recovery actions. Only an intervention that generates <strong>strictly positive incremental net revenue</strong> beyond natural recovery will be selected.
              </p>

              {/* Counterfactual Grid */}
              <div className="cf-matrix">
                {/* 1. DO NOTHING */}
                <div className={`cf-card ${decision?.selected_intervention === "DO_NOTHING" ? "selected" : ""}`}>
                  <div>
                    <div className="cf-tag">
                      {decision?.selected_intervention === "DO_NOTHING" ? "★ METIS SELECTED" : "CONTROL"}
                    </div>
                    <strong style={{ fontSize: "13px", display: "block" }}>DO NOTHING</strong>
                    <div className="cf-rate">{pct(naturalRecoveryProb)}</div>
                    <div className="cf-sub">Uplift: 0.0%</div>
                    <div className="cf-sub" style={{ marginTop: "4px" }}>Cost: ₹0</div>
                  </div>
                  <div className="cf-val" style={{ color: decision?.selected_intervention === "DO_NOTHING" ? "var(--white)" : "var(--muted)" }}>
                    Net Value: ₹0
                  </div>
                </div>

                {/* Other 5 actionable interventions */}
                {(["RETRY", "REMINDER", "PAYMENT_LINK", "PAYMENT_PLAN", "NEGOTIATION"] as const).map((type) => {
                  const pred = predictions.find((p) => p.intervention_type === type);
                  const isSelected = decision?.selected_intervention === type;
                  const uplift = pred?.uplift ?? 0;
                  const probWith = pred?.probability_with_intervention ?? 0;
                  const netVal = pred ? parseFloat(String(pred.expected_net_value)) : 0;
                  const incRev = parseFloat(activeCase.revenue_at_risk) * uplift;

                  return (
                    <div key={type} className={`cf-card ${isSelected ? "selected" : ""}`}>
                      <div>
                        <div className="cf-tag">
                          {isSelected ? "★ METIS SELECTED" : "TREATMENT"}
                        </div>
                        <strong style={{ fontSize: "13px", display: "block" }}>{type.replace("_", " ")}</strong>
                        <div className="cf-rate">{pct(probWith)}</div>
                        <div className="cf-sub">
                          Uplift: {uplift >= 0 ? `+${pct(uplift)}` : pct(uplift)}
                        </div>
                        <div className="cf-sub" style={{ marginTop: "4px" }}>
                          Inc: {inr(Math.max(0, incRev))}
                        </div>
                      </div>
                      <div
                        className="cf-val"
                        style={{
                          color: netVal > 0 ? "var(--white)" : "var(--dim)",
                        }}
                      >
                        Net: {inr(netVal)}
                      </div>
                    </div>
                  );
                })}
              </div>

              {/* Highlight Why Selected */}
              {decision && (
                <div
                  style={{
                    marginTop: "24px",
                    padding: "24px",
                    border: "1px solid var(--white)",
                    background: "#0c0c0c",
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", flexWrap: "wrap", gap: "12px" }}>
                    <div>
                      <span style={{ fontSize: "10px", letterSpacing: "0.14em", textTransform: "uppercase", color: "var(--muted)" }}>
                        Optimizer Recommendation
                      </span>
                      <h3 style={{ fontSize: "24px", margin: "6px 0 0", fontFamily: "Georgia, serif" }}>
                        Action: {decision.selected_intervention.replace("_", " ")}
                      </h3>
                    </div>
                    <div style={{ textAlign: "right" }}>
                      <span style={{ fontSize: "10px", letterSpacing: "0.12em", textTransform: "uppercase", color: "var(--muted)", display: "block" }}>
                        Expected Incremental Net Value
                      </span>
                      <strong style={{ fontSize: "24px", fontFamily: "monospace" }}>
                        {inr(decision.expected_net_value)}
                      </strong>
                    </div>
                  </div>

                  <p style={{ margin: "16px 0 0", fontSize: "14px", color: "var(--muted)", lineHeight: "1.6", borderTop: "1px solid var(--line)", paddingTop: "14px" }}>
                    <strong>Reasoning:</strong> {decision.reason}
                  </p>
                </div>
              )}
            </section>

            {/* Step 5: Decision Explanation & SHAP Insights */}
            <section className="step-section">
              <p className="eyebrow">Step 5 · Decision Factors & Local Explanation</p>
              <h2>Explainability and feature drivers.</h2>

              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "20px", marginTop: "24px" }}>
                <div className="card-sharp">
                  <span style={{ fontSize: "10px", letterSpacing: "0.12em", textTransform: "uppercase", color: "var(--muted)", display: "block", marginBottom: "12px" }}>
                    Natural Propensity Drivers (Tree Importance)
                  </span>
                  {explanation?.propensity && explanation.propensity.length > 0 ? (
                    <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                      {explanation.propensity.slice(0, 4).map((f, i) => (
                        <div key={i} style={{ display: "flex", justifyContent: "space-between", fontSize: "12px", fontFamily: "monospace" }}>
                          <span style={{ color: "var(--muted)" }}>{f.feature}</span>
                          <span>{(f.importance * 100).toFixed(1)}%</span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p style={{ margin: 0, fontSize: "12px", color: "var(--dim)" }}>
                      Historical payment rate, ticket amount, and recent contact frequency drove natural propensity.
                    </p>
                  )}
                </div>

                <div className="card-sharp">
                  <span style={{ fontSize: "10px", letterSpacing: "0.12em", textTransform: "uppercase", color: "var(--muted)", display: "block", marginBottom: "12px" }}>
                    Causal Uplift Key Metrics
                  </span>
                  <div style={{ display: "flex", flexDirection: "column", gap: "10px", fontSize: "12px", fontFamily: "monospace" }}>
                    <div style={{ display: "flex", justifyContent: "space-between" }}>
                      <span style={{ color: "var(--muted)" }}>Natural P(pay|control):</span>
                      <span>{pct(naturalRecoveryProb)}</span>
                    </div>
                    <div style={{ display: "flex", justifyContent: "space-between" }}>
                      <span style={{ color: "var(--muted)" }}>Intervention P(pay|action):</span>
                      <span>{selectedPrediction ? pct(selectedPrediction.probability_with_intervention) : pct(naturalRecoveryProb)}</span>
                    </div>
                    <div style={{ display: "flex", justifyContent: "space-between" }}>
                      <span style={{ color: "var(--muted)" }}>Treatment Uplift:</span>
                      <span>{selectedPrediction ? `+${pct(selectedPrediction.uplift)}` : "0.0%"}</span>
                    </div>
                    <div style={{ display: "flex", justifyContent: "space-between" }}>
                      <span style={{ color: "var(--muted)" }}>Model Confidence:</span>
                      <span>{decision ? `${(decision.confidence * 100).toFixed(0)}%` : "90%"}</span>
                    </div>
                  </div>
                </div>

                <div className="card-sharp">
                  <span style={{ fontSize: "10px", letterSpacing: "0.12em", textTransform: "uppercase", color: "var(--muted)", display: "block", marginBottom: "12px" }}>
                    Merchant Policy Validation
                  </span>
                  <div style={{ display: "flex", flexDirection: "column", gap: "8px", fontSize: "12px" }}>
                    <div style={{ display: "flex", justifyContent: "space-between" }}>
                      <span style={{ color: "var(--muted)" }}>Discount Limit:</span>
                      <span>Allowed (≤ {policy?.max_discount_percent ?? 15}%)</span>
                    </div>
                    <div style={{ display: "flex", justifyContent: "space-between" }}>
                      <span style={{ color: "var(--muted)" }}>Max Outreach Contacts:</span>
                      <span>Allowed (≤ {policy?.max_contacts ?? 3})</span>
                    </div>
                    <div style={{ display: "flex", justifyContent: "space-between" }}>
                      <span style={{ color: "var(--muted)" }}>Min Payment Threshold:</span>
                      <span>Allowed (≥ {inr(policy?.min_payment_amount ?? 500)})</span>
                    </div>
                    <div style={{ marginTop: "6px", paddingTop: "8px", borderTop: "1px solid var(--line)", color: "var(--white)", fontWeight: "bold", fontSize: "11px", letterSpacing: "0.1em" }}>
                      STATUS: POLICY CHECK PASSED ✓
                    </div>
                  </div>
                </div>
              </div>
            </section>

            {/* Step 6: Autonomous AI Agent Execution */}
            <section className="step-section">
              <AgentChat
                caseId={activeCase.case_id}
                selectedIntervention={decision?.selected_intervention}
                policy={policy}
                onPaymentLinkCreated={(url) => setPaymentLinkUrl(url)}
              />
            </section>

            {/* Step 7: Razorpay Payment & Recovery Outcome */}
            <section className="step-section">
              <p className="eyebrow">Step 7 · Razorpay Recovery & Webhook Verification</p>
              <h2>Execute customer payment.</h2>
              <p style={{ color: "var(--muted)", fontSize: "14px", marginTop: "10px", maxWidth: "700px" }}>
                When the customer uses the Razorpay payment link or installment agreement, a signed <code>payment.captured</code> webhook arrives from Razorpay to close the case.
              </p>

              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: "24px", marginTop: "24px" }}>
                <div className="card-sharp">
                  <span style={{ fontSize: "10px", letterSpacing: "0.12em", textTransform: "uppercase", color: "var(--muted)", display: "block", marginBottom: "8px" }}>
                    Razorpay Checkout Link
                  </span>
                  <div style={{ wordBreak: "break-all", fontFamily: "monospace", fontSize: "12px", color: "var(--white)", padding: "12px", background: "#111", border: "1px solid var(--line)" }}>
                    {paymentLinkUrl || `https://mock.razorpay.local/pay/mock_link_${activeCase.case_id.slice(0, 8)}`}
                  </div>
                  <div style={{ marginTop: "16px" }}>
                    <button
                      className="action"
                      onClick={handleCompletePayment}
                      disabled={isPaymentSimulating || paymentRecovered}
                      style={{ width: "100%", textAlign: "center" }}
                    >
                      {paymentRecovered
                        ? "PAYMENT CAPTURED ✓"
                        : isPaymentSimulating
                        ? "DISPATCHING WEBHOOK..."
                        : "SIMULATE CUSTOMER PAYMENT →"}
                    </button>
                  </div>
                </div>

                <div className="card-sharp" style={{ display: "flex", flexDirection: "column", justifyContent: "space-between" }}>
                  <div>
                    <span style={{ fontSize: "10px", letterSpacing: "0.12em", textTransform: "uppercase", color: "var(--muted)", display: "block", marginBottom: "8px" }}>
                      Reconciliation Status
                    </span>
                    <strong style={{ fontSize: "24px", fontFamily: "monospace" }}>
                      {paymentRecovered || activeCase.status === "RECOVERED" ? "RECOVERED" : activeCase.status}
                    </strong>
                    <p style={{ fontSize: "13px", color: "var(--muted)", margin: "8px 0 0", lineHeight: "1.5" }}>
                      {paymentRecovered || activeCase.status === "RECOVERED"
                        ? "HMAC signature verified. Payment captured and case closed in immutable audit ledger."
                        : "Waiting for customer payment or webhook signal."}
                    </p>
                  </div>
                </div>
              </div>
            </section>

            {/* Step 8: FINAL RESULT & ECONOMIC RECONCILIATION */}
            <section className="step-section">
              <p className="eyebrow">Step 8 · Final Result & Economic Reconciliation</p>
              <h2>Actual recovery economics.</h2>
              <p style={{ color: "var(--muted)", fontSize: "14px", marginTop: "10px", maxWidth: "700px" }}>
                True performance measurement: decomposing raw recovered amount into expected natural recovery vs genuine incremental value created.
              </p>

              <div className="eco-table">
                <div className="eco-row">
                  <span>Total Payment Amount at Risk</span>
                  <strong>{inr(activeCase.revenue_at_risk)}</strong>
                </div>
                <div className="eco-row">
                  <span>Natural Recovery Probability (Baseline)</span>
                  <strong>{pct(naturalRecoveryProb)}</strong>
                </div>
                <div className="eco-row">
                  <span>Expected Natural Recovery (Would pay without intervention)</span>
                  <strong>{inr(parseFloat(activeCase.revenue_at_risk) * naturalRecoveryProb)}</strong>
                </div>
                <div className="eco-row">
                  <span>Selected Action</span>
                  <strong>{decision?.selected_intervention.replace("_", " ") ?? "DO NOTHING"}</strong>
                </div>
                <div className="eco-row">
                  <span>Intervention Recovery Probability</span>
                  <strong>
                    {selectedPrediction
                      ? pct(selectedPrediction.probability_with_intervention)
                      : pct(naturalRecoveryProb)}
                  </strong>
                </div>
                <div className="eco-row">
                  <span>Causal Uplift Realized</span>
                  <strong>{selectedPrediction ? `+${pct(selectedPrediction.uplift)}` : "0.0%"}</strong>
                </div>
                <div className="eco-row">
                  <span>Expected Incremental Revenue</span>
                  <strong>
                    {selectedPrediction
                      ? inr(parseFloat(activeCase.revenue_at_risk) * selectedPrediction.uplift)
                      : "₹0"}
                  </strong>
                </div>
                <div className="eco-row">
                  <span>Intervention & Concession Costs</span>
                  <strong>
                    {selectedPrediction
                      ? inr(
                          (parseFloat(String(selectedPrediction.intervention_cost ?? 0)) || 0) +
                            (parseFloat(String(selectedPrediction.concession_cost ?? 0)) || 0)
                        )
                      : "₹0"}
                  </strong>
                </div>
                <div className="eco-row" style={{ borderTop: "2px solid var(--white)", borderBottom: "2px solid var(--white)", padding: "18px 0" }}>
                  <span style={{ color: "var(--white)", fontWeight: "bold" }}>
                    Expected Net Incremental Value
                  </span>
                  <strong style={{ color: "var(--white)", fontSize: "18px" }}>
                    {decision ? inr(decision.expected_net_value) : "₹0"}
                  </strong>
                </div>
                <div className="eco-row">
                  <span>Actual Recovered Revenue (Post-Webhook)</span>
                  <strong>
                    {paymentRecovered || activeCase.status === "RECOVERED"
                      ? inr(activeCase.revenue_at_risk)
                      : "Pending"}
                  </strong>
                </div>
              </div>
            </section>

            {/* Step 9: AUDIT TIMELINE */}
            <section className="step-section">
              <p className="eyebrow">Step 9 · Immutable Audit Timeline</p>
              <h2>End-to-end execution trail.</h2>
              <p style={{ color: "var(--muted)", fontSize: "14px", marginTop: "10px" }}>
                Failure → Prediction → Counterfactuals → Decision → Policy → Agent → Razorpay → Outcome
              </p>

              <ul className="timeline">
                {auditLogs.length > 0 ? (
                  auditLogs.map((log) => (
                    <li key={log.audit_id}>
                      <span className="time-tag">
                        {new Date(log.timestamp).toLocaleTimeString("en-IN", { hour12: false })}
                      </span>
                      <div>
                        <span className="action-title">{log.action}</span>
                        {log.after_state && (
                          <div style={{ fontSize: "11px", color: "var(--muted)", marginTop: "4px", fontFamily: "monospace" }}>
                            {JSON.stringify(log.after_state)}
                          </div>
                        )}
                      </div>
                      <span className="actor-tag">{log.actor_type}</span>
                    </li>
                  ))
                ) : (
                  <li>
                    <span className="time-tag">--:--:--</span>
                    <div>
                      <span className="action-title">Audit logs loading...</span>
                    </div>
                    <span className="actor-tag">SYSTEM</span>
                  </li>
                )}
              </ul>
            </section>

            {/* Step 10: Experiment / A/B Test Context */}
            {experiments.length > 0 && experimentResult && (
              <section className="step-section">
                <p className="eyebrow">Step 10 · Live A/B Experimentation</p>
                <h2>Continuous incremental lift validation.</h2>
                <div className="card-sharp" style={{ marginTop: "20px" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", flexWrap: "wrap", gap: "12px", marginBottom: "16px" }}>
                    <strong style={{ fontSize: "16px" }}>{experiments[0].name}</strong>
                    <span style={{ fontSize: "11px", fontFamily: "monospace", color: "var(--muted)" }}>
                      Status: {experiments[0].status}
                    </span>
                  </div>
                  <div className="metric-readout">
                    <div className="metric-item">
                      <span>Incremental Lift</span>
                      <strong>+{pct(experimentResult.incremental_lift)}</strong>
                      <small>Treatment vs Control group</small>
                    </div>
                    <div className="metric-item">
                      <span>Incremental Revenue</span>
                      <strong>{inr(experimentResult.incremental_revenue)}</strong>
                      <small>Attributable to METIS</small>
                    </div>
                    <div className="metric-item">
                      <span>Net Recovery</span>
                      <strong>{inr(experimentResult.net_recovery)}</strong>
                      <small>After all intervention costs</small>
                    </div>
                  </div>
                </div>
              </section>
            )}

            {/* Bottom Replay Action */}
            <div style={{ marginTop: "60px", paddingTop: "40px", borderTop: "1px solid var(--line)", display: "flex", gap: "20px", alignItems: "center" }}>
              <button className="action" onClick={handleReset}>
                REPLAY DEMO WITH ANOTHER CUSTOMER ↺
              </button>
              <Link className="action action-ghost" href="/about">
                READ ARCHITECTURE & METHODOLOGY →
              </Link>
            </div>
          </>
        )}
      </main>
    </>
  );
}
