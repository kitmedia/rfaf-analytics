"""Router: /api/federation — dashboard federativo con métricas agregadas."""

import uuid
from datetime import datetime, timedelta

import structlog
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models import AnalysisStatus, Club, FederationConvention, MatchAnalysis, PlanType

logger = structlog.get_logger()

router = APIRouter(prefix="/federation", tags=["federation"])


class FederationDashboard(BaseModel):
    total_clubs: int
    active_clubs: int
    analyses_this_month: int
    analyses_total: int
    avg_xg_local: float | None
    avg_xg_visitante: float | None


@router.get("/dashboard", response_model=FederationDashboard)
async def get_federation_dashboard(
    db: AsyncSession = Depends(get_db),
):
    """Dashboard federativo con métricas agregadas. Solo datos agregados, nunca individuales."""
    now = datetime.utcnow()
    first_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # Club counts (federado only)
    total = await db.execute(
        select(func.count(Club.id)).where(Club.plan == PlanType.FEDERADO)
    )
    total_clubs = total.scalar() or 0

    active = await db.execute(
        select(func.count(Club.id))
        .where(Club.plan == PlanType.FEDERADO)
        .where(Club.active == True)  # noqa: E712
    )
    active_clubs = active.scalar() or 0

    # Analyses counts
    analyses_month = await db.execute(
        select(func.count(MatchAnalysis.id))
        .join(Club, MatchAnalysis.club_id == Club.id)
        .where(Club.plan == PlanType.FEDERADO)
        .where(MatchAnalysis.status == AnalysisStatus.DONE)
        .where(MatchAnalysis.created_at >= first_of_month)
    )
    analyses_this_month = analyses_month.scalar() or 0

    analyses_all = await db.execute(
        select(func.count(MatchAnalysis.id))
        .join(Club, MatchAnalysis.club_id == Club.id)
        .where(Club.plan == PlanType.FEDERADO)
        .where(MatchAnalysis.status == AnalysisStatus.DONE)
    )
    analyses_total = analyses_all.scalar() or 0

    # Average xG (aggregated)
    avg_xg = await db.execute(
        select(
            func.avg(MatchAnalysis.xg_local),
            func.avg(MatchAnalysis.xg_visitante),
        )
        .join(Club, MatchAnalysis.club_id == Club.id)
        .where(Club.plan == PlanType.FEDERADO)
        .where(MatchAnalysis.status == AnalysisStatus.DONE)
        .where(MatchAnalysis.xg_local.isnot(None))
    )
    xg_row = avg_xg.one()

@router.get("/export-pdf")
async def export_federation_pdf(
    db: AsyncSession = Depends(get_db),
):
    """Genera PDF con resumen ejecutivo federativo."""
    from backend.services.pdf_service import generate_pdf
    from fastapi.responses import StreamingResponse
    import io

    # Build markdown summary
    dashboard = await get_federation_dashboard(db)

    md = f"""# Informe Federativo - RFAF Analytics

## Resumen Ejecutivo

- **Clubes federados:** {dashboard.total_clubs} ({dashboard.active_clubs} activos)
- **Análisis este mes:** {dashboard.analyses_this_month}
- **Análisis totales:** {dashboard.analyses_total}

## Métricas Agregadas

| Métrica | Valor |
|---------|-------|
| xG Local promedio | {dashboard.avg_xg_local or 'N/A'} |
| xG Visitante promedio | {dashboard.avg_xg_visitante or 'N/A'} |

---

*Generado automáticamente por RFAF Analytics Platform*
"""

    pdf_bytes = generate_pdf(
        contenido_md=md,
        charts_json=None,
        equipo_local="RFAF",
        equipo_visitante="Federación",
        competicion=None,
    )

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="informe_federativo.pdf"'},
    )


    return FederationDashboard(
        total_clubs=total_clubs,
        active_clubs=active_clubs,
        analyses_this_month=analyses_this_month,
        analyses_total=analyses_total,
        avg_xg_local=round(xg_row[0], 2) if xg_row[0] else None,
        avg_xg_visitante=round(xg_row[1], 2) if xg_row[1] else None,
    )


# --- Convention Management (Story 5.3) ---


class ConventionCreate(BaseModel):
    federation_name: str
    discount_code: str
    discount_pct: int = 30
    start_date: str
    end_date: str
    contact_email: str | None = None


class ConventionOut(BaseModel):
    id: uuid.UUID
    federation_name: str
    discount_code: str
    discount_pct: int
    start_date: str
    end_date: str
    contact_email: str | None
    active: bool
    clubs_count: int


