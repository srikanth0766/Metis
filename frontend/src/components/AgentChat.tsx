"use client";
import { useState, useRef, useEffect } from "react";
import { createAgentRun, sendAgentMessage, getAgentTools, AgentRun, AgentToolCall, Policy, inr } from "../lib/api";

type Props = {
  caseId: string;
  selectedIntervention?: string | null;
  policy?: Policy | null;
  onPaymentLinkCreated?: (url: string) => void;
};

export function AgentChat({ caseId, selectedIntervention, policy, onPaymentLinkCreated }: Props) {
  const [run, setRun] = useState<AgentRun | null>(null);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [tools, setTools] = useState<AgentToolCall[]>([]);
  const [error, setError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [run?.messages, tools]);

  const refreshTools = async (runId: string) => {
    const list = await getAgentTools(runId);
    setTools(list);
    // Check if a payment link was created in tools
    for (const t of list) {
      if (t.tool_name === "create_payment_link" && t.result?.short_url) {
        onPaymentLinkCreated?.(t.result.short_url as string);
      }
    }
  };

  const startRun = async () => {
    setLoading(true);
    setError(null);
    const newRun = await createAgentRun(caseId);
    if (newRun) {
      setRun(newRun);
      // Kick off with an initial opening prompt if appropriate
      const intro = await sendAgentMessage(newRun.run_id, "Hello, I am reaching out regarding my recent transaction.");
      if (intro) {
        setRun((prev) =>
          prev
            ? {
                ...prev,
                status: intro.status,
                messages: [
                  { role: "assistant", content: intro.reply },
                ],
              }
            : null
        );
        await refreshTools(newRun.run_id);
      }
    } else {
      setError("Failed to start agent. Please verify backend connection.");
    }
    setLoading(false);
  };

  const sendMessage = async (messageText?: string) => {
    const msg = (messageText ?? input).trim();
    if (!msg || !run || loading) return;
    setInput("");
    setLoading(true);
    setRun((prev) =>
      prev ? { ...prev, messages: [...prev.messages, { role: "user", content: msg }] } : null
    );

    const response = await sendAgentMessage(run.run_id, msg);
    if (response) {
      setRun((prev) =>
        prev
          ? {
              ...prev,
              status: response.status,
              messages: [...prev.messages, { role: "assistant", content: response.reply }],
            }
          : null
      );
      await refreshTools(run.run_id);
    } else {
      setError("Agent communication error.");
    }
    setLoading(false);
  };

  const done = run ? ["COMPLETED", "FAILED", "ESCALATED"].includes(run.status) : false;

  return (
    <div className="agent-chat" style={{ marginTop: "40px", paddingTop: "32px", borderTop: "1px solid var(--line)" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: "20px" }}>
        <div>
          <p className="eyebrow" style={{ margin: "0 0 6px" }}>Step 6 · Autonomous AI Agent Execution</p>
          <h3 style={{ fontSize: "22px", margin: 0 }}>Grounded Recovery Agent</h3>
        </div>
        {run && (
          <div style={{ display: "flex", gap: "16px", fontSize: "11px", color: "var(--muted)", fontFamily: "monospace" }}>
            <span>RUN: {run.run_id.slice(0, 8)}</span>
            <span style={{ color: run.status === "FAILED" ? "#ff5555" : "var(--white)" }}>{run.status}</span>
          </div>
        )}
      </div>

      <p style={{ color: "var(--muted)", fontSize: "14px", lineHeight: "1.5", margin: "0 0 24px" }}>
        The agent executes only policy-validated interventions. It cannot invent discounts or bypass merchant constraints.
      </p>

      {/* Policy and strategy constraints bar */}
      <div className="chat-context" style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "24px", padding: "18px", border: "1px solid var(--line)", background: "#0a0a0a", marginBottom: "24px" }}>
        <div>
          <span style={{ display: "block", fontSize: "10px", letterSpacing: "0.12em", textTransform: "uppercase", color: "var(--muted)", marginBottom: "6px" }}>
            Mandated Action
          </span>
          <strong style={{ fontSize: "14px", fontFamily: "monospace" }}>
            {selectedIntervention ? selectedIntervention.replaceAll("_", " ") : "EVALUATING..."}
          </strong>
        </div>
        <div>
          <span style={{ display: "block", fontSize: "10px", letterSpacing: "0.12em", textTransform: "uppercase", color: "var(--muted)", marginBottom: "6px" }}>
            Merchant Policy Guardrails
          </span>
          <span style={{ fontSize: "13px", color: "var(--white)" }}>
            Max Discount {policy?.max_discount_percent ?? 15}% · Max Contacts {policy?.max_contacts ?? 3} · Min Payment {inr(policy?.min_payment_amount ?? 500)}
          </span>
        </div>
      </div>

      {!run ? (
        <div style={{ padding: "32px", border: "1px solid var(--line)", textAlign: "center" }}>
          <p style={{ margin: "0 0 20px", color: "var(--muted)", fontSize: "14px" }}>
            Start the Groq-powered autonomous agent to execute recovery for this case.
          </p>
          <button
            className="action"
            onClick={startRun}
            disabled={loading}
            style={{ padding: "14px 28px", fontSize: "11px" }}
          >
            {loading ? "INITIALIZING AGENT..." : "LAUNCH AI AGENT"}
          </button>
          {error && <p style={{ color: "var(--muted)", fontSize: "12px", marginTop: "16px" }}>{error}</p>}
        </div>
      ) : (
        <div style={{ border: "1px solid var(--line)", background: "#050505" }}>
          {/* Tool Calls Audit Log Banner */}
          {tools.length > 0 && (
            <div style={{ padding: "12px 18px", borderBottom: "1px solid var(--line)", background: "#0d0d0d" }}>
              <span style={{ fontSize: "10px", letterSpacing: "0.12em", textTransform: "uppercase", color: "var(--muted)", display: "block", marginBottom: "8px" }}>
                Agent Tool Invocations ({tools.length} executed)
              </span>
              <div style={{ display: "flex", flexWrap: "wrap", gap: "8px" }}>
                {tools.map((t, idx) => (
                  <span
                    key={idx}
                    style={{
                      display: "inline-flex",
                      alignItems: "center",
                      gap: "6px",
                      fontSize: "11px",
                      fontFamily: "monospace",
                      padding: "4px 8px",
                      background: "#161616",
                      border: "1px solid var(--line)",
                    }}
                  >
                    <span style={{ color: "var(--white)" }}>{t.tool_name}</span>
                    <span style={{ fontSize: "9px", padding: "1px 4px", border: "1px solid var(--line)", color: t.policy_status === "ALLOWED" ? "var(--white)" : "var(--muted)" }}>
                      {t.policy_status}
                    </span>
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Conversation history */}
          <div className="chat-messages" style={{ padding: "20px 24px", maxHeight: "380px", overflowY: "auto" }}>
            {run.messages.map((msg, i) => (
              <div
                key={i}
                style={{
                  display: "grid",
                  gridTemplateColumns: "80px 1fr",
                  gap: "16px",
                  padding: "14px 0",
                  borderBottom: i < run.messages.length - 1 ? "1px solid #1a1a1a" : "none",
                  fontSize: "13px",
                  lineHeight: "1.6",
                }}
              >
                <span
                  style={{
                    fontSize: "10px",
                    textTransform: "uppercase",
                    letterSpacing: "0.12em",
                    fontFamily: "monospace",
                    color: msg.role === "assistant" ? "var(--white)" : "var(--muted)",
                  }}
                >
                  {msg.role === "assistant" ? "METIS" : "CUSTOMER"}
                </span>
                <div style={{ whiteSpace: "pre-wrap", color: msg.role === "assistant" ? "var(--white)" : "var(--muted)" }}>
                  {msg.content}
                </div>
              </div>
            ))}
            {loading && (
              <div style={{ display: "grid", gridTemplateColumns: "80px 1fr", gap: "16px", padding: "14px 0", fontSize: "13px" }}>
                <span style={{ fontSize: "10px", textTransform: "uppercase", letterSpacing: "0.12em", fontFamily: "monospace", color: "var(--white)" }}>
                  METIS
                </span>
                <span style={{ color: "var(--muted)", fontFamily: "monospace" }}>thinking & checking policy...</span>
              </div>
            )}
            <div ref={bottomRef} />
          </div>

          {/* Quick preset customer prompts */}
          {!done && (
            <div style={{ padding: "10px 18px", borderTop: "1px solid var(--line)", background: "#0a0a0a", display: "flex", gap: "8px", flexWrap: "wrap", alignItems: "center" }}>
              <span style={{ fontSize: "10px", textTransform: "uppercase", letterSpacing: "0.1em", color: "var(--muted)" }}>
                Suggest:
              </span>
              <button
                type="button"
                onClick={() => sendMessage("Can you send me a secure payment link?")}
                disabled={loading}
                style={{ background: "transparent", border: "1px solid var(--line)", color: "var(--muted)", padding: "4px 10px", fontSize: "11px", borderRadius: "0", cursor: "pointer" }}
              >
                "Send payment link"
              </button>
              <button
                type="button"
                onClick={() => sendMessage("Can I pay in 3 monthly installments?")}
                disabled={loading}
                style={{ background: "transparent", border: "1px solid var(--line)", color: "var(--muted)", padding: "4px 10px", fontSize: "11px", borderRadius: "0", cursor: "pointer" }}
              >
                "Request installment plan"
              </button>
              <button
                type="button"
                onClick={() => sendMessage("Can I get a 10% discount to clear this immediately?")}
                disabled={loading}
                style={{ background: "transparent", border: "1px solid var(--line)", color: "var(--muted)", padding: "4px 10px", fontSize: "11px", borderRadius: "0", cursor: "pointer" }}
              >
                "Negotiate discount"
              </button>
            </div>
          )}

          {/* Input Form */}
          {!done ? (
            <form
              onSubmit={(e) => {
                e.preventDefault();
                sendMessage();
              }}
              style={{ display: "flex", borderTop: "1px solid var(--line)" }}
            >
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Type customer reply..."
                disabled={loading}
                style={{
                  flex: 1,
                  background: "transparent",
                  color: "var(--white)",
                  border: "none",
                  padding: "16px 20px",
                  fontSize: "13px",
                  outline: "none",
                }}
              />
              <button
                type="submit"
                disabled={!input.trim() || loading}
                style={{
                  background: "var(--white)",
                  color: "var(--black)",
                  border: "none",
                  borderRadius: "0",
                  padding: "0 24px",
                  fontSize: "11px",
                  fontWeight: "bold",
                  textTransform: "uppercase",
                  letterSpacing: "0.1em",
                  cursor: !input.trim() || loading ? "not-allowed" : "pointer",
                }}
              >
                SEND
              </button>
            </form>
          ) : (
            <div style={{ padding: "16px 20px", borderTop: "1px solid var(--line)", fontSize: "12px", color: "var(--muted)" }}>
              Agent conversation ended ({run.status.toLowerCase()}).
            </div>
          )}
        </div>
      )}
    </div>
  );
}
