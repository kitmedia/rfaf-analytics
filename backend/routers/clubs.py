"""Router: /api/clubs - CRUD + Auth JWT + Stripe checkout."""

import os
import uuid

import stripe
import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models import Club, PlanType

logger = structlog.get_logger()
router = APIRouter(prefix="/clubs", tags=["clubs"])

STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")

# Stripe Price IDs (configure in Stripe Dashboard)
PLAN_PRICE_IDS = {
    PlanType.BASICO: os.getenv("STRIPE_PRICE_BASICO", "price_basico"),
    PlanType.PROFESIONAL: os.getenv("STRIPE_PRICE_PROFESIONAL", "price_profesional"),
    PlanType.FEDERADO: os.getenv("STRIPE_PRICE_FEDERADO", "price_federado"),
}


# --- Schemas ---


class ClubResponse(BaseModel):
    id: uuid.UUID
    name: str
    email: str
    plan: str
    analisis_mes_actual: int
    active: bool
    created_at: str


class ClubCreateRequest(BaseModel):
    name: str
    email: EmailStr
    plan: str = "BASICO"


class CheckoutRequest(BaseModel):
    plan: str
    success_url: str = "https://rfaf-analytics.es/dashboard?payment=success"
    cancel_url: str = "https://rfaf-analytics.es/dashboard?payment=cancel"


class CheckoutResponse(BaseModel):
    checkout_url: str
    session_id: str


# --- Endpoints ---


@router.get("/{club_id}", response_model=ClubResponse)
async def get_club(
    club_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Obtiene datos de un club."""
    result = await db.execute(select(Club).where(Club.id == club_id))
    club = result.scalar_one_or_none()

    if not club:
        raise HTTPException(status_code=404, detail="Club no encontrado.")

    return ClubResponse(
        id=club.id,
        name=club.name,
        email=club.email,
        plan=club.plan.value if isinstance(club.plan, PlanType) else club.plan,
        analisis_mes_actual=club.analisis_mes_actual,
        active=club.active,
        created_at=club.created_at.isoformat(),
    )


@router.post("", response_model=ClubResponse, status_code=201)
async def create_club(
    request: ClubCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Crea un nuevo club."""
    # Check duplicate email
    existing = await db.execute(select(Club).where(Club.email == request.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Ya existe un club con ese email.")

    try:
        plan = PlanType(request.plan)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Plan no válido. Opciones: {[p.value for p in PlanType]}",
        )

    club = Club(name=request.name, email=request.email, plan=plan)
    db.add(club)
    await db.flush()

    return ClubResponse(
        id=club.id,
        name=club.name,
        email=club.email,
        plan=club.plan.value,
        analisis_mes_actual=club.analisis_mes_actual,
        active=club.active,
        created_at=club.created_at.isoformat(),
    )


class PortalResponse(BaseModel):
    portal_url: str


@router.post("/{club_id}/portal", response_model=PortalResponse)
async def create_portal_session(
    club_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Crea una sesión del portal de facturación de Stripe (PAY-03).

    Permite al club gestionar su suscripción, métodos de pago y facturas.
    """
    if not STRIPE_SECRET_KEY:
        raise HTTPException(status_code=500, detail="Stripe no configurado.")

    stripe.api_key = STRIPE_SECRET_KEY

    result = await db.execute(select(Club).where(Club.id == club_id))
    club = result.scalar_one_or_none()
    if not club:
        raise HTTPException(status_code=404, detail="Club no encontrado.")

    if not club.stripe_customer_id:
        raise HTTPException(
            status_code=400,
            detail="El club no tiene una suscripción activa en Stripe.",
        )

    try:
        session = stripe.billing_portal.Session.create(
            customer=club.stripe_customer_id,
            return_url=os.getenv(
                "STRIPE_PORTAL_RETURN_URL",
                "https://rfaf-analytics.es/dashboard",
            ),
        )
    except stripe.error.StripeError as e:
        logger.error("stripe_portal_error", club_id=str(club_id), error=str(e))
        raise HTTPException(status_code=502, detail="Error al crear el portal de facturación.")

    return PortalResponse(portal_url=session.url)


@router.post("/{club_id}/checkout", response_model=CheckoutResponse)
async def create_checkout_session(
    club_id: uuid.UUID,
    request: CheckoutRequest,
    db: AsyncSession = Depends(get_db),
):
    """Crea una sesión de Stripe Checkout para el club."""
    if not STRIPE_SECRET_KEY:
        raise HTTPException(status_code=500, detail="Stripe no configurado.")

    stripe.api_key = STRIPE_SECRET_KEY

    result = await db.execute(select(Club).where(Club.id == club_id))
    club = result.scalar_one_or_none()
    if not club:
        raise HTTPException(status_code=404, detail="Club no encontrado.")

    try:
        plan = PlanType(request.plan)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Plan no válido. Opciones: {[p.value for p in PlanType]}",
        )

    price_id = PLAN_PRICE_IDS.get(plan)

    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            mode="subscription",
            line_items=[{"price": price_id, "quantity": 1}],
            metadata={"club_id": str(club_id), "plan": plan.value},
            customer_email=club.email,
            success_url=request.success_url,
            cancel_url=request.cancel_url,
        )
    except stripe.error.StripeError as e:
        logger.error("stripe_checkout_error", club_id=str(club_id), error=str(e))
        raise HTTPException(status_code=502, detail="Error al crear la sesión de pago.")

    return CheckoutResponse(checkout_url=session.url, session_id=session.id)