@router.get("/conventions", response_model=list[ConventionOut])
async def list_conventions(db: AsyncSession = Depends(get_db)):
    """Lista todos los convenios federativos."""
    result = await db.execute(select(FederationConvention).order_by(FederationConvention.created_at.desc()))
    conventions = result.scalars().all()

    out = []
    for c in conventions:
        clubs_count_result = await db.execute(
            select(func.count(Club.id)).where(Club.federation_convention_id == c.id)
        )
        out.append(ConventionOut(
            id=c.id,
            federation_name=c.federation_name,
            discount_code=c.discount_code,
            discount_pct=c.discount_pct,
            start_date=c.start_date.isoformat(),
            end_date=c.end_date.isoformat(),
            contact_email=c.contact_email,
            active=c.active,
            clubs_count=clubs_count_result.scalar() or 0,
        ))
    return out


@router.post("/conventions", response_model=ConventionOut)
async def create_convention(
    request: ConventionCreate,
    db: AsyncSession = Depends(get_db),
):
    """Crea un nuevo convenio federativo."""
    from fastapi import HTTPException

    convention = FederationConvention(
        federation_name=request.federation_name,
        discount_code=request.discount_code,
        discount_pct=request.discount_pct,
        start_date=datetime.fromisoformat(request.start_date),
        end_date=datetime.fromisoformat(request.end_date),
        contact_email=request.contact_email,
    )
    db.add(convention)
    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise HTTPException(status_code=409, detail="El código de descuento ya existe.")

    await db.refresh(convention)

    logger.info("convention_created", federation=request.federation_name, code=request.discount_code)

    return ConventionOut(
        id=convention.id,
        federation_name=convention.federation_name,
        discount_code=convention.discount_code,
        discount_pct=convention.discount_pct,
        start_date=convention.start_date.isoformat(),
        end_date=convention.end_date.isoformat(),
        contact_email=convention.contact_email,
        active=convention.active,
        clubs_count=0,
    )


# --- Convention Validation for Signup (Story 5.4) ---


class ValidateCodeResponse(BaseModel):
    valid: bool
    federation_name: str | None = None
    discount_pct: int | None = None


@router.get("/validate-code/{code}", response_model=ValidateCodeResponse)
async def validate_convention_code(
    code: str,
    db: AsyncSession = Depends(get_db),
):
    """Valida un código de convenio federativo para signup."""
    result = await db.execute(
        select(FederationConvention)
        .where(FederationConvention.discount_code == code)
        .where(FederationConvention.active == True)  # noqa: E712
        .where(FederationConvention.end_date >= datetime.utcnow())
    )
    convention = result.scalar_one_or_none()

    if not convention:
        return ValidateCodeResponse(valid=False)

    return ValidateCodeResponse(
        valid=True,
        federation_name=convention.federation_name,
        discount_pct=convention.discount_pct,
    )


# --- Channel Metrics (Story 5.5) ---


class ChannelMetrics(BaseModel):
    channel: str
    club_count: int
    active_count: int
    total_analyses: int
    avg_analyses_per_club: float


@router.get("/channel-metrics", response_model=list[ChannelMetrics])
async def get_channel_metrics(db: AsyncSession = Depends(get_db)):
    """Métricas diferenciadas por canal de adquisición."""
    channels = ["federativo", "direct"]

    metrics = []
    for channel in channels:
        if channel == "federativo":
            club_filter = Club.acquisition_channel == "federativo"
        else:
            club_filter = (Club.acquisition_channel == "direct") | (Club.acquisition_channel.is_(None))

        club_count = await db.execute(select(func.count(Club.id)).where(club_filter))
        active_count = await db.execute(
            select(func.count(Club.id)).where(club_filter).where(Club.active == True)  # noqa: E712
        )
        analyses_count = await db.execute(
            select(func.count(MatchAnalysis.id))
            .join(Club, MatchAnalysis.club_id == Club.id)
            .where(club_filter)
            .where(MatchAnalysis.status == AnalysisStatus.DONE)
        )

        total_clubs = club_count.scalar() or 0
        total_analyses = analyses_count.scalar() or 0

        metrics.append(ChannelMetrics(
            channel=channel,
            club_count=total_clubs,
            active_count=active_count.scalar() or 0,
            total_analyses=total_analyses,
            avg_analyses_per_club=round(total_analyses / total_clubs, 1) if total_clubs > 0 else 0,
        ))

    return metrics
