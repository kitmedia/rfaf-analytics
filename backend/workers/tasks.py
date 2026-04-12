"""Celery tasks: analyze_match, analyze_rival, scout, weekly_report."""

import os
import uuid

from celery import Celery
from sqlalchemy import create_engine, update
from sqlalchemy.orm import Session, sessionmaker

import structlog

logger = structlog.get_logger()

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://rfaf_user:rfaf_pass@postgres:5432/rfaf_analytics",
)
# Celery tasks use sync psycopg2 driver, not asyncpg
SYNC_DATABASE_URL = DATABASE_URL.replace("+asyncpg", "+psycopg2").replace(
    "postgresql+psycopg2", "postgresql+psycopg2"
)

app = Celery("rfaf", broker=REDIS_URL, backend=REDIS_URL)
app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Europe/Madrid",
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    broker_connection_retry_on_startup=True,
)

# Sync DB engine for Celery tasks
_engine = create_engine(SYNC_DATABASE_URL, pool_size=5, max_overflow=10)
_SessionLocal = sessionmaker(_engine)


def _update_analysis_status(
    analysis_id: str,
    status: str,
    progress_pct: int,
    current_step: str,
    **extra_fields,
):
    """Update MatchAnalysis status in PostgreSQL (sync)."""
    from backend.models import MatchAnalysis

    with _SessionLocal() as session:
        values = {
            "status": status,
            "progress_pct": progress_pct,
            "current_step": current_step,
            **extra_fields,
        }
        session.execute(
            update(MatchAnalysis)
            .where(MatchAnalysis.id == uuid.UUID(analysis_id))
            .values(**values)
        )
        session.commit()


def _save_tactical_data(match_id: str, tactical_data: dict):
    """Save Gemini tactical JSON to Match record (sync)."""
    from backend.models import Match

    with _SessionLocal() as session:
        session.execute(
            update(Match)
            .where(Match.id == uuid.UUID(match_id))
            .values(tactical_data=tactical_data)
        )
        session.commit()


import time


