export type Merchant = {
  merchant_id: string;
  name: string;
  currency: string;
  timezone: string;
  status: string;
};

export type Customer = {
  customer_id: string;
  merchant_id: string;
  external_customer_id?: string | null;
  name: string;
  email: string;
  phone: string;
  segment: "HIGH_VALUE" | "REGULAR" | "AT_RISK" | "DORMANT";
};

export type Payment = {
  payment_id: string;
  merchant_id: string;
  customer_id: string;
  razorpay_payment_id?: string | null;
  order_id?: string | null;
  amount: string;
  currency: string;
  payment_method?: string | null;
  status: string;
  failure_reason?: string | null;
  failed_at?: string | null;
  created_at: string;
};

export type RecoveryCase = {
  case_id: string;
  payment_id: string;
  customer_id: string;
  merchant_id: string;
  status: string;
  revenue_at_risk: string;
  priority_score?: number | null;
  created_at: string;
  updated_at: string;
  closed_at?: string | null;
  customer?: Customer;
  payment?: Payment;
};

export type CaseDetail = RecoveryCase & {
  customer: Customer;
  payment: Payment;
};

export type Prediction = {
  prediction_id?: string;
  case_id?: string;
  intervention_type: "DO_NOTHING" | "RETRY" | "REMINDER" | "PAYMENT_LINK" | "PAYMENT_PLAN" | "NEGOTIATION";
  probability_without_intervention: number;
  probability_with_intervention: number;
  uplift: number;
  expected_recovery: string | number;
  intervention_cost?: string | number;
  concession_cost?: string | number;
  fatigue_cost?: string | number;
  expected_net_value: string | number;
  model_version?: string | null;
};

export type Decision = {
  decision_id?: string;
  case_id: string;
  selected_intervention: "DO_NOTHING" | "RETRY" | "REMINDER" | "PAYMENT_LINK" | "PAYMENT_PLAN" | "NEGOTIATION";
  expected_net_value: string;
  confidence: number;
  reason?: string | null;
  decision_source?: string;
  created_at?: string;
};

export type Policy = {
  policy_id?: string;
  merchant_id: string;
  max_discount_percent: number;
  max_contacts: number;
  max_negotiation_attempts: number;
  min_payment_amount: string;
  max_installment_period_days: number;
  allowed_channels: string[];
  stopping_rules?: Record<string, any>;
};

export type Explanation = {
  mode: string;
  propensity: { feature: string; importance: number }[];
  interventions: Record<string, { feature: string; importance: number }[]>;
};

export type Experiment = {
  experiment_id: string;
  name: string;
  status: string;
  description?: string | null;
};

export type ExperimentResult = {
  incremental_lift: number;
  incremental_revenue: string;
  net_recovery: string;
  groups: { group_name: string; recovery_rate: number }[];
};

export type AuditLog = {
  audit_id: string;
  action: string;
  actor_type: string;
  actor_id?: string | null;
  timestamp: string;
  before_state?: Record<string, any> | null;
  after_state?: Record<string, any> | null;
};

export type AgentToolCall = {
  tool_name: string;
  arguments: Record<string, any>;
  result: Record<string, any>;
  policy_status: "ALLOWED" | "BLOCKED";
  executed_at: string;
};

export type AgentMessage = { role: "user" | "assistant"; content: string };
export type AgentRun = {
  run_id: string;
  case_id: string;
  status: string;
  messages: AgentMessage[];
  tools?: AgentToolCall[];
};

export type SystemHealth = {
  ok: boolean;
  service: string;
  ml_mode: string;
  models?: Record<string, string | null>;
};

type AgentRunResponse = {
  run_id: string;
  case_id: string;
  status: string;
  input_summary?: string | null;
  output_summary?: string | null;
};

type AgentMessageResponse = {
  run_id: string;
  reply: string;
  status: string;
  tool_calls_made?: number;
};

const baseUrl = typeof window === "undefined"
  ? process.env.METIS_API_URL ?? process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000"
  : "";

async function api<T>(path: string): Promise<T | null> {
  try {
    const response = await fetch(`${baseUrl}/api/v1${path}`, { cache: "no-store" });
    return response.ok ? await response.json() as T : null;
  } catch {
    return null;
  }
}

