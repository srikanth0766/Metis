"""
Typed tool definitions for the METIS AI agent.

Every tool that touches financial data or executes actions MUST call
the policy engine before returning. Tools are pure async functions.
"""
from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


# ─── Tool Schema Definitions ──────────────────────────────────────────────────
# These are passed to the LLM as function-call schemas.

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "get_customer_context",
            "description": "Retrieve customer profile, payment history, and previous recovery attempts.",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_id": {"type": "string", "description": "The customer UUID"},
                },
                "required": ["customer_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_payment_context",
            "description": "Get full details of the outstanding payment including amount, failure reason, and days overdue.",
            "parameters": {
                "type": "object",
                "properties": {
                    "payment_id": {"type": "string", "description": "The payment UUID"},
                },
                "required": ["payment_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_recovery_options",
            "description": "Get available recovery interventions and their predicted outcomes for a case.",
            "parameters": {
                "type": "object",
                "properties": {
                    "case_id": {"type": "string"},
                },
                "required": ["case_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_merchant_policy",
            "description": "Retrieve the merchant's recovery policy constraints.",
            "parameters": {
                "type": "object",
                "properties": {
                    "merchant_id": {"type": "string"},
                },
                "required": ["merchant_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_recovery_value",
            "description": "Calculate expected net recovery value for a specific intervention and amount.",
            "parameters": {
                "type": "object",
                "properties": {
                    "case_id": {"type": "string"},
                    "intervention_type": {
                        "type": "string",
                        "enum": ["RETRY", "REMINDER", "PAYMENT_LINK", "PAYMENT_PLAN", "NEGOTIATION"],
                    },
                    "concession_amount": {"type": "number", "description": "Discount/concession in INR", "default": 0},
                },
                "required": ["case_id", "intervention_type"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_payment_plan",
            "description": "Create an installment payment plan for the customer. Policy validation is mandatory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "case_id": {"type": "string"},
                    "installment_count": {"type": "integer", "minimum": 2, "maximum": 12},
                    "frequency": {"type": "string", "enum": ["WEEKLY", "BIWEEKLY", "MONTHLY"]},
                },
                "required": ["case_id", "installment_count", "frequency"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_payment_link",
            "description": "Generate a secure Razorpay payment link for the outstanding amount.",
            "parameters": {
                "type": "object",
                "properties": {
                    "case_id": {"type": "string"},
                    "description": {"type": "string"},
                },
                "required": ["case_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_payment_status",
            "description": "Check whether the payment has been completed.",
            "parameters": {
                "type": "object",
                "properties": {
                    "payment_id": {"type": "string"},
                },
                "required": ["payment_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "record_customer_response",
            "description": "Log the customer's response, decision, or expressed constraint.",
            "parameters": {
                "type": "object",
                "properties": {
                    "case_id": {"type": "string"},
                    "response_type": {
                        "type": "string",
                        "enum": ["AGREED", "DECLINED", "REQUESTED_PLAN", "EXPRESSED_HARDSHIP", "NO_RESPONSE"],
                    },
                    "notes": {"type": "string"},
                },
                "required": ["case_id", "response_type"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "escalate_to_human",
            "description": "Hand off this case to a human operator. Use when confidence is low or policy limits are reached.",
            "parameters": {
                "type": "object",
                "properties": {
                    "case_id": {"type": "string"},
                    "reason": {"type": "string"},
                },
                "required": ["case_id", "reason"],
            },
        },
    },
]


# ─── Tool Executor ────────────────────────────────────────────────────────────


class ToolExecutor:
    """
    Executes agent tool calls after policy validation.
    Injected with a database session and service references.
    """

    def __init__(self, db: AsyncSession, context: dict[str, Any]) -> None:
        self.db = db
        self.context = context  # case_id, merchant_id, customer_id, payment_id

    async def execute(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Route tool call to the appropriate handler."""
        handler = getattr(self, f"_tool_{tool_name}", None)
        if handler is None:
            logger.error("Unknown tool called: %s", tool_name)
            return {"error": f"Tool '{tool_name}' is not available."}
        try:
            return await handler(**arguments)
        except Exception as exc:
            logger.exception("Tool '%s' raised an error: %s", tool_name, exc)
            return {"error": str(exc)}

    # ── Handlers ──────────────────────────────────────────────────────────────

    async def _tool_get_customer_context(self, customer_id: str) -> dict[str, Any]:
        from app.services.context_service import get_customer_context_data

        return await get_customer_context_data(self.db, customer_id)

    async def _tool_get_payment_context(self, payment_id: str) -> dict[str, Any]:
        from app.services.context_service import get_payment_context_data

        return await get_payment_context_data(self.db, payment_id)

    async def _tool_get_recovery_options(self, case_id: str) -> dict[str, Any]:
        from app.services.prediction_service import get_all_predictions

        predictions = await get_all_predictions(self.db, case_id)
        return {
            "options": [
                {
                    "intervention_type": p.intervention_type.value if hasattr(p.intervention_type, "value") else str(p.intervention_type),
                    "probability_without_intervention": float(p.probability_without_intervention),
                    "probability_with_intervention": float(p.probability_with_intervention),
                    "uplift": float(p.uplift),
                    "expected_recovery": float(p.expected_recovery),
                    "expected_net_value": float(p.expected_net_value),
                }
                for p in predictions
            ]
        }

    async def _tool_get_merchant_policy(self, merchant_id: str) -> dict[str, Any]:
        from app.services.policy_service import get_policy_dict

        return await get_policy_dict(self.db, merchant_id)

    async def _tool_calculate_recovery_value(
        self,
        case_id: str,
        intervention_type: str,
        concession_amount: float = 0,
    ) -> dict[str, Any]:
        from app.services.optimizer_service import calculate_value_for_intervention
        from app.models.models import InterventionType as IT

        return await calculate_value_for_intervention(
            self.db,
            case_id,
            IT(intervention_type),
            Decimal(str(concession_amount)),
        )

    async def _tool_create_payment_plan(
        self,
        case_id: str,
        installment_count: int,
        frequency: str,
    ) -> dict[str, Any]:
        from app.services.recovery_service import create_payment_plan_for_case
        from app.policies.engine import validate_action

        # Must validate before creating
        from app.services.policy_service import get_policy_object

        policy = await get_policy_object(self.db, self.context["merchant_id"])
        case_amount = self.context.get("amount", Decimal("0"))
        installment_amount = case_amount / installment_count

        result = validate_action(
            "CREATE_PAYMENT_PLAN",
            {
                "installment_count": installment_count,
                "period_days": 30 * installment_count if frequency == "MONTHLY" else 7 * installment_count,
                "installment_amount": float(installment_amount),
            },
            policy,
        )
        if not result.allowed:
            return {"error": result.reason, "policy_blocked": True}

        plan = await create_payment_plan_for_case(self.db, case_id, installment_count, frequency)
        return {"plan_id": plan.plan_id, "installment_amount": float(plan.installment_amount), "status": plan.status.value}

    async def _tool_create_payment_link(
        self,
        case_id: str,
        description: str | None = None,
    ) -> dict[str, Any]:
        from app.services.razorpay_service import create_payment_link

        return await create_payment_link(self.db, case_id, description)

    async def _tool_check_payment_status(self, payment_id: str) -> dict[str, Any]:
        from app.services.razorpay_service import verify_payment_status

        return await verify_payment_status(self.db, payment_id)

    async def _tool_record_customer_response(
        self,
        case_id: str,
        response_type: str,
        notes: str = "",
    ) -> dict[str, Any]:
        from app.services.recovery_service import record_interaction

        await record_interaction(self.db, case_id, self.context["customer_id"], response_type, notes)
        return {"recorded": True}

    async def _tool_escalate_to_human(self, case_id: str, reason: str) -> dict[str, Any]:
        from app.services.recovery_service import escalate_case

        await escalate_case(self.db, case_id, reason)
        return {"escalated": True, "reason": reason}
