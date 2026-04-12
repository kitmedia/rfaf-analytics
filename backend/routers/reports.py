"""Router: GET /api/reports - listar y obtener informes."""

import os
import uuid

import anthropic
import structlog
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.limiter import limiter
from backend.models import AnalysisStatus, Match, MatchAnalysis
from backend.routers.auth import TokenPayload, get_current_user
from backend.services.pdf_service import generate_pdf
from backend.services.tracking_service import (
    track_chatbot_query,
    track_pdf_downloaded,
    track_report_viewed,
)

logger = structlog.get_logger()

router = APIRouter(prefix="/reports", tags=["reports"])


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
    cost_gemini: float | None
    cost_claude: float | None
    duration_s: float | None
    created_at: str


# --- Endpoints ---


@router.get("", response_model=list[ReportSummary])
async def list_reports(
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_user),
):
    """Lista todos los informes del club autenticado."""
    club_id = uuid.UUID(current_user.club_id)
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
    current_user: TokenPayload = Depends(get_current_user),
):
    """Obtiene un informe completo por ID."""
    result = await db.execute(
        select(MatchAnalysis, Match)
        .join(Match, MatchAnalysis.match_id == Match.id)
        .where(
            MatchAnalysis.id == analysis_id,
            MatchAnalysis.club_id == uuid.UUID(current_user.club_id),
        )
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
        cost_gemini=analysis.cost_gemini,
        cost_claude=analysis.cost_claude,
        duration_s=analysis.duration_s,
        created_at=analysis.created_at.isoformat(),
    )


@router.get("/{analysis_id}/pdf")
async def download_report_pdf(
    analysis_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_user),
):
    """Descarga el informe en formato PDF."""
    result = await db.execute(
        select(MatchAnalysis, Match)
        .join(Match, MatchAnalysis.match_id == Match.id)
        .where(
            MatchAnalysis.id == analysis_id,
            MatchAnalysis.club_id == uuid.UUID(current_user.club_id),
        )
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


class ChatRequest(BaseModel):
    question: str
    club_id: uuid.UUID


class ChatResponse(BaseModel):
    answer: str
    model: str


@router.post("/{analysis_id}/chat", response_model=ChatResponse)
@limiter.limit("20/minute")
async def chat_about_report(
    http_request: Request,
    analysis_id: uuid.UUID,
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_user),
):
    """Chatbot táctico con Haiku — responde preguntas sobre un informe específico."""
    result = await db.execute(
        select(MatchAnalysis, Match)
        .join(Match, MatchAnalysis.match_id == Match.id)
        .where(MatchAnalysis.id == analysis_id)
        .where(MatchAnalysis.club_id == uuid.UUID(current_user.club_id))
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
        club_id=current_user.club_id,
        analysis_id=str(analysis_id),
        query_length=len(request.question),
    )

    logger.info(
        "chatbot_query",
        analysis_id=str(analysis_id),
        club_id=current_user.club_id,
        query_length=len(request.question),
        answer_length=len(answer),
        model="claude-haiku-4-5-20251001",
    )

    return ChatResponse(answer=answer, model="claude-haiku-4-5-20251001")
