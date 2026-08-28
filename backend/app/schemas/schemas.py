"""
Pydantic schemas for every API request and response.
Keep schemas strictly separated from ORM models.
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.models import (
    AgentRunStatus,
    AuditActorType,
    CustomerSegment,
    DecisionSource,
    ExperimentStatus,
    FatigueLevel,
    InteractionChannel,
    InterventionStatus,
    InterventionType,
    MerchantStatus,
    PaymentPlanFrequency,
    PaymentPlanStatus,
    PaymentStatus,
    RecoveryCaseStatus,
    RecoveryStatus,
)


# ─── Shared ───────────────────────────────────────────────────────────────────


class OKResponse(BaseModel):
    ok: bool = True
    message: str = "success"


# ─── Merchant ─────────────────────────────────────────────────────────────────


class MerchantCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    currency: str = Field("INR", min_length=3, max_length=3)
    timezone: str = Field("Asia/Kolkata")


class MerchantRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    merchant_id: str
    name: str
    currency: str
    timezone: str
    status: MerchantStatus
    created_at: datetime
    updated_at: datetime


# ─── Customer ─────────────────────────────────────────────────────────────────


class CustomerCreate(BaseModel):
    merchant_id: str
    external_customer_id: Optional[str] = None
    name: str = Field(..., min_length=1, max_length=255)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=20)
    segment: CustomerSegment = CustomerSegment.REGULAR


class CustomerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    customer_id: str
    merchant_id: str
    external_customer_id: Optional[str]
    name: str
    email: Optional[str]
    phone: Optional[str]
    segment: CustomerSegment
    created_at: datetime
    updated_at: datetime


# ─── Payment ──────────────────────────────────────────────────────────────────


class PaymentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    payment_id: str
    merchant_id: str
    customer_id: str
    razorpay_payment_id: Optional[str]
    order_id: Optional[str]
    amount: Decimal
    currency: str
    payment_method: Optional[str]
    status: PaymentStatus
    failure_reason: Optional[str]
    failed_at: Optional[datetime]
    due_at: Optional[datetime]
    created_at: datetime


class PaymentCreate(BaseModel):
    """Payment ingestion payload from a merchant system or Razorpay sync."""

    merchant_id: str
    customer_id: str
    razorpay_payment_id: Optional[str] = Field(None, max_length=255)
    order_id: Optional[str] = Field(None, max_length=255)
    amount: Decimal = Field(..., gt=0, max_digits=12, decimal_places=2)
    currency: str = Field("INR", min_length=3, max_length=3)
    payment_method: Optional[str] = Field(None, max_length=50)
    status: PaymentStatus = PaymentStatus.CREATED
    failure_reason: Optional[str] = Field(None, max_length=500)
    failed_at: Optional[datetime] = None
    due_at: Optional[datetime] = None


# ─── Recovery Case ────────────────────────────────────────────────────────────


class RecoveryCaseCreate(BaseModel):
    payment_id: str


class RecoveryCaseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    case_id: str
    payment_id: str
    customer_id: str
    merchant_id: str
    status: RecoveryCaseStatus
    revenue_at_risk: Decimal
    priority_score: Optional[float]
    created_at: datetime
    updated_at: datetime
    closed_at: Optional[datetime]


class RecoveryCaseDetail(RecoveryCaseRead):
    payment: PaymentRead
    customer: CustomerRead


# ─── Intervention Predictions ─────────────────────────────────────────────────


class InterventionPredictionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    prediction_id: str
    case_id: str
    intervention_type: InterventionType
    probability_without_intervention: float
    probability_with_intervention: float
    uplift: float
    expected_recovery: Decimal
    intervention_cost: Decimal
    concession_cost: Decimal
    fatigue_cost: Decimal
    expected_net_value: Decimal
    model_version: Optional[str]
    created_at: datetime


class CasePredictionsResponse(BaseModel):
    case_id: str
    predictions: list[InterventionPredictionRead]


# ─── Recovery Decision ────────────────────────────────────────────────────────


class RecoveryDecisionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    decision_id: str
    case_id: str
    selected_intervention: InterventionType
    expected_net_value: Decimal
    confidence: float
    reason: Optional[str]
    decision_source: DecisionSource
    created_at: datetime


# ─── Merchant Policy ──────────────────────────────────────────────────────────


class MerchantPolicyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    policy_id: str
    merchant_id: str
    max_discount_percent: float
    max_contacts: int
    max_negotiation_attempts: int
    min_payment_amount: Decimal
    max_installment_period_days: int
    allowed_channels: list[str]
    stopping_rules: Optional[Any]
    updated_at: datetime


class MerchantPolicyUpdate(BaseModel):
    max_discount_percent: Optional[float] = Field(None, ge=0, le=100)
    max_contacts: Optional[int] = Field(None, ge=1, le=20)
    max_negotiation_attempts: Optional[int] = Field(None, ge=0, le=10)
    min_payment_amount: Optional[Decimal] = Field(None, ge=0)
    max_installment_period_days: Optional[int] = Field(None, ge=7, le=365)
    allowed_channels: Optional[list[InteractionChannel]] = None
    stopping_rules: Optional[Any] = None


# ─── Policy Validation ────────────────────────────────────────────────────────


class PolicyValidateRequest(BaseModel):
    merchant_id: str
    action: str
    parameters: dict[str, Any] = Field(default_factory=dict)


class PolicyValidateResponse(BaseModel):
    allowed: bool
    reason: Optional[str] = None


# ─── Payment Plan ─────────────────────────────────────────────────────────────


class PaymentPlanCreate(BaseModel):
    installment_count: int = Field(..., ge=2, le=12)
    frequency: PaymentPlanFrequency = PaymentPlanFrequency.MONTHLY
    start_date: datetime


class PaymentPlanRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    plan_id: str
    case_id: str
    customer_id: str
    total_amount: Decimal
    installment_count: int
    installment_amount: Decimal
    frequency: PaymentPlanFrequency
    start_date: datetime
    end_date: datetime
    status: PaymentPlanStatus
    created_at: datetime


# ─── Simulation ───────────────────────────────────────────────────────────────


class SimulateRequest(BaseModel):
    case_id: str
    interventions: Optional[list[InterventionType]] = None


class SimulateResult(BaseModel):
    intervention_type: InterventionType
    probability_with_intervention: float
    uplift: float
    expected_recovery: Decimal
    expected_net_value: Decimal


class SimulateResponse(BaseModel):
    case_id: str
    results: list[SimulateResult]


class PolicySimulateRequest(BaseModel):
    merchant_id: str
    proposed_policy: MerchantPolicyUpdate


class PolicySimulateResult(BaseModel):
    current_expected_recovery: Decimal
    proposed_expected_recovery: Decimal
    delta: Decimal
    breakdown: dict[str, Any]


# ─── Agent ────────────────────────────────────────────────────────────────────


class AgentRunCreate(BaseModel):
    case_id: str


class AgentRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    run_id: str
    case_id: str
    model_name: str
    status: AgentRunStatus
    input_summary: Optional[str]
    output_summary: Optional[str]
    started_at: datetime
    completed_at: Optional[datetime]


class AgentMessageRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)


class AgentMessageResponse(BaseModel):
    run_id: str
    reply: str
    status: AgentRunStatus
    tool_calls_made: int


# ─── Negotiation ──────────────────────────────────────────────────────────────


class NegotiationStart(BaseModel):
    initial_message: Optional[str] = None


class NegotiationState(BaseModel):
    case_id: str
    run_id: str
    status: AgentRunStatus
    conversation: list[dict[str, str]]
    attempts: int
    current_offer: Optional[dict[str, Any]]


# ─── Experiment ───────────────────────────────────────────────────────────────


class ExperimentCreate(BaseModel):
    merchant_id: str
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    start_at: Optional[datetime] = None
    end_at: Optional[datetime] = None


class ExperimentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    experiment_id: str
    merchant_id: str
    name: str
    description: Optional[str]
    status: ExperimentStatus
    start_at: Optional[datetime]
    end_at: Optional[datetime]
    created_at: datetime


class ExperimentAssignRequest(BaseModel):
    case_id: str
    group_name: str
    intervention_type: Optional[InterventionType] = None


class ExperimentResults(BaseModel):
    experiment_id: str
    groups: list[dict[str, Any]]
    total_recovery_rate: float
    incremental_lift: float
    incremental_revenue: Decimal
    net_recovery: Decimal
    intervention_cost: Decimal
    concession_cost: Decimal


# ─── Razorpay ─────────────────────────────────────────────────────────────────


class PaymentLinkCreate(BaseModel):
    case_id: str
    description: Optional[str] = None
    expiry_minutes: int = Field(default=1440, ge=15, le=10080)  # 15 min – 7 days


class PaymentLinkResponse(BaseModel):
    payment_link_id: str
    short_url: str
    amount: Decimal
    currency: str
    expires_at: datetime


# ─── Dashboard ────────────────────────────────────────────────────────────────


class DashboardOverview(BaseModel):
    merchant_id: str
    revenue_at_risk: Decimal
    expected_natural_recovery: Decimal
    expected_incremental_recovery: Decimal
    actual_recovered_revenue: Decimal
    open_cases: int
    in_progress_cases: int
    recovered_cases: int
    escalated_cases: int


class RecoveryAnalytics(BaseModel):
    by_intervention: list[dict[str, Any]]
    by_customer_segment: list[dict[str, Any]]
    by_payment_method: list[dict[str, Any]]
    by_failure_reason: list[dict[str, Any]]


# ─── Audit ────────────────────────────────────────────────────────────────────


class AuditLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    audit_id: str
    merchant_id: Optional[str]
    case_id: Optional[str]
    actor_type: AuditActorType
    actor_id: Optional[str]
    action: str
    before_state: Optional[Any]
    after_state: Optional[Any]
    timestamp: datetime


class CaseAuditTrail(BaseModel):
    case_id: str
    logs: list[AuditLogRead]
