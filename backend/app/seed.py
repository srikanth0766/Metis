from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select

from app.core.database import AsyncSessionLocal, engine
from app.models import (
    AgentRun, AgentRunStatus, Base, Customer, CustomerSegment, Experiment, ExperimentStatus,
    Intervention, InterventionStatus, InterventionType, Merchant, Payment, PaymentStatus,
    RecoveryCaseStatus, RecoveryOutcome, RecoveryStatus,
)
from app.services.experiment_service import assign_case_to_experiment
from app.services.optimizer_service import optimize_recovery_action
from app.services.prediction_service import get_all_predictions
from app.services.recovery_service import create_case_for_payment

DEMO_MERCHANT_NAME = "METIS Demo Merchant"


async def seed() -> None:
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with AsyncSessionLocal() as db:
        merchant = (await db.execute(select(Merchant).where(Merchant.name == DEMO_MERCHANT_NAME))).scalar_one_or_none()
        if merchant is not None:
            return
        merchant = Merchant(name=DEMO_MERCHANT_NAME, currency="INR", timezone="Asia/Kolkata")
        db.add(merchant)
        await db.flush()

        customers: list[Customer] = []
        segments = list(CustomerSegment)
        for index in range(50):
            customer = Customer(
                merchant_id=merchant.merchant_id,
                external_customer_id=f"demo_customer_{index + 1:03d}",
                name=f"Demo Customer {index + 1}",
                email=f"customer{index + 1}@example.test",
                phone=f"+9190000{index + 100:05d}",
                segment=segments[index % len(segments)],
            )
            db.add(customer)
            customers.append(customer)
        await db.flush()

        failed_payments: list[Payment] = []
        for index in range(100):
            failed = index < 30
            payment = Payment(
                merchant_id=merchant.merchant_id,
                customer_id=customers[index % len(customers)].customer_id,
                razorpay_payment_id=f"pay_demo_{index + 1:04d}",
                order_id=f"order_demo_{index + 1:04d}",
                amount=Decimal(1000 + (index % 10) * 750),
                currency="INR",
                payment_method=["upi", "card", "netbanking"][index % 3],
                status=PaymentStatus.FAILED if failed else PaymentStatus.CAPTURED,
                failure_reason="insufficient_funds" if failed else None,
                failed_at=datetime.now(timezone.utc) - timedelta(days=(index % 14) + 1) if failed else None,
            )
            db.add(payment)
            if failed:
                failed_payments.append(payment)
        await db.flush()

        cases = []
        for payment in failed_payments[:25]:
            case = await create_case_for_payment(db, payment.payment_id)
            await get_all_predictions(db, case.case_id)
            await optimize_recovery_action(db, case.case_id, merchant.merchant_id)
            cases.append(case)

        for case in cases[:6]:
            case.status = RecoveryCaseStatus.RECOVERED
            intervention = Intervention(
                case_id=case.case_id,
                type=InterventionType.PAYMENT_LINK,
                status=InterventionStatus.SUCCESS,
                actual_recovered_amount=case.revenue_at_risk,
                cost=Decimal("3.00"),
            )
            db.add(intervention)
            await db.flush()
            db.add(RecoveryOutcome(
                case_id=case.case_id,
                intervention_id=intervention.intervention_id,
                amount_recovered=case.revenue_at_risk,
                recovery_status=RecoveryStatus.FULL,
                recovery_time=datetime.now(timezone.utc),
                intervention_cost=Decimal("3.00"),
                concession_cost=Decimal("0.00"),
                net_recovered_amount=case.revenue_at_risk - Decimal("3.00"),
            ))

        experiment = Experiment(
            merchant_id=merchant.merchant_id,
            name="Payment plan uplift - September",
            description="Control versus assisted payment plan recovery.",
            status=ExperimentStatus.ACTIVE,
            start_at=datetime.now(timezone.utc) - timedelta(days=7),
        )
        db.add(experiment)
        await db.flush()
        for index, case in enumerate(cases[:15]):
            await assign_case_to_experiment(
                db,
                experiment.experiment_id,
                case.case_id,
                group_name="CONTROL" if index % 3 == 0 else "PAYMENT_PLAN",
                intervention_type=None if index % 3 == 0 else InterventionType.PAYMENT_PLAN,
            )
        db.add(AgentRun(
            case_id=cases[0].case_id,
            model_name="demo-negotiator",
            status=AgentRunStatus.COMPLETED,
            input_summary='[{"role":"user","content":"I need a little more time."}]',
            output_summary="A three-installment plan was offered within the merchant policy.",
            completed_at=datetime.now(timezone.utc),
        ))
        await db.commit()
        print(f"Seeded METIS demo merchant: {merchant.merchant_id}")


if __name__ == "__main__":
    asyncio.run(seed())
