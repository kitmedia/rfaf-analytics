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


def _store_shadow_run(analysis_id: str, model_name: str, model_version: str, xg_local: float, xg_visitante: float):
    """Store shadow model run result (sync)."""
    from backend.models import ModelShadowRun

    with _SessionLocal() as session:
        shadow = ModelShadowRun(
            analysis_id=uuid.UUID(analysis_id),
            model_name=model_name,
            model_version=model_version,
            xg_result_json={"xg_local": xg_local, "xg_visitante": xg_visitante},
        )
        session.add(shadow)
        session.commit()
    logger.info("shadow_run_stored", analysis_id=analysis_id, model=model_name, xg_local=xg_local, xg_visitante=xg_visitante)


import time


# --- Pipeline Fallback Config (NFR-8) ---

SHADOW_MODEL_ENABLED = os.getenv("SHADOW_MODEL_ENABLED", "false").lower() == "true"

PIPELINE_FALLBACKS = {
    "extraction": {"primary": "gemini-2.5-flash", "fallback": "claude-sonnet-4-6"},
    "narrative": {"primary": "claude-sonnet-4-6", "fallback": "claude-haiku-4-5-20251001"},
}


def _run_with_fallback(step_name, primary_fn, fallback_fn, context):
    """Execute primary function, fall back on failure. Returns (result, model_used) or (None, None)."""
    try:
        result = primary_fn()
        return result, PIPELINE_FALLBACKS.get(step_name, {}).get("primary", step_name)
    except Exception as primary_err:
        logger.warning(
            "pipeline_fallback_triggered",
            step=step_name,
            primary_model=PIPELINE_FALLBACKS.get(step_name, {}).get("primary"),
            fallback_model=PIPELINE_FALLBACKS.get(step_name, {}).get("fallback"),
            primary_error=str(primary_err)[:200],
            **context,
        )
        if fallback_fn is None:
            return None, None
        try:
            result = fallback_fn()
            return result, PIPELINE_FALLBACKS.get(step_name, {}).get("fallback", f"{step_name}_fallback")
        except Exception as fallback_err:
            logger.error(
                "pipeline_fallback_failed",
                step=step_name,
                fallback_error=str(fallback_err)[:200],
                **context,
            )
            return None, None


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
        fallback_ctx = {"club_id": club_id, "analysis_id": analysis_id}
        sections = {"extraction": True, "xg_calculation": True, "charts": True, "narrative": True, "pdf": True}

        # Step 1: Gemini analysis (with fallback)
        _update_analysis_status(
            analysis_id, "processing", 10, "Analizando vídeo con Gemini..."
        )

        from backend.services.gemini_service import analyze_youtube_video, _get_video_duration, CHUNK_DURATION, MAX_DIRECT_DURATION

        tactical_data, extraction_model = _run_with_fallback(
            "extraction",
            lambda: asyncio.run(analyze_youtube_video(youtube_url)),
            None,  # No viable fallback for video extraction yet
            fallback_ctx,
        )

        if tactical_data is None:
            sections["extraction"] = False
            sections["xg_calculation"] = False
            sections["charts"] = False
            tactical_data = {}

        # Estimate Gemini cost
        _cost_gemini = 0.0
        if sections["extraction"]:
            vid_dur = _get_video_duration(youtube_url)
            if vid_dur and vid_dur > MAX_DIRECT_DURATION:
                _cost_gemini = round(0.15 * (vid_dur // CHUNK_DURATION + 1), 2)
            else:
                _cost_gemini = 0.49

        # Step 2: Recalculate xG with our model
        shots = []
        if sections["extraction"]:
            _update_analysis_status(
                analysis_id, "processing", 30, "Recalculando xG con modelo propio..."
            )

            from backend.services.data_service import predict_xg

            shots = tactical_data.get("shots", [])
            shots = predict_xg(shots)
            tactical_data["shots"] = shots

        # Shadow mode: run alternative xG in parallel (NFR-7)
        if sections["extraction"] and SHADOW_MODEL_ENABLED:
            try:
                shadow_xg_local = sum(
                    s.get("xg_estimado", 0) for s in tactical_data.get("shots", [])
                    if s.get("equipo") == "local"
                )
                shadow_xg_visitante = sum(
                    s.get("xg_estimado", 0) for s in tactical_data.get("shots", [])
                    if s.get("equipo") == "visitante"
                )
                _store_shadow_run(
                    analysis_id, "gemini_raw_xg", "1.0",
                    round(shadow_xg_local, 2), round(shadow_xg_visitante, 2),
                )
            except Exception as shadow_err:
                logger.warning("shadow_mode_error", analysis_id=analysis_id, error=str(shadow_err))

        # Step 3: Save tactical data to Match
        if sections["extraction"]:
            _update_analysis_status(
                analysis_id, "processing", 40, "Guardando datos tácticos..."
            )
            _save_tactical_data(match_id, tactical_data)

        # Step 4: Generate visualizations
        charts_json = {}
        if sections["extraction"]:
            _update_analysis_status(
                analysis_id, "processing", 50, "Generando gráficas mplsoccer..."
            )

            from backend.services.visualization_service import generate_all_charts

            try:
                charts_json = generate_all_charts(
                    tactical_data=tactical_data,
                    equipo_local=equipo_local,
                    equipo_visitante=equipo_visitante,
                )
            except Exception:
                sections["charts"] = False
                charts_json = {}

        # Step 5: Claude report generation (with fallback)
        _update_analysis_status(
            analysis_id, "processing", 65, "Generando informe con Claude..."
        )

        from backend.services.claude_service import generate_match_report

        def _primary_narrative():
            return asyncio.run(generate_match_report(
                tactical_data=tactical_data,
                equipo_local=equipo_local,
                equipo_visitante=equipo_visitante,
                competicion=competicion,
            ))

        def _fallback_narrative():
            """Fallback to Haiku — same prompt, cheaper model."""
            import anthropic
            import os
            from backend.services.claude_service import _load_system_prompt, _safe_json

            api_key = os.getenv("ANTHROPIC_API_KEY", "")
            system_prompt = _load_system_prompt("INFORME_PARTIDO.md")
            user_msg = (
                f"Genera el informe táctico completo del partido:\n"
                f"- Equipo local: {equipo_local}\n- Equipo visitante: {equipo_visitante}\n"
            )
            if competicion:
                user_msg += f"- Competición: {competicion}\n"
            user_msg += f"\nDatos tácticos (JSON):\n```json\n{_safe_json(tactical_data)}\n```"

            client = anthropic.Anthropic(api_key=api_key)
            resp = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=4096,
                system=system_prompt,
                messages=[{"role": "user", "content": user_msg}],
            )
            md = resp.content[0].text
            cost = round(((resp.usage.input_tokens * 0.8 + resp.usage.output_tokens * 4) / 1_000_000) * 0.92, 4)
            return md, cost

        narrative_result, narrative_model = _run_with_fallback(
            "narrative", _primary_narrative, _fallback_narrative, fallback_ctx,
        )

        contenido_md = None
        cost_claude = 0.0
        if narrative_result:
            contenido_md, cost_claude = narrative_result
        else:
            sections["narrative"] = False

        # Step 6: Calculate xG totals
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
        pdf_url = None
        if contenido_md:
            _update_analysis_status(
                analysis_id, "processing", 85, "Generando PDF..."
            )

            from backend.services.pdf_service import generate_pdf
            from backend.services.storage_service import upload_pdf

            try:
                pdf_bytes = generate_pdf(
                    contenido_md=contenido_md,
                    charts_json=charts_json,
                    equipo_local=equipo_local,
                    equipo_visitante=equipo_visitante,
                    competicion=competicion,
                )
                pdf_key = f"reports/{analysis_id}.pdf"
                pdf_url = upload_pdf(pdf_key, pdf_bytes)
            except Exception:
                sections["pdf"] = False
        else:
            sections["pdf"] = False

        # Step 8: Save everything to MatchAnalysis
        _update_analysis_status(
            analysis_id,
            "done",
            100,
            "Informe completado" if all(sections.values()) else "Informe parcial — algunas secciones no disponibles",
            contenido_md=contenido_md,
            charts_json=charts_json if charts_json else None,
            pdf_url=pdf_url,
            cost_claude=cost_claude,
            cost_gemini=_cost_gemini,
            xg_local=round(xg_local, 2),
            xg_visitante=round(xg_visitante, 2),
            sections_available=sections,
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


@app.task(
    bind=True,
    name="generate_training_plan",
    max_retries=3,
    default_retry_delay=30,
    acks_late=True,
)
def generate_training_plan_task(
    self,
    analysis_id: str,
    club_id: str,
):
    """Genera plan de entrenamiento (P3) a partir de un MatchAnalysis completado.

    Idempotente: si falla, Celery reintenta sin crear duplicados.
    """
    import asyncio

    _task_start_time = time.time()

    try:
        # Step 1: Load MatchAnalysis and verify it's done
        from backend.models import MatchAnalysis, Match

        with _SessionLocal() as session:
            from sqlalchemy import select
            result = session.execute(
                select(MatchAnalysis, Match)
                .join(Match, MatchAnalysis.match_id == Match.id)
                .where(MatchAnalysis.id == uuid.UUID(analysis_id))
                .where(MatchAnalysis.club_id == uuid.UUID(club_id))
            )
            row = result.one_or_none()

            if not row:
                logger.error(
                    "training_plan_not_found",
                    analysis_id=analysis_id,
                    club_id=club_id,
                )
                return {"analysis_id": analysis_id, "status": "error", "detail": "Análisis no encontrado"}

            analysis, match = row

            if analysis.status.value != "done":
                logger.error(
                    "training_plan_analysis_not_done",
                    analysis_id=analysis_id,
                    status=analysis.status.value,
                )
                return {"analysis_id": analysis_id, "status": "error", "detail": "El análisis aún no está completado"}

            tactical_data = match.tactical_data
            equipo_local = match.equipo_local
            equipo_visitante = match.equipo_visitante
            competicion = match.competicion

        if not tactical_data:
            logger.error("training_plan_no_tactical_data", analysis_id=analysis_id)
            return {"analysis_id": analysis_id, "status": "error", "detail": "No hay datos tácticos disponibles"}

        # Step 2: Generate training plan with Claude Sonnet
        from backend.services.claude_service import generate_training_plan

        plan_md, cost_eur = asyncio.run(
            generate_training_plan(
                tactical_data=tactical_data,
                equipo_local=equipo_local,
                equipo_visitante=equipo_visitante,
                competicion=competicion,
            )
        )

        # Step 3: Store result and add cost (atomic, with TOCTOU guard)
        training_plan_data = {
            "contenido_md": plan_md,
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "model": "claude-sonnet-4-6",
            "cost_eur": cost_eur,
        }

        from sqlalchemy import update as sa_update
        from sqlalchemy.sql import func as sa_func
        with _SessionLocal() as session:
            # Atomic update: only write if training_plan_json is still NULL (TOCTOU guard)
            # and atomically increment cost_claude
            result = session.execute(
                sa_update(MatchAnalysis)
                .where(MatchAnalysis.id == uuid.UUID(analysis_id))
                .where(MatchAnalysis.training_plan_json.is_(None))
                .values(
                    training_plan_json=training_plan_data,
                    cost_claude=sa_func.coalesce(MatchAnalysis.cost_claude, 0) + cost_eur,
                )
            )
            session.commit()

            if result.rowcount == 0:
                logger.warning(
                    "training_plan_already_exists",
                    analysis_id=analysis_id,
                    detail="Skipped — another task already wrote the training plan",
                )
                return {"analysis_id": analysis_id, "status": "skipped"}

        duration_s = time.time() - _task_start_time

        logger.info(
            "training_plan_done",
            analysis_id=analysis_id,
            club_id=club_id,
            cost_eur=cost_eur,
            duration_s=round(duration_s, 1),
            model="claude-sonnet-4-6",
            plan_length=len(plan_md),
        )

        return {"analysis_id": analysis_id, "status": "done"}

    except (ConnectionError, TimeoutError, OSError) as exc:
        # Transient errors — retry
        logger.warning(
            "training_plan_transient_error",
            analysis_id=analysis_id,
            club_id=club_id,
            error=str(exc),
            retry=self.request.retries,
        )
        raise self.retry(exc=exc)
    except Exception as exc:
        # Permanent errors — store failure marker, do not retry
        logger.error(
            "training_plan_error",
            analysis_id=analysis_id,
            club_id=club_id,
            error=str(exc),
        )
        try:
            from sqlalchemy import update as sa_update
            with _SessionLocal() as session:
                session.execute(
                    sa_update(MatchAnalysis)
                    .where(MatchAnalysis.id == uuid.UUID(analysis_id))
                    .where(MatchAnalysis.training_plan_json.is_(None))
                    .values(training_plan_json={"error": str(exc)[:500], "status": "error"})
                )
                session.commit()
        except Exception:
            pass
        return {"analysis_id": analysis_id, "status": "error", "detail": str(exc)[:200]}


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


# --- Operations tasks (admin panel) ---


@app.task(name="backup_postgres", bind=True, max_retries=1)
def backup_postgres_task(self):
    """Trigger PostgreSQL backup to R2. Called from admin panel."""
    try:
        from backend.scripts.backup_postgres import backup_postgres
        result = backup_postgres()
        logger.info("backup_postgres_done", result=result)
        return {"status": "ok", "result": str(result)}
    except Exception as exc:
        logger.error("backup_postgres_failed", error=str(exc))
        raise self.retry(exc=exc, countdown=60)


@app.task(name="train_xg_model", bind=True, max_retries=0)
def train_xg_model_task(self):
    """Train xG model from StatsBomb data. Called from admin panel."""
    try:
        from backend.services.data_service import train_rfaf_xg_model
        metrics = train_rfaf_xg_model()
        logger.info("train_xg_model_done", **metrics)
        return {"status": "ok", "metrics": metrics}
    except Exception as exc:
        logger.error("train_xg_model_failed", error=str(exc))
        return {"status": "error", "error": str(exc)}


@app.task(bind=True, name="retry_section", max_retries=1, default_retry_delay=10)
def retry_section_task(self, analysis_id: str, section: str, club_id: str):
    """Reintenta una sección específica del pipeline."""
    import asyncio

    try:
        from backend.models import MatchAnalysis, Match

        with _SessionLocal() as session:
            from sqlalchemy import select
            result = session.execute(
                select(MatchAnalysis, Match)
                .join(Match, MatchAnalysis.match_id == Match.id)
                .where(MatchAnalysis.id == uuid.UUID(analysis_id))
                .where(MatchAnalysis.club_id == uuid.UUID(club_id))
            )
            row = result.one_or_none()
            if not row:
                return {"status": "error", "detail": "Análisis no encontrado"}
            analysis, match = row
            tactical_data = match.tactical_data or {}
            youtube_url = match.youtube_url
            equipo_local = match.equipo_local
            equipo_visitante = match.equipo_visitante
            competicion = match.competicion
            sections = dict(analysis.sections_available or {})

        result_data = {}

        if section == "extraction":
            from backend.services.gemini_service import analyze_youtube_video
            new_tactical = asyncio.run(analyze_youtube_video(youtube_url))
            _save_tactical_data(str(match.id), new_tactical)
            sections["extraction"] = True
            sections["xg_calculation"] = True

        elif section == "narrative":
            from backend.services.claude_service import generate_match_report
            contenido_md, cost = asyncio.run(generate_match_report(
                tactical_data=tactical_data, equipo_local=equipo_local,
                equipo_visitante=equipo_visitante, competicion=competicion,
            ))
            result_data["contenido_md"] = contenido_md
            sections["narrative"] = True

        elif section == "charts":
            from backend.services.visualization_service import generate_all_charts
            charts = generate_all_charts(tactical_data=tactical_data,
                equipo_local=equipo_local, equipo_visitante=equipo_visitante)
            result_data["charts_json"] = charts
            sections["charts"] = True

        elif section == "pdf":
            from backend.services.pdf_service import generate_pdf
            from backend.services.storage_service import upload_pdf
            with _SessionLocal() as session:
                md = session.execute(
                    select(MatchAnalysis.contenido_md).where(MatchAnalysis.id == uuid.UUID(analysis_id))
                ).scalar()
            if md:
                pdf_bytes = generate_pdf(contenido_md=md, charts_json=None,
                    equipo_local=equipo_local, equipo_visitante=equipo_visitante, competicion=competicion)
                pdf_url = upload_pdf(f"reports/{analysis_id}.pdf", pdf_bytes)
                result_data["pdf_url"] = pdf_url
                sections["pdf"] = True

        # Update MatchAnalysis
        from sqlalchemy import update as sa_update
        with _SessionLocal() as session:
            session.execute(
                sa_update(MatchAnalysis)
                .where(MatchAnalysis.id == uuid.UUID(analysis_id))
                .values(sections_available=sections, **result_data)
            )
            session.commit()

        logger.info("retry_section_done", analysis_id=analysis_id, section=section, club_id=club_id)
        return {"analysis_id": analysis_id, "section": section, "status": "done"}

    except Exception as exc:
        logger.error("retry_section_error", analysis_id=analysis_id, section=section, error=str(exc))
        raise self.retry(exc=exc)


@app.task(
    bind=True,
    name="generate_scout_report",
    max_retries=3,
    default_retry_delay=30,
    acks_late=True,
)
def generate_scout_report_task(
    self,
    scout_report_id: str,
    analysis_id: str,
    player_id: str,
    club_id: str,
):
    """Genera informe de scouting (P2) para un jugador."""
    import asyncio

    _task_start_time = time.time()

    try:
        from backend.models import ScoutReport, MatchAnalysis, Match, Player

        with _SessionLocal() as session:
            from sqlalchemy import select

            # Load scout report
            scout = session.execute(
                select(ScoutReport)
                .where(ScoutReport.id == uuid.UUID(scout_report_id))
                .where(ScoutReport.club_id == uuid.UUID(club_id))
            ).scalar_one_or_none()

            if not scout:
                logger.error("scout_report_not_found", scout_report_id=scout_report_id)
                return {"scout_report_id": scout_report_id, "status": "error"}

            # Update to processing
            scout.status = "processing"
            session.commit()

            # Load player + match data
            player = session.execute(
                select(Player).where(Player.id == uuid.UUID(player_id))
            ).scalar_one_or_none()

            result = session.execute(
                select(MatchAnalysis, Match)
                .join(Match, MatchAnalysis.match_id == Match.id)
                .where(MatchAnalysis.id == uuid.UUID(analysis_id))
            )
            row = result.one_or_none()

            if not player or not row:
                scout.status = "error"
                session.commit()
                return {"scout_report_id": scout_report_id, "status": "error", "detail": "Datos no encontrados"}

            analysis, match = row
            tactical_data = match.tactical_data
            player_name = player.name
            player_number = player.shirt_number
            equipo = match.equipo_local
            competicion = match.competicion
            player_stats = player.stats

        if not tactical_data:
            with _SessionLocal() as session:
                session.execute(
                    __import__("sqlalchemy").update(ScoutReport)
                    .where(ScoutReport.id == uuid.UUID(scout_report_id))
                    .values(status="error")
                )
                session.commit()
            return {"scout_report_id": scout_report_id, "status": "error", "detail": "No hay datos tácticos"}

        # Generate with Claude
        from backend.services.claude_service import generate_scout_report

        contenido_md, cost_eur = asyncio.run(
            generate_scout_report(
                tactical_data=tactical_data,
                player_name=player_name,
                player_number=player_number,
                equipo=equipo,
                competicion=competicion,
                player_stats=player_stats,
            )
        )

        # Store result
        from sqlalchemy import update as sa_update
        with _SessionLocal() as session:
            session.execute(
                sa_update(ScoutReport)
                .where(ScoutReport.id == uuid.UUID(scout_report_id))
                .values(
                    status="done",
                    contenido_md=contenido_md,
                    cost_eur=cost_eur,
                    duration_s=round(time.time() - _task_start_time, 1),
                )
            )
            session.commit()

        logger.info(
            "scout_report_done",
            scout_report_id=scout_report_id,
            player_id=player_id,
            club_id=club_id,
            cost_eur=cost_eur,
            duration_s=round(time.time() - _task_start_time, 1),
            model="claude-sonnet-4-6",
        )

        return {"scout_report_id": scout_report_id, "status": "done"}

    except (ConnectionError, TimeoutError, OSError) as exc:
        logger.warning("scout_report_transient_error", scout_report_id=scout_report_id, error=str(exc))
        raise self.retry(exc=exc)
    except Exception as exc:
        logger.error("scout_report_error", scout_report_id=scout_report_id, club_id=club_id, error=str(exc))
        try:
            from sqlalchemy import update as sa_update
            with _SessionLocal() as session:
                session.execute(
                    sa_update(ScoutReport)
                    .where(ScoutReport.id == uuid.UUID(scout_report_id))
                    .values(status="error")
                )
                session.commit()
        except Exception:
            pass
        return {"scout_report_id": scout_report_id, "status": "error"}


@app.task(name="weekly_adoption_summary")
def send_weekly_adoption_summary_task():
    """Send weekly adoption summary email to clubs with training plans."""
    from backend.models import Club, MatchAnalysis, ExerciseTracking, AnalysisStatus
    from sqlalchemy import select, func
    from datetime import datetime, timedelta

    now = datetime.utcnow()
    monday = now - timedelta(days=now.weekday())
    monday = monday.replace(hour=0, minute=0, second=0, microsecond=0)
    sunday = monday + timedelta(days=6, hours=23, minutes=59, seconds=59)
    two_weeks_ago = now - timedelta(days=14)

    emails_sent = 0
    clubs_processed = 0

    with _SessionLocal() as session:
        # Get active clubs with at least 1 done analysis
        clubs_with_analyses = session.execute(
            select(Club)
            .where(Club.active == True)  # noqa: E712
            .where(
                Club.id.in_(
                    select(MatchAnalysis.club_id)
                    .where(MatchAnalysis.status == AnalysisStatus.DONE)
                    .distinct()
                )
            )
        ).scalars().all()

        for club in clubs_with_analyses:
            clubs_processed += 1
            try:
                # Weekly summary: count exercises
                total_count = 0
                plans = session.execute(
                    select(MatchAnalysis.training_plan_json)
                    .where(MatchAnalysis.club_id == club.id)
                    .where(MatchAnalysis.status == AnalysisStatus.DONE)
                    .where(MatchAnalysis.training_plan_json.isnot(None))
                ).scalars().all()
                for plan in plans:
                    if isinstance(plan, dict) and plan.get("contenido_md"):
                        total_count += plan["contenido_md"].count("#### Ejercicio")

                completed_count = session.execute(
                    select(func.count(ExerciseTracking.id))
                    .where(ExerciseTracking.club_id == club.id)
                    .where(ExerciseTracking.completed == True)  # noqa: E712
                    .where(ExerciseTracking.completed_date >= monday)
                    .where(ExerciseTracking.completed_date <= sunday)
                ).scalar() or 0

                # Impact calculation
                improvement_msg = None
                first_date = session.execute(
                    select(func.min(ExerciseTracking.completed_date))
                    .where(ExerciseTracking.club_id == club.id)
                    .where(ExerciseTracking.completed == True)  # noqa: E712
                ).scalar()

                if first_date:
                    before = [r[0] for r in session.execute(
                        select(MatchAnalysis.xg_local)
                        .where(MatchAnalysis.club_id == club.id)
                        .where(MatchAnalysis.status == AnalysisStatus.DONE)
                        .where(MatchAnalysis.xg_local.isnot(None))
                        .where(MatchAnalysis.created_at < first_date)
                    ).all()]
                    after = [r[0] for r in session.execute(
                        select(MatchAnalysis.xg_local)
                        .where(MatchAnalysis.club_id == club.id)
                        .where(MatchAnalysis.status == AnalysisStatus.DONE)
                        .where(MatchAnalysis.xg_local.isnot(None))
                        .where(MatchAnalysis.created_at >= first_date)
                    ).all()]
                    if len(before) >= 2 and len(after) >= 2:
                        avg_b = sum(before) / len(before)
                        avg_a = sum(after) / len(after)
                        if avg_b > 0:
                            imp = round(((avg_a - avg_b) / avg_b) * 100, 1)
                            improvement_msg = f"Tu equipo {'mejoró' if imp > 0 else 'empeoró'} un {abs(imp)}% en xG desde que empezaste los ejercicios"

                # Recommended exercises from latest plan
                recommended = []
                latest_plan = session.execute(
                    select(MatchAnalysis.training_plan_json)
                    .where(MatchAnalysis.club_id == club.id)
                    .where(MatchAnalysis.training_plan_json.isnot(None))
                    .order_by(MatchAnalysis.created_at.desc())
                    .limit(1)
                ).scalar()
                if latest_plan and isinstance(latest_plan, dict) and latest_plan.get("contenido_md"):
                    import re
                    matches = re.findall(r"#### Ejercicio \d+:\s*(.+)", latest_plan["contenido_md"])
                    recommended = matches[:3]

                # Has recent analysis?
                latest_analysis_date = session.execute(
                    select(func.max(MatchAnalysis.created_at))
                    .where(MatchAnalysis.club_id == club.id)
                    .where(MatchAnalysis.status == AnalysisStatus.DONE)
                ).scalar()
                has_recent = latest_analysis_date is not None and latest_analysis_date >= two_weeks_ago

                # Send email
                from backend.services.email_service import send_weekly_adoption_email
                sent = send_weekly_adoption_email(
                    to_email=club.email,
                    club_name=club.name,
                    completed_count=completed_count,
                    total_count=total_count,
                    improvement_msg=improvement_msg,
                    recommended_exercises=recommended,
                    has_recent_analysis=has_recent,
                )
                if sent:
                    emails_sent += 1

            except Exception as exc:
                logger.warning(
                    "weekly_adoption_club_error",
                    club_id=str(club.id),
                    error=str(exc),
                )

    logger.info(
        "weekly_adoption_done",
        clubs_processed=clubs_processed,
        emails_sent=emails_sent,
    )
    return {"clubs_processed": clubs_processed, "emails_sent": emails_sent}


@app.task(name="compare_shadow_results")
def compare_shadow_results_task():
    """Weekly comparison of shadow model results vs production."""
    from backend.models import ModelShadowRun, MatchAnalysis
    from sqlalchemy import select
    from datetime import datetime, timedelta

    one_week_ago = datetime.utcnow() - timedelta(days=7)

    with _SessionLocal() as session:
        shadow_runs = session.execute(
            select(ModelShadowRun, MatchAnalysis)
            .join(MatchAnalysis, ModelShadowRun.analysis_id == MatchAnalysis.id)
            .where(ModelShadowRun.created_at >= one_week_ago)
        ).all()

        if not shadow_runs:
            logger.info("shadow_comparison_no_data", detail="No shadow runs this week")
            return {"status": "no_data"}

        divergences = []
        for shadow, analysis in shadow_runs:
            if not shadow.xg_result_json or analysis.xg_local is None:
                continue
            shadow_xg = shadow.xg_result_json.get("xg_local", 0)
            prod_xg = analysis.xg_local
            if prod_xg > 0:
                div = abs(shadow_xg - prod_xg) / prod_xg * 100
                divergences.append(div)
                # Update divergence on the shadow run
                shadow.divergence_pct = round(div, 2)

        session.commit()

        if not divergences:
            logger.info("shadow_comparison_no_xg", detail="No valid xG comparisons")
            return {"status": "no_comparisons"}

        avg_divergence = round(sum(divergences) / len(divergences), 2)
        max_divergence = round(max(divergences), 2)

        if avg_divergence > 8:
            logger.warning(
                "shadow_divergence_high",
                avg_divergence_pct=avg_divergence,
                max_divergence_pct=max_divergence,
                total_runs=len(divergences),
                detail="Divergencia > 8% — revisar modelo shadow antes de activar",
            )
        else:
            logger.info(
                "shadow_comparison_ok",
                avg_divergence_pct=avg_divergence,
                max_divergence_pct=max_divergence,
                total_runs=len(divergences),
            )

        return {
            "status": "ok",
            "avg_divergence_pct": avg_divergence,
            "max_divergence_pct": max_divergence,
            "total_runs": len(divergences),
        }


@app.task(name="check_upcoming_matches")
def check_upcoming_matches_task():
    """Check for upcoming matches and auto-generate rival analysis."""
    import asyncio
    from backend.models import Club, UpcomingMatch, Match, MatchAnalysis, ScoutReport, ScoutType, AnalysisStatus, PlanType
    from sqlalchemy import select, or_
    from datetime import datetime, timedelta

    now = datetime.utcnow()
    five_days = now + timedelta(days=5)

    with _SessionLocal() as session:
        # Get federado clubs
        federado_clubs = session.execute(
            select(Club)
            .where(Club.active == True)  # noqa: E712
            .where(Club.plan == PlanType.FEDERADO)
        ).scalars().all()

        matches_found = 0
        analyses_generated = 0
        notifications_sent = 0

        for club in federado_clubs:
            # Find upcoming matches needing notification
            upcoming_list = session.execute(
                select(UpcomingMatch)
                .where(UpcomingMatch.club_id == club.id)
                .where(UpcomingMatch.match_date >= now)
                .where(UpcomingMatch.match_date <= five_days)
                .where(UpcomingMatch.notification_sent == False)  # noqa: E712
            ).scalars().all()

            for upcoming in upcoming_list:
                matches_found += 1
                rival = upcoming.rival_name

                # Search for previous matches of the rival
                rival_matches = session.execute(
                    select(Match, MatchAnalysis)
                    .join(MatchAnalysis, MatchAnalysis.match_id == Match.id)
                    .where(MatchAnalysis.status == AnalysisStatus.DONE)
                    .where(or_(
                        Match.equipo_local.ilike(f"%{rival}%"),
                        Match.equipo_visitante.ilike(f"%{rival}%"),
                    ))
                    .order_by(Match.created_at.desc())
                    .limit(3)
                ).all()

                has_analysis = len(rival_matches) > 0

                if has_analysis:
                    # Generate rival analysis
                    try:
                        tactical_data_list = [m.tactical_data for m, ma in rival_matches if m.tactical_data]
                        if tactical_data_list:
                            from backend.services.claude_service import generate_rival_analysis
                            contenido_md, cost_eur = asyncio.run(
                                generate_rival_analysis(tactical_data_list, rival, upcoming.competition)
                            )

                            # Create ScoutReport
                            scout = ScoutReport(
                                club_id=club.id,
                                analysis_id=rival_matches[0][1].id,
                                scout_type=ScoutType.RIVAL_ANALYSIS,
                                status=AnalysisStatus.DONE,
                                contenido_md=contenido_md,
                                cost_eur=cost_eur,
                            )
                            session.add(scout)
                            session.flush()
                            upcoming.auto_analysis_id = rival_matches[0][1].id
                            analyses_generated += 1
                    except Exception as exc:
                        logger.warning("rival_analysis_error", rival=rival, club_id=str(club.id), error=str(exc))

                # Send notification
                try:
                    from backend.services.email_service import send_rival_analysis_email
                    send_rival_analysis_email(
                        to_email=club.email,
                        club_name=club.name,
                        rival_name=rival,
                        has_analysis=has_analysis,
                        match_date=upcoming.match_date.strftime("%d/%m/%Y %H:%M") if upcoming.match_date else None,
                    )
                    notifications_sent += 1
                except Exception as exc:
                    logger.warning("rival_notification_error", error=str(exc))

                upcoming.notification_sent = True

            session.commit()

    logger.info(
        "check_upcoming_matches_done",
        federado_clubs=len(federado_clubs),
        matches_found=matches_found,
        analyses_generated=analyses_generated,
        notifications_sent=notifications_sent,
    )
    return {
        "federado_clubs": len(federado_clubs),
        "matches_found": matches_found,
        "analyses_generated": analyses_generated,
        "notifications_sent": notifications_sent,
    }


# Celery beat schedule (PDF-05)
from celery.schedules import crontab

app.conf.beat_schedule = {
    "weekly-digest-monday-8am": {
        "task": "weekly_digest",
        "schedule": crontab(hour=8, minute=0, day_of_week=1),  # Monday 8:00 AM
        "options": {"queue": "default"},
    },
    "weekly-adoption-monday-8am": {
        "task": "weekly_adoption_summary",
        "schedule": crontab(hour=8, minute=0, day_of_week=1),  # Monday 8:00 AM
        "options": {"queue": "default"},
    },
    "shadow-comparison-sunday-23pm": {
        "task": "compare_shadow_results",
        "schedule": crontab(hour=23, minute=0, day_of_week=0),  # Sunday 23:00
        "options": {"queue": "default"},
    },
    "check-upcoming-matches-daily-6am": {
        "task": "check_upcoming_matches",
        "schedule": crontab(hour=6, minute=0),  # Daily 6:00 AM
        "options": {"queue": "default"},
    },
}
