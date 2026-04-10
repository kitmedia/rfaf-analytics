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

    try:
        # Step 1: Gemini analysis
        _update_analysis_status(
            analysis_id, "processing", 10, "Analizando vídeo con Gemini..."
        )

        from backend.services.gemini_service import analyze_youtube_video

        tactical_data = asyncio.run(analyze_youtube_video(youtube_url))

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

        # Step 7: Save everything to MatchAnalysis
        _update_analysis_status(
            analysis_id,
            "done",
            100,
            "Informe completado",
            contenido_md=contenido_md,
            charts_json=charts_json,
            cost_claude=cost_claude,
            cost_gemini=0.49,
            xg_local=round(xg_local, 2),
            xg_visitante=round(xg_visitante, 2),
        )

        duration_s = time.time() - _task_start_time

        from backend.services.tracking_service import track_analysis_completed
        track_analysis_completed(
            club_id=club_id,
            analysis_id=analysis_id,
            duration_s=duration_s,
            cost_gemini=0.49,
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
