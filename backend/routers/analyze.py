"""Router: POST /api/analyze/match + GET /api/analyze/status/{id}."""

import re
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models import AnalysisStatus, Club, Match, MatchAnalysis, PlanType
from backend.workers.tasks import analyze_match_task

PLAN_LIMITS = {
    PlanType.BASICO: 3,
    PlanType.PROFESIONAL: None,  # Unlimited
    PlanType.FEDERADO: None,     # Unlimited
}

router = APIRouter(prefix="/analyze", tags=["analyze"])

YOUTUBE_URL_REGEX = re.compile(
    r"^(https?://)?(www\.)?(youtube\.com/watch\?v=|youtu\.be/|youtube\.com/live/)[\w\-]{11}"
)


# --- Schemas ---


class AnalyzeMatchRequest(BaseModel):
    youtube_url: str
    equipo_local: str
    equipo_visitante: str
    competicion: str | None = None
    club_id: uuid.UUID

    @field_validator("youtube_url")
    @classmethod
    def validate_youtube_url(cls, v: str) -> str:
        if not YOUTUBE_URL_REGEX.match(v):
            raise ValueError(
                "URL de YouTube no válida. Usa el formato: "
                "https://www.youtube.com/watch?v=XXXXXXXXXXX"
            )
        return v


class AnalyzeMatchResponse(BaseModel):
    analysis_id: uuid.UUID
    status: str
    check_url: str


class AnalysisStatusResponse(BaseModel):
    analysis_id: uuid.UUID
    status: str
    progress_pct: int
    current_step: str | None
    estimated_remaining_seconds: int | None = None
    xg_local: float | None = None
    xg_visitante: float | None = None
    contenido_md: str | None = None
    pdf_url: str | None = None


# --- Endpoints ---


@router.post("/match", response_model=AnalyzeMatchResponse)
async def analyze_match(
    request: AnalyzeMatchRequest,
    db: AsyncSession = Depends(get_db),
):
    """Encola análisis de partido. Devuelve analysis_id inmediatamente."""

    # Check club exists and plan limits
    result = await db.execute(select(Club).where(Club.id == request.club_id))
    club = result.scalar_one_or_none()
    if not club:
        raise HTTPException(status_code=404, detail="Club no encontrado.")
    if not club.active:
        raise HTTPException(status_code=403, detail="La suscripción del club no está activa.")

    limit = PLAN_LIMITS.get(club.plan)
    if limit is not None and club.analisis_mes_actual >= limit:
        raise HTTPException(
            status_code=429,
            detail=f"Has alcanzado el límite de {limit} análisis/mes del plan {club.plan.value}. "
                   f"Actualiza a Profesional o Federado para análisis ilimitados.",
        )

    # Increment monthly counter
    club.analisis_mes_actual += 1

    # Create Match record
    match = Match(
        club_id=request.club_id,
        youtube_url=request.youtube_url,
        equipo_local=request.equipo_local,
        equipo_visitante=request.equipo_visitante,
        competicion=request.competicion,
    )
    db.add(match)
    await db.flush()

    # Create MatchAnalysis record (pending)
    analysis = MatchAnalysis(
        match_id=match.id,
        club_id=request.club_id,
        status=AnalysisStatus.PENDING,
        progress_pct=0,
        current_step="En cola de procesamiento",
    )
    db.add(analysis)
    await db.flush()

    # Enqueue Celery task
    analyze_match_task.delay(
        analysis_id=str(analysis.id),
        match_id=str(match.id),
        youtube_url=request.youtube_url,
        equipo_local=request.equipo_local,
        equipo_visitante=request.equipo_visitante,
        competicion=request.competicion,
        club_id=str(request.club_id),
    )

    return AnalyzeMatchResponse(
        analysis_id=analysis.id,
        status="pending",
        check_url=f"/api/analyze/status/{analysis.id}",
    )


@router.get("/status/{analysis_id}", response_model=AnalysisStatusResponse)
async def get_analysis_status(
    analysis_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Consulta el estado de un análisis en curso."""
    result = await db.execute(
        select(MatchAnalysis).where(MatchAnalysis.id == analysis_id)
    )
    analysis = result.scalar_one_or_none()

    if not analysis:
        raise HTTPException(
            status_code=404,
            detail="Análisis no encontrado. Verifica el analysis_id.",
        )

    response = AnalysisStatusResponse(
        analysis_id=analysis.id,
        status=analysis.status.value if isinstance(analysis.status, AnalysisStatus) else analysis.status,
        progress_pct=analysis.progress_pct,
        current_step=analysis.current_step,
    )

    if analysis.status == AnalysisStatus.DONE:
        response.xg_local = analysis.xg_local
        response.xg_visitante = analysis.xg_visitante
        response.contenido_md = analysis.contenido_md
        response.pdf_url = analysis.pdf_url

    return response
