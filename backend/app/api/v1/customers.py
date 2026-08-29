from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.common import not_found
from app.core.database import get_db
from app.models.models import Customer
from app.schemas.schemas import CustomerCreate, CustomerRead

router = APIRouter(prefix="/customers", tags=["customers"])


@router.post("", response_model=CustomerRead, status_code=201)
async def create_or_update_customer(payload: CustomerCreate, db: AsyncSession = Depends(get_db)) -> Customer:
    query = select(Customer).where(Customer.merchant_id == payload.merchant_id)
    if payload.external_customer_id:
        query = query.where(Customer.external_customer_id == payload.external_customer_id)
    else:
        query = query.where(Customer.email == payload.email).where(Customer.phone == payload.phone)
    customer = (await db.execute(query)).scalar_one_or_none()
    values = payload.model_dump()
    if customer is None:
        customer = Customer(**values)
        db.add(customer)
    else:
        for key, value in values.items():
            setattr(customer, key, value)
    await db.flush()
    await db.refresh(customer)
    return customer


@router.get("", response_model=list[CustomerRead])
async def list_customers(
    merchant_id: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> list[Customer]:
    query = select(Customer)
    if merchant_id:
        query = query.where(Customer.merchant_id == merchant_id)
    result = await db.execute(query.order_by(Customer.created_at.asc()))
    return list(result.scalars().all())


@router.get("/{customer_id}", response_model=CustomerRead)
async def get_customer(customer_id: str, db: AsyncSession = Depends(get_db)) -> Customer:
    customer = await db.get(Customer, customer_id)
    if customer is None:
        raise not_found("Customer")
    return customer
