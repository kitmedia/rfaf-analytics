"""Router: POST /api/upload/video — subida directa de video a R2."""

import uuid

import structlog
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models import AnalysisStatus, Club, Match, MatchAnalysis, PlanType
from backend.services.tracking_service import track_analysis_started

logger = structlog.get_logger()

router = APIRouter(prefix="/upload", tags=["upload"])
limiter = Limiter(key_func=get_remote_address)

ALLOWED_EXTENSIONS = {"mp4", "mov", "avi"}
ALLOWED_CONTENT_TYPES = {"video/mp4", "video/quicktime", "video/x-msvideo", "video/avi"}

UPLOAD_SIZE_LIMITS = {
    PlanType.BASICO: 2 * 1024 * 1024 * 1024,        # 2 GB
    PlanType.PROFESIONAL: 5 * 1024 * 1024 * 1024,    # 5 GB
    PlanType.FEDERADO: 5 * 1024 * 1024 * 1024,       # 5 GB
}


class UploadResponse(BaseModel):
    analysis_id: uuid.UUID
    status: str
    check_url: str


@router.post("/video", response_model=UploadResponse)
@limiter.limit("3/minute")
async def upload_video(
    req: Request,
    file: UploadFile = File(...),
    club_id: str = Form(...),
    equipo_local: str = Form(...),
    equipo_visitante: str = Form(...),
    competicion: str = Form(None),
    db: AsyncSession = Depends(get_db),
):
    """Sube video directamente a R2 y encola análisis."""
    club_uuid = uuid.UUID(club_id)

    # Validate club
    result = await db.execute(select(Club).where(Club.id == club_uuid))
    club = result.scalar_one_or_none()
    if not club:
        raise HTTPException(status_code=404, detail="Club no encontrado.")
    if not club.active:
        raise HTTPException(status_code=403, detail="La suscripción del club no está activa.")

    # Validate file extension
    if not file.filename:
        raise HTTPException(status_code=422, detail="El archivo debe tener un nombre.")
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=422,
            detail=f"Formato no soportado: .{ext}. Usa MP4, MOV o AVI.",
        )

    # Read file
    file_bytes = await file.read()
    file_size = len(file_bytes)

    # Validate size
    size_limit = UPLOAD_SIZE_LIMITS.get(club.plan, 2 * 1024 * 1024 * 1024)
    if file_size > size_limit:
        limit_gb = size_limit / (1024 * 1024 * 1024)
        raise HTTPException(
            status_code=413,
            detail=f"El archivo excede el límite de {limit_gb:.0f} GB de tu plan {club.plan.value}.",
        )

    # Plan limits check
    from backend.routers.analyze import PLAN_LIMITS
    limit = PLAN_LIMITS.get(club.plan)
    if limit is not None and club.analisis_mes_actual >= limit:
        raise HTTPException(
            status_code=429,
            detail=f"Has alcanzado el límite de {limit} análisis/mes del plan {club.plan.value}.",
        )

    # Upload to R2
    video_uuid = uuid.uuid4()
    r2_key = f"videos/{club_id}/{video_uuid}.{ext}"
    content_type = file.content_type or "video/mp4"

    from backend.services.storage_service import upload_video as r2_upload_video
    r2_url = r2_upload_video(r2_key, file_bytes, content_type)

    if not r2_url:
        raise HTTPException(
            status_code=500,
            detail="Error al subir el video. Inténtalo de nuevo.",
        )

    # Increment monthly counter
    club.analisis_mes_actual += 1

    # Create Match + MatchAnalysis
    match = Match(
        club_id=club_uuid,
        youtube_url=r2_url,  # Reuse youtube_url field for R2 URL
        equipo_local=equipo_local,
        equipo_visitante=equipo_visitante,
        competicion=competicion,
    )
    db.add(match)
    await db.flush()

    analysis = MatchAnalysis(
        match_id=match.id,
        club_id=club_uuid,
        status=AnalysisStatus.PENDING,
        progress_pct=0,
        current_step="Video subido — en cola de procesamiento",
    )
    db.add(analysis)
    await db.flush()
    await db.commit()

    # Enqueue task
    from backend.workers.tasks import analyze_match_task

    analyze_match_task.delay(
        analysis_id=str(analysis.id),
        match_id=str(match.id),
        youtube_url=r2_url,
        equipo_local=equipo_local,
        equipo_visitante=equipo_visitante,
        competicion=competicion,
        club_id=club_id,
    )

    track_analysis_started(
        club_id=club_id,
        analysis_id=str(analysis.id),
        youtube_url=r2_url,
        equipo_local=equipo_local,
        equipo_visitante=equipo_visitante,
        competicion=competicion,
    )

    logger.info(
        "video_upload_enqueued",
        analysis_id=str(analysis.id),
        club_id=club_id,
        r2_key=r2_key,
        file_size_mb=round(file_size / (1024 * 1024), 1),
    )

    return UploadResponse(
        analysis_id=analysis.id,
        status="pending",
        check_url=f"/api/analyze/status/{analysis.id}",
    )