async function apiPost<T, B = unknown>(path: string, body: B, headers: Record<string, string> = {}): Promise<T | null> {
  try {
    const response = await fetch(`${baseUrl}/api/v1${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...headers },
      body: JSON.stringify(body),
      cache: "no-store",
    });
    return response.ok ? await response.json() as T : null;
  } catch {
    return null;
  }
}

export async function getSystemHealth(): Promise<SystemHealth | null> {
  try {
    const response = await fetch(`${baseUrl}/health`, { cache: "no-store" });
    return response.ok ? await response.json() as SystemHealth : null;
  } catch {
    return null;
  }
}

export async function getMerchants(): Promise<Merchant[]> {
  return (await api<Merchant[]>("/merchants")) ?? [];
}

export async function getCustomers(merchantId: string): Promise<Customer[]> {
  return (await api<Customer[]>(`/customers?merchant_id=${merchantId}`)) ?? [];
}

export async function getMerchant(): Promise<Merchant | null> {
  const merchants = await getMerchants();
  return merchants[0] ?? null;
}

export async function getCases(merchantId: string): Promise<RecoveryCase[]> {
  return (await api<RecoveryCase[]>(`/recovery/cases?merchant_id=${merchantId}`)) ?? [];
}

export async function getCase(caseId: string): Promise<CaseDetail | null> {
  return api<CaseDetail>(`/recovery/cases/${caseId}`);
}

export async function getPredictions(caseId: string): Promise<Prediction[]> {
  const res = await api<{ case_id: string; predictions: Prediction[] }>(`/recovery/cases/${caseId}/predictions`);
  return res?.predictions ?? [];
}

export async function getDecision(caseId: string): Promise<Decision | null> {
  return api<Decision>(`/recovery/cases/${caseId}/recommendation`);
}

export async function optimizeCase(caseId: string): Promise<Decision | null> {
  return apiPost<Decision>(`/recovery/cases/${caseId}/optimize`, {});
}

export async function getExplanation(caseId: string): Promise<Explanation | null> {
  return api<Explanation>(`/recovery/cases/${caseId}/explanation`);
}

export async function getPolicy(merchantId: string): Promise<Policy | null> {
  return api<Policy>(`/merchants/${merchantId}/policy`);
}

export async function getAudit(caseId: string): Promise<AuditLog[]> {
  return (await api<{ logs: AuditLog[] }>(`/audit/recovery/${caseId}`))?.logs ?? [];
}

export async function getExperiments(merchantId: string): Promise<Experiment[]> {
  return (await api<Experiment[]>(`/experiments?merchant_id=${merchantId}`)) ?? [];
}

export async function getExperimentResults(experimentId: string): Promise<ExperimentResult | null> {
  return api<ExperimentResult>(`/experiments/${experimentId}/results`);
}

export async function createAgentRun(caseId: string): Promise<AgentRun | null> {
  const run = await apiPost<AgentRunResponse, { case_id: string }>(`/agent/runs`, { case_id: caseId });
  return run ? { run_id: run.run_id, case_id: run.case_id, status: run.status, messages: [] } : null;
}

export async function sendAgentMessage(runId: string, content: string): Promise<AgentMessageResponse | null> {
  return apiPost<AgentMessageResponse, { message: string }>(`/agent/runs/${runId}/messages`, { message: content });
}

export async function getAgentTools(runId: string): Promise<AgentToolCall[]> {
  return (await api<AgentToolCall[]>(`/agent/runs/${runId}/tools`)) ?? [];
}

export async function createRazorpayLink(caseId: string, description?: string): Promise<{ payment_link_id: string; short_url: string; amount: string | number; mode: string } | null> {
  return apiPost<{ payment_link_id: string; short_url: string; amount: string | number; mode: string }, any>(
    `/razorpay/payment-links`,
    { case_id: caseId, description }
  );
}

export async function verifyPaymentStatus(paymentId: string): Promise<{ payment_id: string; status: string; is_paid: boolean } | null> {
  return api<{ payment_id: string; status: string; is_paid: boolean }>(`/razorpay/payments/${paymentId}/verify`);
}

export async function simulatePaymentFailure(params: {
  merchant_id: string;
  customer_id: string;
  amount: number;
  payment_method: string;
  failure_reason: string;
  order_id?: string;
  razorpay_payment_id?: string;
  contacts?: number;
  days_ago?: number;
}): Promise<RecoveryCase | null> {
  const failedAt = params.days_ago
    ? new Date(Date.now() - params.days_ago * 24 * 3600 * 1000).toISOString()
    : new Date().toISOString();

  const payment = await apiPost<Payment, any>("/payments", {
    merchant_id: params.merchant_id,
    customer_id: params.customer_id,
    amount: params.amount,
    currency: "INR",
    payment_method: params.payment_method,
    status: "FAILED",
    failure_reason: params.failure_reason,
    failed_at: failedAt,
    order_id: params.order_id || `order_sim_${Date.now().toString(36)}`,
    razorpay_payment_id: params.razorpay_payment_id || `pay_sim_${Date.now().toString(36)}`,
  });

  if (!payment?.payment_id) return null;

  const recoveryCase = await apiPost<RecoveryCase, any>("/recovery/cases", {
    payment_id: payment.payment_id,
  });

  if (recoveryCase && params.contacts && params.contacts > 0) {
    for (let i = 0; i < params.contacts; i++) {
      await apiPost(`/recovery/cases/${recoveryCase.case_id}/interactions`, {
        response_type: "REMINDER",
        notes: i === 0 ? "Automated reminder sent" : "Follow-up",
      });
    }
  }

  return recoveryCase;
}

export async function simulateRazorpayWebhook(params: {
  razorpay_payment_id: string;
  order_id: string;
  amount: number;
}): Promise<{ ok: boolean; dispatch?: any } | null> {
  const payload = {
    event: "payment.captured",
    payload: {
      payment: {
        entity: {
          id: params.razorpay_payment_id,
          order_id: params.order_id,
          amount: Math.round(params.amount * 100),
          status: "captured",
        },
      },
    },
  };

  return apiPost<{ ok: boolean; dispatch?: any }, any>(
    "/webhooks/razorpay",
    payload,
    { "x-razorpay-signature": "metis_test_signature" }
  );
}

export function inr(value: string | number): string {
  const num = typeof value === "number" ? value : parseFloat(value) || 0;
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(num);
}

export function pct(val: number): string {
  return `${(val * 100).toFixed(1)}%`;
}
