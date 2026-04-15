"""Router: /api/clubs - CRUD + Auth JWT + Stripe checkout."""

import os
import uuid

import stripe
import structlog
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
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


# --- Club Dashboard (Story 6.1) ---


class ClubDashboardResponse(BaseModel):
    analyses_this_month: int
    analyses_total: int
    plan: str
    plan_limit: int | None
    usage_pct: int
    last_analysis_date: str | None


@router.get("/{club_id}/dashboard", response_model=ClubDashboardResponse)
async def get_club_dashboard(
    club_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Dashboard del club con métricas de uso."""
    from backend.models import MatchAnalysis, AnalysisStatus
    from sqlalchemy import func
    from datetime import datetime

    result = await db.execute(select(Club).where(Club.id == club_id))
    club = result.scalar_one_or_none()
    if not club:
        raise HTTPException(status_code=404, detail="Club no encontrado.")

    now = datetime.utcnow()
    first_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    month_count = await db.execute(
        select(func.count(MatchAnalysis.id))
        .where(MatchAnalysis.club_id == club_id)
        .where(MatchAnalysis.status == AnalysisStatus.DONE)
        .where(MatchAnalysis.created_at >= first_of_month)
    )
    analyses_this_month = month_count.scalar() or 0

    total_count = await db.execute(
        select(func.count(MatchAnalysis.id))
        .where(MatchAnalysis.club_id == club_id)
        .where(MatchAnalysis.status == AnalysisStatus.DONE)
    )
    analyses_total = total_count.scalar() or 0

    last_analysis = await db.execute(
        select(func.max(MatchAnalysis.created_at))
        .where(MatchAnalysis.club_id == club_id)
        .where(MatchAnalysis.status == AnalysisStatus.DONE)
    )
    last_date = last_analysis.scalar()

    plan_limits = {PlanType.BASICO: 3, PlanType.PROFESIONAL: None, PlanType.FEDERADO: None}
    plan_limit = plan_limits.get(club.plan)
    usage_pct = round((club.analisis_mes_actual / plan_limit) * 100) if plan_limit else 0

    return ClubDashboardResponse(
        analyses_this_month=analyses_this_month,
        analyses_total=analyses_total,
        plan=club.plan.value,
        plan_limit=plan_limit,
        usage_pct=usage_pct,
        last_analysis_date=last_date.isoformat() if last_date else None,
    )


# --- Sponsor Logo Upload (Story 6.2) ---


class SponsorLogoResponse(BaseModel):
    sponsor_logo_url: str | None


@router.post("/{club_id}/sponsor-logo", response_model=SponsorLogoResponse)
async def upload_sponsor_logo(
    club_id: uuid.UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Sube logo del patrocinador para incluir en PDFs."""
    result = await db.execute(select(Club).where(Club.id == club_id))
    club = result.scalar_one_or_none()
    if not club:
        raise HTTPException(status_code=404, detail="Club no encontrado.")

    # Validate format
    if not file.filename or not file.filename.lower().endswith((".png", ".jpg", ".jpeg")):
        raise HTTPException(status_code=422, detail="Formato no soportado. Usa PNG o JPG.")

    file_bytes = await file.read()
    if len(file_bytes) > 2 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="El logo no puede superar 2 MB.")

    # Upload to R2
    from backend.services.storage_service import upload_pdf as r2_upload
    import uuid as uuid_mod
    logo_key = f"logos/{club_id}/{uuid_mod.uuid4()}.{file.filename.rsplit('.', 1)[-1]}"
    logo_url = r2_upload(logo_key, file_bytes, file.content_type or "image/png")

    if not logo_url:
        raise HTTPException(status_code=500, detail="Error al subir el logo.")

    club.sponsor_logo_url = logo_url
    await db.commit()

    return SponsorLogoResponse(sponsor_logo_url=logo_url)


# --- Export Club Report PDF (Story 6.3) ---


@router.get("/{club_id}/export-pdf")
async def export_club_pdf(
    club_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Genera PDF resumen del club para asambleas."""
    from backend.models import MatchAnalysis, AnalysisStatus
    from backend.services.pdf_service import generate_pdf
    from fastapi.responses import StreamingResponse
    from sqlalchemy import func
    from datetime import datetime
    import io as io_mod

    result = await db.execute(select(Club).where(Club.id == club_id))
    club = result.scalar_one_or_none()
    if not club:
        raise HTTPException(status_code=404, detail="Club no encontrado.")

    total = await db.execute(
        select(func.count(MatchAnalysis.id))
        .where(MatchAnalysis.club_id == club_id)
        .where(MatchAnalysis.status == AnalysisStatus.DONE)
    )
    analyses_total = total.scalar() or 0

    avg_xg = await db.execute(
        select(func.avg(MatchAnalysis.xg_local))
        .where(MatchAnalysis.club_id == club_id)
        .where(MatchAnalysis.status == AnalysisStatus.DONE)
        .where(MatchAnalysis.xg_local.isnot(None))
    )
    avg = avg_xg.scalar()

    cost_total = await db.execute(
        select(func.sum(MatchAnalysis.cost_gemini) + func.sum(MatchAnalysis.cost_claude))
        .where(MatchAnalysis.club_id == club_id)
        .where(MatchAnalysis.status == AnalysisStatus.DONE)
    )
    total_cost = cost_total.scalar() or 0

    md = f"""# Informe de Actividad — {club.name}

## Resumen

- **Plan:** {club.plan.value}
- **Análisis realizados:** {analyses_total}
- **xG promedio local:** {round(avg, 2) if avg else 'N/A'}
- **Coste total plataforma:** {round(total_cost, 2)} EUR
- **ROI estimado:** El análisis táctico profesional equivaldría a {analyses_total * 200} EUR en servicios de consultoría

---

*Generado por RFAF Analytics Platform — {datetime.now().strftime('%d/%m/%Y')}*
"""

    pdf_bytes = generate_pdf(
        contenido_md=md,
        charts_json=None,
        equipo_local=club.name,
        equipo_visitante="Resumen",
        competicion=None,
        sponsor_logo_url=club.sponsor_logo_url,
    )

    filename = f"informe_{club.name.replace(' ', '_')}.pdf"
    return StreamingResponse(
        io_mod.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
