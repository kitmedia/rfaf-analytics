"""Router: GET /api/reports - listar y obtener informes."""

import os
import uuid

import anthropic
import structlog
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from pydantic import BaseModel
from sqlalchemy import select, func as sa_func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models import AnalysisStatus, Match, MatchAnalysis, Player, ScoutReport, ScoutType
from backend.services.pdf_service import generate_pdf
from backend.services.tracking_service import (
    track_chatbot_query,
    track_pdf_downloaded,
    track_report_viewed,
)

logger = structlog.get_logger()

router = APIRouter(prefix="/reports", tags=["reports"])
limiter = Limiter(key_func=get_remote_address)


# --- Schemas ---


class ReportSummary(BaseModel):
    analysis_id: uuid.UUID
    equipo_local: str
    equipo_visitante: str
    competicion: str | None
    status: str
    xg_local: float | None
    xg_visitante: float | None
    created_at: str


class ReportDetail(BaseModel):
    analysis_id: uuid.UUID
    equipo_local: str
    equipo_visitante: str
    competicion: str | None
    status: str
    xg_local: float | None
    xg_visitante: float | None
    contenido_md: str | None
    charts_json: dict | None
    training_plan_json: dict | None
    sections_available: dict | None
    cost_gemini: float | None
    cost_claude: float | None
    duration_s: float | None
    created_at: str


class TrendWeek(BaseModel):
    week: str
    xg_local: float
    xg_visitante: float
    match_count: int


class TrendsResponse(BaseModel):
    has_enough_data: bool
    weeks: list[TrendWeek]


