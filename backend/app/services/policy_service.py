"""
Merchant policy helpers.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import AuditActorType, InteractionChannel, MerchantPolicy
from app.schemas.schemas import MerchantPolicyUpdate
from app.services.audit_service import write_audit_log

_DEFAULT_ALLOWED_CHANNELS = [
    InteractionChannel.EMAIL.value,
    InteractionChannel.SMS.value,
    InteractionChannel.WHATSAPP.value,
]


def _serialize_policy(policy: MerchantPolicy) -> dict[str, Any]:
    return {
        "policy_id": policy.policy_id,
        "merchant_id": policy.merchant_id,
        "max_discount_percent": policy.max_discount_percent,
        "max_contacts": policy.max_contacts,
        "max_negotiation_attempts": policy.max_negotiation_attempts,
        "min_payment_amount": float(policy.min_payment_amount),
        "max_installment_period_days": policy.max_installment_period_days,
        "allowed_channels": [
            channel if isinstance(channel, str) else channel.value
            for channel in (policy.allowed_channels or [])
        ],
        "stopping_rules": policy.stopping_rules,
    }


async def get_policy_object(db: AsyncSession, merchant_id: str) -> MerchantPolicy:
    """Fetch a merchant policy, creating a default one if it does not exist yet."""
    result = await db.execute(
        select(MerchantPolicy).where(MerchantPolicy.merchant_id == merchant_id)
    )
    policy = result.scalar_one_or_none()
    if policy is not None:
        return policy

    policy = MerchantPolicy(
        merchant_id=merchant_id,
        max_discount_percent=5.0,
        max_contacts=3,
        max_negotiation_attempts=2,
        min_payment_amount=Decimal("500.00"),
        max_installment_period_days=60,
        allowed_channels=list(_DEFAULT_ALLOWED_CHANNELS),
        stopping_rules=[],
    )
    db.add(policy)
    await db.flush()
    return policy


async def get_policy_dict(db: AsyncSession, merchant_id: str) -> dict[str, Any]:
    """Return a serializable policy representation."""
    policy = await get_policy_object(db, merchant_id)
    return _serialize_policy(policy)


async def update_policy(
    db: AsyncSession,
    merchant_id: str,
    payload: MerchantPolicyUpdate,
    *,
    actor_id: str | None = None,
) -> MerchantPolicy:
    """Update the merchant policy and emit an audit record."""
    policy = await get_policy_object(db, merchant_id)
    before_state = _serialize_policy(policy)

    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        if field == "allowed_channels" and value is not None:
            setattr(policy, field, [item.value if hasattr(item, "value") else item for item in value])
            continue
        setattr(policy, field, value)

    await db.flush()

    await write_audit_log(
        db,
        action="merchant_policy.updated",
        actor_type=AuditActorType.MERCHANT,
        actor_id=actor_id,
        merchant_id=merchant_id,
        before_state=before_state,
        after_state=_serialize_policy(policy),
    )
    return policy
