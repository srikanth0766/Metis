"""
Deterministic policy & guardrail engine.

The LLM/agent NEVER bypasses this layer.
Every proposed financial action must pass through validate_action() before execution.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from app.models.models import InteractionChannel, InterventionType, MerchantPolicy


class PolicyViolation(Exception):
    """Raised when a proposed action violates merchant policy."""

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)


class PolicyResult:
    __slots__ = ("allowed", "reason")

    def __init__(self, allowed: bool, reason: str | None = None) -> None:
        self.allowed = allowed
        self.reason = reason

    @classmethod
    def ok(cls) -> "PolicyResult":
        return cls(allowed=True)

    @classmethod
    def blocked(cls, reason: str) -> "PolicyResult":
        return cls(allowed=False, reason=reason)


def validate_action(
    action: str,
    parameters: dict[str, Any],
    policy: MerchantPolicy,
    contact_count: int = 0,
    negotiation_count: int = 0,
) -> PolicyResult:
    """
    Validates a proposed agent action against the merchant's policy.

    Parameters
    ----------
    action:
        One of: DISCOUNT, CONTACT, NEGOTIATE, CREATE_PAYMENT_PLAN,
                CREATE_PAYMENT_LINK, RETRY, ESCALATE
    parameters:
        Action-specific parameters (e.g. {"discount_percent": 5}).
    policy:
        The merchant's MerchantPolicy ORM object.
    contact_count:
        How many times this customer has already been contacted for this case.
    negotiation_count:
        How many negotiation attempts have already occurred for this case.
    """
    action = action.upper()

    if action == "DISCOUNT":
        discount = float(parameters.get("discount_percent", 0))
        if discount > policy.max_discount_percent:
            return PolicyResult.blocked(
                f"Requested discount {discount}% exceeds merchant maximum of {policy.max_discount_percent}%."
            )
        amount_after = Decimal(str(parameters.get("amount_after_discount", 0)))
        if amount_after < policy.min_payment_amount:
            return PolicyResult.blocked(
                f"Amount after discount ₹{amount_after} is below minimum payable amount ₹{policy.min_payment_amount}."
            )
        return PolicyResult.ok()

    if action == "CONTACT":
        if contact_count >= policy.max_contacts:
            return PolicyResult.blocked(
                f"Customer has already been contacted {contact_count} times. Merchant limit is {policy.max_contacts}."
            )
        channel = parameters.get("channel", "").upper()
        allowed = [c.upper() if isinstance(c, str) else c.value for c in (policy.allowed_channels or [])]
        if channel and allowed and channel not in allowed:
            return PolicyResult.blocked(
                f"Channel '{channel}' is not in merchant's allowed channels: {allowed}."
            )
        return PolicyResult.ok()

    if action == "NEGOTIATE":
        if negotiation_count >= policy.max_negotiation_attempts:
            return PolicyResult.blocked(
                f"Negotiation attempt {negotiation_count + 1} exceeds merchant limit of {policy.max_negotiation_attempts}."
            )
        return PolicyResult.ok()

    if action == "CREATE_PAYMENT_PLAN":
        installment_count = int(parameters.get("installment_count", 1))
        period_days = int(parameters.get("period_days", 0))
        if period_days > policy.max_installment_period_days:
            return PolicyResult.blocked(
                f"Payment plan duration {period_days} days exceeds merchant maximum of {policy.max_installment_period_days} days."
            )
        if installment_count < 2:
            return PolicyResult.blocked("Payment plan must have at least 2 installments.")
        installment_amount = Decimal(str(parameters.get("installment_amount", 0)))
        if installment_amount < policy.min_payment_amount:
            return PolicyResult.blocked(
                f"Installment amount ₹{installment_amount} is below minimum payable amount ₹{policy.min_payment_amount}."
            )
        return PolicyResult.ok()

    if action in ("CREATE_PAYMENT_LINK", "RETRY", "ESCALATE"):
        # These actions do not require additional parameter checks beyond contact limits.
        return PolicyResult.ok()

    # Unknown actions are blocked by default — fail safe.
    return PolicyResult.blocked(f"Unknown action '{action}' is not permitted.")


def check_stopping_rules(
    policy: MerchantPolicy,
    context: dict[str, Any],
) -> PolicyResult:
    """
    Evaluates merchant-configured stopping rules.

    Stopping rules are stored as a list of condition dicts:
    [{"condition": "contact_count >= 5"}, ...]

    Currently supports simple threshold conditions.
    Complex rule expressions are intentionally NOT evaluated via eval().
    """
    rules = policy.stopping_rules or []
    contact_count = int(context.get("contact_count", 0))
    days_overdue = int(context.get("days_overdue", 0))

    for rule in rules:
        rule_type = rule.get("type", "")
        if rule_type == "max_days_overdue":
            if days_overdue > int(rule.get("value", 9999)):
                return PolicyResult.blocked(
                    f"Payment is {days_overdue} days overdue which exceeds the stopping rule threshold of {rule['value']} days."
                )
        elif rule_type == "max_contacts":
            if contact_count >= int(rule.get("value", 9999)):
                return PolicyResult.blocked(
                    f"Contact limit of {rule['value']} reached per stopping rule."
                )
    return PolicyResult.ok()
