"""Router: /api/webhooks - Stripe webhooks (idempotente)."""

import os
import uuid

import stripe
import structlog
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models import Club, PlanType
from backend.services.tracking_service import track_club_cancelled, track_club_subscribed

logger = structlog.get_logger()
router = APIRouter(prefix="/webhooks", tags=["webhooks"])

STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")


@router.post("/stripe")
async def stripe_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Handle Stripe webhooks. Idempotent by design."""
    if not STRIPE_SECRET_KEY or not STRIPE_WEBHOOK_SECRET:
        raise HTTPException(status_code=500, detail="Stripe no configurado.")

    stripe.api_key = STRIPE_SECRET_KEY
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Firma de webhook inválida.")

    event_type = event["type"]
    data = event["data"]["object"]

    logger.info("stripe_webhook_received", event_type=event_type, event_id=event["id"])

    if event_type == "checkout.session.completed":
        await _handle_checkout_completed(data, db)
    elif event_type == "invoice.payment_succeeded":
        await _handle_invoice_paid(data, db)
    elif event_type == "customer.subscription.deleted":
        await _handle_subscription_deleted(data, db)
    else:
        logger.info("stripe_webhook_ignored", event_type=event_type)

    return {"status": "ok"}


async def _handle_checkout_completed(data: dict, db: AsyncSession):
    """Activate subscription after successful checkout."""
    metadata = data.get("metadata", {})
    club_id = metadata.get("club_id")
    plan = metadata.get("plan")
    customer_id = data.get("customer")

    if not club_id:
        logger.warning("stripe_webhook_no_club_id", session_id=data.get("id"))
        return

    try:
        plan_type = PlanType(plan)
    except (ValueError, KeyError):
        plan_type = PlanType.BASICO

    await db.execute(
        update(Club)
        .where(Club.id == uuid.UUID(club_id))
        .values(
            plan=plan_type,
            stripe_customer_id=customer_id,
            active=True,
        )
    )

    PLAN_PRICES = {"basico": 49.0, "profesional": 149.0, "federado": 104.0}
    mrr = PLAN_PRICES.get(plan_type.value, 0.0)
    track_club_subscribed(club_id=club_id, plan=plan_type.value, mrr_eur=mrr)

    logger.info(
        "stripe_subscription_activated",
        club_id=club_id,
        plan=plan_type.value,
        customer_id=customer_id,
    )


async def _handle_invoice_paid(data: dict, db: AsyncSession):
    """Reset monthly analysis counter on successful payment."""
    customer_id = data.get("customer")
    if not customer_id:
        return

    result = await db.execute(
        select(Club).where(Club.stripe_customer_id == customer_id)
    )
    club = result.scalar_one_or_none()
    if not club:
        logger.warning("stripe_invoice_unknown_customer", customer_id=customer_id)
        return

    # Reset monthly counter (idempotent — setting to 0 is safe to repeat)
    await db.execute(
        update(Club)
        .where(Club.id == club.id)
        .values(analisis_mes_actual=0, active=True)
    )

    logger.info(
        "stripe_invoice_paid_reset",
        club_id=str(club.id),
        club_name=club.name,
    )


async def _handle_subscription_deleted(data: dict, db: AsyncSession):
    """Downgrade to Básico on subscription cancellation."""
    customer_id = data.get("customer")
    if not customer_id:
        return

    result = await db.execute(
        select(Club).where(Club.stripe_customer_id == customer_id)
    )
    club = result.scalar_one_or_none()
    if not club:
        return

    await db.execute(
        update(Club)
        .where(Club.id == club.id)
        .values(plan=PlanType.BASICO, active=True)
    )

    track_club_cancelled(
        club_id=str(club.id),
        plan=club.plan.value if hasattr(club.plan, "value") else str(club.plan),
    )

    logger.info(
        "stripe_subscription_cancelled",
        club_id=str(club.id),
        club_name=club.name,
        downgraded_to="BASICO",
    )
