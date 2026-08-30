from decimal import Decimal
from types import SimpleNamespace

from app.policies.engine import validate_action


def policy():
    return SimpleNamespace(
        max_discount_percent=5.0,
        max_contacts=3,
        max_negotiation_attempts=2,
        min_payment_amount=Decimal("500"),
        max_installment_period_days=60,
        allowed_channels=["EMAIL", "SMS"],
        stopping_rules=[],
    )


def test_policy_blocks_discount_above_merchant_limit():
    result = validate_action("DISCOUNT", {"discount_percent": 6, "amount_after_discount": 1000}, policy())
    assert not result.allowed
    assert "exceeds" in result.reason


def test_policy_blocks_disallowed_channel():
    result = validate_action("CONTACT", {"channel": "WHATSAPP"}, policy(), contact_count=0)
    assert not result.allowed


def test_policy_allows_safe_payment_plan():
    result = validate_action("CREATE_PAYMENT_PLAN", {"installment_count": 3, "period_days": 60, "installment_amount": 750}, policy())
    assert result.allowed