@router.get("/trends", response_model=TrendsResponse)
async def get_trends(
    club_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Devuelve tendencias de métricas del club (últimas 8 semanas)."""
    from datetime import datetime, timedelta

    eight_weeks_ago = datetime.now() - timedelta(weeks=8)

    result = await db.execute(
        select(
            MatchAnalysis.xg_local,
            MatchAnalysis.xg_visitante,
            MatchAnalysis.created_at,
        )
        .where(MatchAnalysis.club_id == club_id)
        .where(MatchAnalysis.status == AnalysisStatus.DONE)
        .where(MatchAnalysis.xg_local.isnot(None))
        .where(MatchAnalysis.created_at >= eight_weeks_ago)
        .order_by(MatchAnalysis.created_at.asc())
    )
    rows = result.all()

    if len(rows) < 3:
        return TrendsResponse(has_enough_data=False, weeks=[])

    # Group by ISO week
    weeks_data: dict[str, list[tuple[float, float]]] = {}
    for xg_l, xg_v, created in rows:
        week_num = created.isocalendar()[1]
        week_key = f"Sem {week_num}"
        if week_key not in weeks_data:
            weeks_data[week_key] = []
        weeks_data[week_key].append((xg_l or 0, xg_v or 0))

    weeks = []
    for week_key, values in weeks_data.items():
        avg_local = round(sum(v[0] for v in values) / len(values), 2)
        avg_visit = round(sum(v[1] for v in values) / len(values), 2)
        weeks.append(TrendWeek(
            week=week_key,
            xg_local=avg_local,
            xg_visitante=avg_visit,
            match_count=len(values),
        ))

    return TrendsResponse(has_enough_data=True, weeks=weeks)


# --- Endpoints ---


@router.get("", response_model=list[ReportSummary])
async def list_reports(
    club_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Lista todos los informes de un club."""
    result = await db.execute(
        select(MatchAnalysis, Match)
        .join(Match, MatchAnalysis.match_id == Match.id)
        .where(MatchAnalysis.club_id == club_id)
        .order_by(MatchAnalysis.created_at.desc())
    )
    rows = result.all()

    return [
        ReportSummary(
            analysis_id=analysis.id,
            equipo_local=match.equipo_local,
            equipo_visitante=match.equipo_visitante,
            competicion=match.competicion,
            status=analysis.status.value if isinstance(analysis.status, AnalysisStatus) else analysis.status,
            xg_local=analysis.xg_local,
            xg_visitante=analysis.xg_visitante,
            created_at=analysis.created_at.isoformat(),
        )
        for analysis, match in rows
    ]


@router.get("/{analysis_id}", response_model=ReportDetail)
async def get_report(
    analysis_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Obtiene un informe completo por ID."""
    result = await db.execute(
        select(MatchAnalysis, Match)
        .join(Match, MatchAnalysis.match_id == Match.id)
        .where(MatchAnalysis.id == analysis_id)
    )
    row = result.one_or_none()

    if not row:
        raise HTTPException(status_code=404, detail="Informe no encontrado.")

    analysis, match = row

    if analysis.status == AnalysisStatus.DONE:
        track_report_viewed(
            club_id=str(analysis.club_id),
            analysis_id=str(analysis.id),
        )

    return ReportDetail(
        analysis_id=analysis.id,
        equipo_local=match.equipo_local,
        equipo_visitante=match.equipo_visitante,
        competicion=match.competicion,
        status=analysis.status.value if isinstance(analysis.status, AnalysisStatus) else analysis.status,
        xg_local=analysis.xg_local,
        xg_visitante=analysis.xg_visitante,
        contenido_md=analysis.contenido_md,
        charts_json=analysis.charts_json,
        training_plan_json=analysis.training_plan_json,
        sections_available=analysis.sections_available,
        cost_gemini=analysis.cost_gemini,
        cost_claude=analysis.cost_claude,
        duration_s=analysis.duration_s,
        created_at=analysis.created_at.isoformat(),
    )


@router.get("/{analysis_id}/pdf")
async def download_report_pdf(
    analysis_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Descarga el informe en formato PDF."""
    result = await db.execute(
        select(MatchAnalysis, Match)
        .join(Match, MatchAnalysis.match_id == Match.id)
        .where(MatchAnalysis.id == analysis_id)
    )
    row = result.one_or_none()

    if not row:
        raise HTTPException(status_code=404, detail="Informe no encontrado.")

    analysis, match = row

    if analysis.status != AnalysisStatus.DONE:
        raise HTTPException(
            status_code=400,
            detail="El informe aún no está completado. Estado actual: "
                   + (analysis.status.value if isinstance(analysis.status, AnalysisStatus) else str(analysis.status)),
        )

    if not analysis.contenido_md:
        raise HTTPException(status_code=400, detail="El informe no tiene contenido.")

    track_pdf_downloaded(
        club_id=str(analysis.club_id),
        analysis_id=str(analysis_id),
    )

    pdf_bytes = generate_pdf(
        contenido_md=analysis.contenido_md,
        charts_json=analysis.charts_json,
        equipo_local=match.equipo_local,
        equipo_visitante=match.equipo_visitante,
        competicion=match.competicion,
    )

    filename = f"informe_{match.equipo_local}_vs_{match.equipo_visitante}.pdf".replace(" ", "_")

    import io
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


class TrainingPlanRequest(BaseModel):
    club_id: uuid.UUID


class TrainingPlanResponse(BaseModel):
    analysis_id: uuid.UUID
    status: str
    detail: str


@router.post("/{analysis_id}/training-plan", response_model=TrainingPlanResponse)
@limiter.limit("5/minute")
async def generate_training_plan(
    analysis_id: uuid.UUID,
    request: TrainingPlanRequest,
    req: Request,
    db: AsyncSession = Depends(get_db),
):
    """Encola generación de plan de entrenamiento (P3) para un análisis completado."""
    result = await db.execute(
        select(MatchAnalysis)
        .where(MatchAnalysis.id == analysis_id)
        .where(MatchAnalysis.club_id == request.club_id)
    )
    analysis = result.scalar_one_or_none()

    if not analysis:
        raise HTTPException(status_code=404, detail="Análisis no encontrado.")

    if analysis.status != AnalysisStatus.DONE:
        raise HTTPException(
            status_code=400,
            detail="El análisis táctico aún no está completado. Espera a que finalice el informe P0.",
        )

    if analysis.training_plan_json is not None:
        raise HTTPException(
            status_code=409,
            detail="El plan de entrenamiento ya fue generado para este análisis.",
        )

    from backend.workers.tasks import generate_training_plan_task

    generate_training_plan_task.delay(
        analysis_id=str(analysis_id),
        club_id=str(request.club_id),
    )

    logger.info(
        "training_plan_enqueued",
        analysis_id=str(analysis_id),
        club_id=str(request.club_id),
    )

    return TrainingPlanResponse(
        analysis_id=analysis_id,
        status="pending",
        detail="Plan de entrenamiento en cola de generación.",
    )


# --- Scouting (P2) ---


class ScoutRequest(BaseModel):
    club_id: uuid.UUID
    player_id: uuid.UUID


class ScoutResponse(BaseModel):
    scout_report_id: uuid.UUID
    status: str
    detail: str


class ScoutReportDetail(BaseModel):
    id: uuid.UUID
    player_name: str
    player_number: int | None
    status: str
    contenido_md: str | None
    cost_eur: float | None
    created_at: str


@router.post("/{analysis_id}/scout", response_model=ScoutResponse)
@limiter.limit("5/minute")
async def generate_scout(
    analysis_id: uuid.UUID,
    request: ScoutRequest,
    req: Request,
    db: AsyncSession = Depends(get_db),
):
    """Encola generación de informe de scouting (P2) para un jugador."""
    # RLS: analysis belongs to club
    result = await db.execute(
        select(MatchAnalysis)
        .where(MatchAnalysis.id == analysis_id)
        .where(MatchAnalysis.club_id == request.club_id)
    )
    analysis = result.scalar_one_or_none()
    if not analysis:
        raise HTTPException(status_code=404, detail="Análisis no encontrado.")

    if analysis.status != AnalysisStatus.DONE:
        raise HTTPException(status_code=400, detail="El análisis táctico aún no está completado.")

    # RLS: player belongs to club
    player_result = await db.execute(
        select(Player)
        .where(Player.id == request.player_id)
        .where(Player.club_id == request.club_id)
    )
    player = player_result.scalar_one_or_none()
    if not player:
        raise HTTPException(status_code=404, detail="Jugador no encontrado.")

    # Idempotency: check existing scout report
    existing = await db.execute(
        select(ScoutReport)
        .where(ScoutReport.analysis_id == analysis_id)
        .where(ScoutReport.player_id == request.player_id)
        .where(ScoutReport.club_id == request.club_id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Ya existe un informe de scouting para este jugador y análisis.")

    # Create ScoutReport
    scout = ScoutReport(
        club_id=request.club_id,
        player_id=request.player_id,
        analysis_id=analysis_id,
        scout_type=ScoutType.PLAYER_SCOUT,
        status=AnalysisStatus.PENDING,
    )
    db.add(scout)
    await db.commit()
    await db.refresh(scout)

    from backend.workers.tasks import generate_scout_report_task

    generate_scout_report_task.delay(
        scout_report_id=str(scout.id),
        analysis_id=str(analysis_id),
        player_id=str(request.player_id),
        club_id=str(request.club_id),
    )

    logger.info(
        "scout_report_enqueued",
        scout_report_id=str(scout.id),
        analysis_id=str(analysis_id),
        player_id=str(request.player_id),
        club_id=str(request.club_id),
    )

    return ScoutResponse(
        scout_report_id=scout.id,
        status="pending",
        detail="Informe de scouting en cola de generación.",
    )


@router.get("/scout/{scout_report_id}", response_model=ScoutReportDetail)
async def get_scout_report(
    scout_report_id: uuid.UUID,
    club_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Obtiene un informe de scouting por ID."""
    result = await db.execute(
        select(ScoutReport, Player)
        .outerjoin(Player, ScoutReport.player_id == Player.id)
        .where(ScoutReport.id == scout_report_id)
        .where(ScoutReport.club_id == club_id)
    )
    row = result.one_or_none()

    if not row:
        raise HTTPException(status_code=404, detail="Informe de scouting no encontrado.")

    scout, player = row

    return ScoutReportDetail(
        id=scout.id,
        player_name=player.name if player else "Desconocido",
        player_number=player.shirt_number if player else None,
        status=scout.status.value if isinstance(scout.status, AnalysisStatus) else scout.status,
        contenido_md=scout.contenido_md,
        cost_eur=scout.cost_eur,
        created_at=scout.created_at.isoformat(),
    )


@router.get("/scout/{scout_report_id}/pdf")
async def download_scout_pdf(
    scout_report_id: uuid.UUID,
    club_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Descarga informe de scouting en formato PDF."""
    result = await db.execute(
        select(ScoutReport, Player)
        .outerjoin(Player, ScoutReport.player_id == Player.id)
        .where(ScoutReport.id == scout_report_id)
        .where(ScoutReport.club_id == club_id)
    )
    row = result.one_or_none()

    if not row:
        raise HTTPException(status_code=404, detail="Informe de scouting no encontrado.")

    scout, player = row

    if scout.status != AnalysisStatus.DONE:
        raise HTTPException(
            status_code=400,
            detail="El informe de scouting aún no está completado.",
        )

    if not scout.contenido_md:
        raise HTTPException(status_code=400, detail="El informe no tiene contenido.")

    player_name = player.name if player else "Jugador"

    pdf_bytes = generate_pdf(
        contenido_md=scout.contenido_md,
        charts_json=None,
        equipo_local=player_name,
        equipo_visitante="Scouting",
        competicion=None,
    )

    filename = f"scouting_{player_name.replace(' ', '_')}.pdf"

    import io
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


class RetrySectionRequest(BaseModel):
    club_id: uuid.UUID
    section: str  # "extraction" | "narrative" | "charts" | "pdf"


class RetrySectionResponse(BaseModel):
    analysis_id: uuid.UUID
    section: str
    status: str


@router.post("/{analysis_id}/retry-section", response_model=RetrySectionResponse)
async def retry_section(
    analysis_id: uuid.UUID,
    request: RetrySectionRequest,
    db: AsyncSession = Depends(get_db),
):
    """Reintenta una sección específica del pipeline que falló."""
    valid_sections = {"extraction", "narrative", "charts", "pdf"}
    if request.section not in valid_sections:
        raise HTTPException(status_code=422, detail=f"Sección no válida. Usa: {', '.join(valid_sections)}")

    result = await db.execute(
        select(MatchAnalysis)
        .where(MatchAnalysis.id == analysis_id)
        .where(MatchAnalysis.club_id == request.club_id)
    )
    analysis = result.scalar_one_or_none()

    if not analysis:
        raise HTTPException(status_code=404, detail="Análisis no encontrado.")

    if analysis.status != AnalysisStatus.DONE:
        raise HTTPException(status_code=400, detail="El análisis debe estar completado para reintentar secciones.")

    sections = analysis.sections_available or {}
    if sections.get(request.section) is True:
        raise HTTPException(status_code=400, detail=f"La sección '{request.section}' ya está disponible.")

    from backend.workers.tasks import retry_section_task

    retry_section_task.delay(
        analysis_id=str(analysis_id),
        section=request.section,
        club_id=str(request.club_id),
    )

    logger.info(
        "retry_section_enqueued",
        analysis_id=str(analysis_id),
        section=request.section,
        club_id=str(request.club_id),
    )

    return RetrySectionResponse(
        analysis_id=analysis_id,
        section=request.section,
        status="pending",
    )


class ChatRequest(BaseModel):
    question: str
    club_id: uuid.UUID


class ChatResponse(BaseModel):
    answer: str
    model: str


@router.post("/{analysis_id}/chat", response_model=ChatResponse)
async def chat_about_report(
    analysis_id: uuid.UUID,
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
):
    """Chatbot táctico con Haiku — responde preguntas sobre un informe específico."""
    result = await db.execute(
        select(MatchAnalysis, Match)
        .join(Match, MatchAnalysis.match_id == Match.id)
        .where(MatchAnalysis.id == analysis_id)
        .where(MatchAnalysis.club_id == request.club_id)
    )
    row = result.one_or_none()

    if not row:
        raise HTTPException(status_code=404, detail="Informe no encontrado.")

    analysis, match = row

    if analysis.status != AnalysisStatus.DONE or not analysis.contenido_md:
        raise HTTPException(
            status_code=400,
            detail="El informe aún no está disponible para consultas.",
        )

    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise HTTPException(status_code=500, detail="Servicio de IA no configurado.")

    system = (
        f"Eres un analista táctico de fútbol experto. Tienes acceso al informe táctico completo "
        f"del partido {match.equipo_local} vs {match.equipo_visitante}. "
        f"Responde en español, de forma concisa y usando terminología táctica correcta.\n\n"
        f"INFORME:\n{analysis.contenido_md[:8000]}"
    )

    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=512,
        system=system,
        messages=[{"role": "user", "content": request.question}],
    )

    answer = response.content[0].text

    track_chatbot_query(
        club_id=str(request.club_id),
        analysis_id=str(analysis_id),
        query_length=len(request.question),
    )

    logger.info(
        "chatbot_query",
        analysis_id=str(analysis_id),
        club_id=str(request.club_id),
        query_length=len(request.question),
        answer_length=len(answer),
        model="claude-haiku-4-5-20251001",
    )

    return ChatResponse(answer=answer, model="claude-haiku-4-5-20251001")
