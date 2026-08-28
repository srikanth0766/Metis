from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, relationship
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    pass


def _uuid() -> str:
    return str(uuid.uuid4())


# ─── Enumerations ─────────────────────────────────────────────────────────────


class MerchantStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    SUSPENDED = "SUSPENDED"


class CustomerSegment(str, enum.Enum):
    HIGH_VALUE = "HIGH_VALUE"
    REGULAR = "REGULAR"
    AT_RISK = "AT_RISK"
    DORMANT = "DORMANT"


class PaymentStatus(str, enum.Enum):
    CREATED = "CREATED"
    AUTHORIZED = "AUTHORIZED"
    CAPTURED = "CAPTURED"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"
    OVERDUE = "OVERDUE"


class RecoveryCaseStatus(str, enum.Enum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    RECOVERED = "RECOVERED"
    ESCALATED = "ESCALATED"
    CLOSED = "CLOSED"


class InterventionType(str, enum.Enum):
    RETRY = "RETRY"
    REMINDER = "REMINDER"
    PAYMENT_LINK = "PAYMENT_LINK"
    PAYMENT_PLAN = "PAYMENT_PLAN"
    NEGOTIATION = "NEGOTIATION"
    ESCALATION = "ESCALATION"
    DO_NOTHING = "DO_NOTHING"


class InterventionStatus(str, enum.Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class InteractionChannel(str, enum.Enum):
    EMAIL = "EMAIL"
    WHATSAPP = "WHATSAPP"
    SMS = "SMS"
    VOICE = "VOICE"
    IN_APP = "IN_APP"


class InteractionDirection(str, enum.Enum):
    INBOUND = "INBOUND"
    OUTBOUND = "OUTBOUND"


class PaymentPlanStatus(str, enum.Enum):
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    DEFAULTED = "DEFAULTED"
    CANCELLED = "CANCELLED"


class PaymentPlanFrequency(str, enum.Enum):
    WEEKLY = "WEEKLY"
    BIWEEKLY = "BIWEEKLY"
    MONTHLY = "MONTHLY"


class ExperimentStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"


class RecoveryStatus(str, enum.Enum):
    PENDING = "PENDING"
    PARTIAL = "PARTIAL"
    FULL = "FULL"
    FAILED = "FAILED"


class AgentRunStatus(str, enum.Enum):
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    ESCALATED = "ESCALATED"


class DecisionSource(str, enum.Enum):
    ML_MODEL = "ML_MODEL"
    RULE_BASED = "RULE_BASED"
    HUMAN = "HUMAN"


class AuditActorType(str, enum.Enum):
    SYSTEM = "SYSTEM"
    MODEL = "MODEL"
    AGENT = "AGENT"
    MERCHANT = "MERCHANT"
    HUMAN_OPERATOR = "HUMAN_OPERATOR"


class ModelDeploymentStatus(str, enum.Enum):
    STAGING = "STAGING"
    PRODUCTION = "PRODUCTION"
    DEPRECATED = "DEPRECATED"


class FatigueLevel(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


# ─── Models ───────────────────────────────────────────────────────────────────


class Merchant(Base):
    __tablename__ = "merchants"

    merchant_id = Column(String(36), primary_key=True, default=_uuid)
    name = Column(String(255), nullable=False)
    currency = Column(String(3), nullable=False, default="INR")
    timezone = Column(String(50), nullable=False, default="Asia/Kolkata")
    status = Column(Enum(MerchantStatus), nullable=False, default=MerchantStatus.ACTIVE)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    customers = relationship("Customer", back_populates="merchant")
    payments = relationship("Payment", back_populates="merchant")
    recovery_cases = relationship("RecoveryCase", back_populates="merchant")
    policies = relationship("MerchantPolicy", back_populates="merchant", uselist=False)
    experiments = relationship("Experiment", back_populates="merchant")
    audit_logs = relationship("AuditLog", back_populates="merchant")


class Customer(Base):
    __tablename__ = "customers"

    customer_id = Column(String(36), primary_key=True, default=_uuid)
    merchant_id = Column(String(36), ForeignKey("merchants.merchant_id"), nullable=False, index=True)
    external_customer_id = Column(String(255), nullable=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=True)
    phone = Column(String(20), nullable=True)
    segment = Column(Enum(CustomerSegment), nullable=False, default=CustomerSegment.REGULAR)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    merchant = relationship("Merchant", back_populates="customers")
    payments = relationship("Payment", back_populates="customer")
    recovery_cases = relationship("RecoveryCase", back_populates="customer")
    interactions = relationship("CustomerInteraction", back_populates="customer")
    payment_plans = relationship("PaymentPlan", back_populates="customer")


class Payment(Base):
    __tablename__ = "payments"

    payment_id = Column(String(36), primary_key=True, default=_uuid)
    merchant_id = Column(String(36), ForeignKey("merchants.merchant_id"), nullable=False, index=True)
    customer_id = Column(String(36), ForeignKey("customers.customer_id"), nullable=False, index=True)
    razorpay_payment_id = Column(String(255), nullable=True, unique=True)
    order_id = Column(String(255), nullable=True)
    amount = Column(Numeric(12, 2), nullable=False)  # in INR (not paise)
    currency = Column(String(3), nullable=False, default="INR")
    payment_method = Column(String(50), nullable=True)
    status = Column(Enum(PaymentStatus), nullable=False, default=PaymentStatus.CREATED)
    failure_reason = Column(String(500), nullable=True)
    failed_at = Column(DateTime(timezone=True), nullable=True)
    due_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    merchant = relationship("Merchant", back_populates="payments")
    customer = relationship("Customer", back_populates="payments")
    recovery_cases = relationship("RecoveryCase", back_populates="payment")


class RecoveryCase(Base):
    __tablename__ = "recovery_cases"

    case_id = Column(String(36), primary_key=True, default=_uuid)
    payment_id = Column(String(36), ForeignKey("payments.payment_id"), nullable=False, index=True)
    customer_id = Column(String(36), ForeignKey("customers.customer_id"), nullable=False, index=True)
    merchant_id = Column(String(36), ForeignKey("merchants.merchant_id"), nullable=False, index=True)
    status = Column(Enum(RecoveryCaseStatus), nullable=False, default=RecoveryCaseStatus.OPEN)
    revenue_at_risk = Column(Numeric(12, 2), nullable=False)
    priority_score = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    closed_at = Column(DateTime(timezone=True), nullable=True)

    payment = relationship("Payment", back_populates="recovery_cases")
    customer = relationship("Customer", back_populates="recovery_cases")
    merchant = relationship("Merchant", back_populates="recovery_cases")
    interventions = relationship("Intervention", back_populates="case")
    predictions = relationship("InterventionPrediction", back_populates="case")
    decisions = relationship("RecoveryDecision", back_populates="case")
    interactions = relationship("CustomerInteraction", back_populates="case")
    payment_plans = relationship("PaymentPlan", back_populates="case")
    agent_runs = relationship("AgentRun", back_populates="case")
    outcomes = relationship("RecoveryOutcome", back_populates="case")
    experiment_assignments = relationship("ExperimentAssignment", back_populates="case")
    audit_logs = relationship("AuditLog", back_populates="case")


class Intervention(Base):
    __tablename__ = "interventions"

    intervention_id = Column(String(36), primary_key=True, default=_uuid)
    case_id = Column(String(36), ForeignKey("recovery_cases.case_id"), nullable=False, index=True)
    type = Column(Enum(InterventionType), nullable=False)
    status = Column(Enum(InterventionStatus), nullable=False, default=InterventionStatus.PENDING)
    channel = Column(Enum(InteractionChannel), nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    cost = Column(Numeric(10, 2), nullable=True, default=0)
    concession_amount = Column(Numeric(10, 2), nullable=True, default=0)
    actual_recovered_amount = Column(Numeric(12, 2), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    case = relationship("RecoveryCase", back_populates="interventions")
    outcomes = relationship("RecoveryOutcome", back_populates="intervention")


class InterventionPrediction(Base):
    """Model predictions for each possible intervention on a case."""

    __tablename__ = "intervention_predictions"

    prediction_id = Column(String(36), primary_key=True, default=_uuid)
    case_id = Column(String(36), ForeignKey("recovery_cases.case_id"), nullable=False, index=True)
    intervention_type = Column(Enum(InterventionType), nullable=False)
    probability_without_intervention = Column(Float, nullable=False)
    probability_with_intervention = Column(Float, nullable=False)
    uplift = Column(Float, nullable=False)  # probability_with - probability_without
    expected_recovery = Column(Numeric(12, 2), nullable=False)
    intervention_cost = Column(Numeric(10, 2), nullable=False, default=0)
    concession_cost = Column(Numeric(10, 2), nullable=False, default=0)
    fatigue_cost = Column(Numeric(10, 2), nullable=False, default=0)
    expected_net_value = Column(Numeric(12, 2), nullable=False)
    model_version = Column(String(50), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    case = relationship("RecoveryCase", back_populates="predictions")


class RecoveryDecision(Base):
    """Final decision from the optimization engine for a recovery case."""

    __tablename__ = "recovery_decisions"

    decision_id = Column(String(36), primary_key=True, default=_uuid)
    case_id = Column(String(36), ForeignKey("recovery_cases.case_id"), nullable=False, index=True)
    selected_intervention = Column(Enum(InterventionType), nullable=False)
    expected_net_value = Column(Numeric(12, 2), nullable=False)
    confidence = Column(Float, nullable=False)
    reason = Column(Text, nullable=True)
    decision_source = Column(Enum(DecisionSource), nullable=False, default=DecisionSource.RULE_BASED)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    case = relationship("RecoveryCase", back_populates="decisions")


class MerchantPolicy(Base):
    """Merchant-defined recovery constraints. Exactly one per merchant."""

    __tablename__ = "merchant_policies"

    policy_id = Column(String(36), primary_key=True, default=_uuid)
    merchant_id = Column(String(36), ForeignKey("merchants.merchant_id"), nullable=False, unique=True)
    max_discount_percent = Column(Float, nullable=False, default=5.0)
    max_contacts = Column(Integer, nullable=False, default=3)
    max_negotiation_attempts = Column(Integer, nullable=False, default=2)
    min_payment_amount = Column(Numeric(10, 2), nullable=False, default=500)
    max_installment_period_days = Column(Integer, nullable=False, default=60)
    allowed_channels = Column(JSON, nullable=False, default=list)  # list of InteractionChannel values
    stopping_rules = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    merchant = relationship("Merchant", back_populates="policies")


class CustomerInteraction(Base):
    __tablename__ = "customer_interactions"

    interaction_id = Column(String(36), primary_key=True, default=_uuid)
    case_id = Column(String(36), ForeignKey("recovery_cases.case_id"), nullable=False, index=True)
    customer_id = Column(String(36), ForeignKey("customers.customer_id"), nullable=False, index=True)
    channel = Column(Enum(InteractionChannel), nullable=False)
    direction = Column(Enum(InteractionDirection), nullable=False)
    message = Column(Text, nullable=False)
    interaction_type = Column(String(50), nullable=True)
    response = Column(Text, nullable=True)
    sent_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    case = relationship("RecoveryCase", back_populates="interactions")
    customer = relationship("Customer", back_populates="interactions")


class PaymentPlan(Base):
    __tablename__ = "payment_plans"

    plan_id = Column(String(36), primary_key=True, default=_uuid)
    case_id = Column(String(36), ForeignKey("recovery_cases.case_id"), nullable=False, index=True)
    customer_id = Column(String(36), ForeignKey("customers.customer_id"), nullable=False, index=True)
    total_amount = Column(Numeric(12, 2), nullable=False)
    installment_count = Column(Integer, nullable=False)
    installment_amount = Column(Numeric(12, 2), nullable=False)
    frequency = Column(Enum(PaymentPlanFrequency), nullable=False, default=PaymentPlanFrequency.MONTHLY)
    start_date = Column(DateTime(timezone=True), nullable=False)
    end_date = Column(DateTime(timezone=True), nullable=False)
    status = Column(Enum(PaymentPlanStatus), nullable=False, default=PaymentPlanStatus.PENDING)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    case = relationship("RecoveryCase", back_populates="payment_plans")
    customer = relationship("Customer", back_populates="payment_plans")


class Experiment(Base):
    __tablename__ = "experiments"

    experiment_id = Column(String(36), primary_key=True, default=_uuid)
    merchant_id = Column(String(36), ForeignKey("merchants.merchant_id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(Enum(ExperimentStatus), nullable=False, default=ExperimentStatus.DRAFT)
    start_at = Column(DateTime(timezone=True), nullable=True)
    end_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    merchant = relationship("Merchant", back_populates="experiments")
    assignments = relationship("ExperimentAssignment", back_populates="experiment")


class ExperimentAssignment(Base):
    __tablename__ = "experiment_assignments"

    assignment_id = Column(String(36), primary_key=True, default=_uuid)
    experiment_id = Column(String(36), ForeignKey("experiments.experiment_id"), nullable=False, index=True)
    case_id = Column(String(36), ForeignKey("recovery_cases.case_id"), nullable=False, index=True)
    group_name = Column(String(50), nullable=False)  # CONTROL / RETRY / REMINDER / PAYMENT_PLAN / NEGOTIATION
    intervention_type = Column(Enum(InterventionType), nullable=True)
    assigned_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    experiment = relationship("Experiment", back_populates="assignments")
    case = relationship("RecoveryCase", back_populates="experiment_assignments")


class RecoveryOutcome(Base):
    """Actual recovery results — compared against predictions to measure lift."""

    __tablename__ = "recovery_outcomes"

    outcome_id = Column(String(36), primary_key=True, default=_uuid)
    case_id = Column(String(36), ForeignKey("recovery_cases.case_id"), nullable=False, index=True)
    intervention_id = Column(String(36), ForeignKey("interventions.intervention_id"), nullable=True, index=True)
    amount_recovered = Column(Numeric(12, 2), nullable=True)
    recovery_status = Column(Enum(RecoveryStatus), nullable=False, default=RecoveryStatus.PENDING)
    recovery_time = Column(DateTime(timezone=True), nullable=True)
    intervention_cost = Column(Numeric(10, 2), nullable=False, default=0)
    concession_cost = Column(Numeric(10, 2), nullable=False, default=0)
    net_recovered_amount = Column(Numeric(12, 2), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    case = relationship("RecoveryCase", back_populates="outcomes")
    intervention = relationship("Intervention", back_populates="outcomes")


class WebhookEvent(Base):
    """Razorpay webhook events with idempotency via unique razorpay_event_id."""

    __tablename__ = "webhook_events"
    __table_args__ = (UniqueConstraint("razorpay_event_id", name="uq_webhook_razorpay_event_id"),)

    event_id = Column(String(36), primary_key=True, default=_uuid)
    razorpay_event_id = Column(String(255), nullable=False)
    event_type = Column(String(100), nullable=False)
    payload = Column(JSON, nullable=False)
    signature = Column(String(500), nullable=True)
    processed = Column(Boolean, nullable=False, default=False)
    received_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    processed_at = Column(DateTime(timezone=True), nullable=True)


class AgentRun(Base):
    __tablename__ = "agent_runs"

    run_id = Column(String(36), primary_key=True, default=_uuid)
    case_id = Column(String(36), ForeignKey("recovery_cases.case_id"), nullable=False, index=True)
    model_name = Column(String(100), nullable=False)
    model_version = Column(String(50), nullable=True)
    status = Column(Enum(AgentRunStatus), nullable=False, default=AgentRunStatus.RUNNING)
    input_summary = Column(Text, nullable=True)
    output_summary = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    case = relationship("RecoveryCase", back_populates="agent_runs")
    tool_calls = relationship("AgentToolCall", back_populates="run")


class AgentToolCall(Base):
    """Complete audit trail of every tool called by the AI agent."""

    __tablename__ = "agent_tool_calls"

    tool_call_id = Column(String(36), primary_key=True, default=_uuid)
    run_id = Column(String(36), ForeignKey("agent_runs.run_id"), nullable=False, index=True)
    tool_name = Column(String(100), nullable=False)
    arguments = Column(JSON, nullable=False)
    result = Column(JSON, nullable=True)
    policy_status = Column(String(20), nullable=True)  # ALLOWED / BLOCKED
    executed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    run = relationship("AgentRun", back_populates="tool_calls")


class AuditLog(Base):
    """Immutable audit record. Never update or delete rows."""

    __tablename__ = "audit_logs"

    audit_id = Column(String(36), primary_key=True, default=_uuid)
    merchant_id = Column(String(36), ForeignKey("merchants.merchant_id"), nullable=True, index=True)
    case_id = Column(String(36), ForeignKey("recovery_cases.case_id"), nullable=True, index=True)
    actor_type = Column(Enum(AuditActorType), nullable=False)
    actor_id = Column(String(255), nullable=True)
    action = Column(String(255), nullable=False)
    before_state = Column(JSON, nullable=True)
    after_state = Column(JSON, nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    merchant = relationship("Merchant", back_populates="audit_logs")
    case = relationship("RecoveryCase", back_populates="audit_logs")


class ModelVersion(Base):
    __tablename__ = "model_versions"

    model_version_id = Column(String(36), primary_key=True, default=_uuid)
    model_name = Column(String(100), nullable=False)
    version = Column(String(50), nullable=False)
    model_type = Column(String(100), nullable=False)
    training_dataset = Column(String(255), nullable=True)
    metrics = Column(JSON, nullable=True)
    deployment_status = Column(Enum(ModelDeploymentStatus), nullable=False, default=ModelDeploymentStatus.STAGING)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