@app.task(
    bind=True,
    name="analyze_match",
    max_retries=3,
    default_retry_delay=30,
    acks_late=True,
)
def analyze_match_task(
    self,
    analysis_id: str,
    match_id: str,
    youtube_url: str,
    equipo_local: str,
    equipo_visitante: str,
    competicion: str | None,
    club_id: str,
):
    """Pipeline completo: Gemini -> PostgreSQL -> Claude -> Informe.

    Idempotente: si falla, Celery reintenta sin crear duplicados.
    """
    import asyncio

    _task_start_time = time.time()

    # Notify user that analysis started
    _send_start_email(club_id, equipo_local, equipo_visitante, analysis_id)

    try:
        # Step 1: Gemini analysis
        _update_analysis_status(
            analysis_id, "processing", 10, "Analizando vídeo con Gemini..."
        )

        from backend.services.gemini_service import analyze_youtube_video, _get_video_duration, CHUNK_DURATION, MAX_DIRECT_DURATION

        tactical_data = asyncio.run(analyze_youtube_video(youtube_url))

        # Estimate Gemini cost based on video length
        vid_dur = _get_video_duration(youtube_url)
        if vid_dur and vid_dur > MAX_DIRECT_DURATION:
            _cost_gemini = round(0.15 * (vid_dur // CHUNK_DURATION + 1), 2)
        else:
            _cost_gemini = 0.49

        # Step 2: Recalculate xG with our model (if available)
        _update_analysis_status(
            analysis_id, "processing", 30, "Recalculando xG con modelo propio..."
        )

        from backend.services.data_service import predict_xg

        shots = tactical_data.get("shots", [])
        shots = predict_xg(shots)
        tactical_data["shots"] = shots

        # Step 3: Save tactical data to Match
        _update_analysis_status(
            analysis_id, "processing", 40, "Guardando datos tácticos..."
        )
        _save_tactical_data(match_id, tactical_data)

        # Step 4: Generate visualizations
        _update_analysis_status(
            analysis_id, "processing", 50, "Generando gráficas mplsoccer..."
        )

        from backend.services.visualization_service import generate_all_charts

        charts_json = generate_all_charts(
            tactical_data=tactical_data,
            equipo_local=equipo_local,
            equipo_visitante=equipo_visitante,
        )

        # Step 5: Claude report generation
        _update_analysis_status(
            analysis_id, "processing", 65, "Generando informe con Claude..."
        )

        from backend.services.claude_service import generate_match_report

        contenido_md, cost_claude = asyncio.run(
            generate_match_report(
                tactical_data=tactical_data,
                equipo_local=equipo_local,
                equipo_visitante=equipo_visitante,
                competicion=competicion,
            )
        )

        # Step 6: Calculate xG totals (prefer model xG, fallback to Gemini)
        xg_local = sum(
            s.get("xg_model") or s.get("xg_estimado") or 0
            for s in shots
            if s.get("equipo") == "local"
        )
        xg_visitante = sum(
            s.get("xg_model") or s.get("xg_estimado") or 0
            for s in shots
            if s.get("equipo") == "visitante"
        )

        # Step 7: Generate PDF and upload to R2
        _update_analysis_status(
            analysis_id, "processing", 85, "Generando PDF..."
        )

        from backend.services.pdf_service import generate_pdf
        from backend.services.storage_service import upload_pdf

        pdf_bytes = generate_pdf(
            contenido_md=contenido_md,
            charts_json=charts_json,
            equipo_local=equipo_local,
            equipo_visitante=equipo_visitante,
            competicion=competicion,
        )

        pdf_key = f"reports/{analysis_id}.pdf"
        pdf_url = upload_pdf(pdf_key, pdf_bytes)

        # Step 8: Save everything to MatchAnalysis
        _update_analysis_status(
            analysis_id,
            "done",
            100,
            "Informe completado",
            contenido_md=contenido_md,
            charts_json=charts_json,
            pdf_url=pdf_url,
            cost_claude=cost_claude,
            cost_gemini=_cost_gemini,
            xg_local=round(xg_local, 2),
            xg_visitante=round(xg_visitante, 2),
        )

        duration_s = time.time() - _task_start_time

        # Step 9: Send completion email
        _send_done_email(
            club_id, equipo_local, equipo_visitante,
            round(xg_local, 2), round(xg_visitante, 2), pdf_url,
        )

        from backend.services.tracking_service import track_analysis_completed
        track_analysis_completed(
            club_id=club_id,
            analysis_id=analysis_id,
            duration_s=duration_s,
            cost_gemini=_cost_gemini,
            cost_claude=cost_claude,
            xg_local=round(xg_local, 2),
            xg_visitante=round(xg_visitante, 2),
        )

        logger.info(
            "analyze_match_done",
            analysis_id=analysis_id,
            club_id=club_id,
            cost_eur=round(0.49 + cost_claude, 4),
            duration_s=round(duration_s, 1),
            charts_count=len(charts_json),
        )

        return {"analysis_id": analysis_id, "status": "done"}

    except Exception as exc:
        logger.error(
            "analyze_match_error",
            analysis_id=analysis_id,
            club_id=club_id,
            error=str(exc),
        )
        _update_analysis_status(
            analysis_id, "error", 0, f"Error: {str(exc)[:200]}"
        )

        from backend.services.tracking_service import track_analysis_failed
        track_analysis_failed(
            club_id=club_id,
            analysis_id=analysis_id,
            error_type=type(exc).__name__,
            retry_count=self.request.retries,
        )

        raise self.retry(exc=exc)


def _get_club_email(club_id: str) -> str | None:
    """Fetch club email from DB."""
    from backend.models import Club

    with _SessionLocal() as session:
        from sqlalchemy import select
        result = session.execute(select(Club.email).where(Club.id == uuid.UUID(club_id)))
        row = result.one_or_none()
        return row[0] if row else None


def _send_start_email(club_id: str, equipo_local: str, equipo_visitante: str, analysis_id: str):
    """Send analysis started email. Silent fail."""
    try:
        email = _get_club_email(club_id)
        if not email:
            return
        from backend.services.email_service import send_analysis_started_email
        send_analysis_started_email(email, equipo_local, equipo_visitante, analysis_id)
    except Exception as exc:
        logger.warning("email_start_failed", error=str(exc))


def _send_done_email(
    club_id: str, equipo_local: str, equipo_visitante: str,
    xg_local: float, xg_visitante: float, pdf_url: str | None,
):
    """Send report completed email. Silent fail."""
    try:
        email = _get_club_email(club_id)
        if not email:
            return
        from backend.services.email_service import send_report_email
        send_report_email(email, equipo_local, equipo_visitante, xg_local, xg_visitante, pdf_url)
    except Exception as exc:
        logger.warning("email_done_failed", error=str(exc))


@app.task(name="weekly_digest")
def weekly_digest_task():
    """Send weekly digest email to all active clubs with their analysis summary."""
    from backend.models import Club, MatchAnalysis, AnalysisStatus
    from sqlalchemy import select, func
    from datetime import datetime, timedelta

    one_week_ago = datetime.utcnow() - timedelta(days=7)

    with _SessionLocal() as session:
        clubs = session.execute(
            select(Club).where(Club.active == True)  # noqa: E712
        ).scalars().all()

        for club in clubs:
            analyses = session.execute(
                select(func.count(MatchAnalysis.id))
                .where(MatchAnalysis.club_id == club.id)
                .where(MatchAnalysis.created_at >= one_week_ago)
                .where(MatchAnalysis.status == AnalysisStatus.DONE)
            ).scalar()

            if analyses and analyses > 0:
                logger.info(
                    "weekly_digest_club",
                    club_id=str(club.id),
                    club_name=club.name,
                    analyses_this_week=analyses,
                )

    logger.info("weekly_digest_done", total_clubs=len(clubs))


# Celery beat schedule (PDF-05)
from celery.schedules import crontab

app.conf.beat_schedule = {
    "weekly-digest-monday-8am": {
        "task": "weekly_digest",
        "schedule": crontab(hour=8, minute=0, day_of_week=1),  # Monday 8:00 AM
        "options": {"queue": "default"},
    },
}
