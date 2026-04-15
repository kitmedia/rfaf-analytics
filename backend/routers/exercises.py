"""Router: /api/exercises — tracking de ejercicios implementados."""

import uuid
from datetime import datetime, timedelta, timezone

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select, delete, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models import ExerciseTracking, MatchAnalysis, AnalysisStatus

logger = structlog.get_logger()

router = APIRouter(prefix="/exercises", tags=["exercises"])


# --- Schemas ---


class MarkCompleteRequest(BaseModel):
    club_id: uuid.UUID
    analysis_id: uuid.UUID
    exercise_name: str = Field(min_length=1, max_length=500)


class ExerciseStatus(BaseModel):
    exercise_name: str
    completed: bool
    completed_date: str | None


class ExerciseListResponse(BaseModel):
    exercises: list[ExerciseStatus]


class WeeklySummaryResponse(BaseModel):
    completed_count: int
    total_count: int
    exercises: list[ExerciseStatus]


# --- Endpoints ---


@router.post("/mark-complete", response_model=ExerciseStatus)
async def mark_exercise_complete(
    request: MarkCompleteRequest,
    db: AsyncSession = Depends(get_db),
):
    """Marca un ejercicio como implementado."""
    # RLS: verify analysis belongs to club
    analysis = await _get_analysis_for_club(db, request.analysis_id, request.club_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="Análisis no encontrado.")

    # Check if already tracked (idempotent)
    result = await db.execute(
        select(ExerciseTracking)
        .where(ExerciseTracking.club_id == request.club_id)
        .where(ExerciseTracking.match_analysis_id == request.analysis_id)
        .where(ExerciseTracking.exercise_name == request.exercise_name)
    )
    existing = result.scalar_one_or_none()

    now = datetime.now(timezone.utc)

    if existing:
        # Already marked — update completed_date
        existing.completed = True
        existing.completed_date = now
    else:
        tracking = ExerciseTracking(
            club_id=request.club_id,
            match_analysis_id=request.analysis_id,
            exercise_name=request.exercise_name,
            completed=True,
            completed_date=now,
        )
        db.add(tracking)

    await db.commit()

    logger.info(
        "exercise_marked_complete",
        club_id=str(request.club_id),
        analysis_id=str(request.analysis_id),
        exercise_name=request.exercise_name,
    )

    return ExerciseStatus(
        exercise_name=request.exercise_name,
        completed=True,
        completed_date=now.isoformat(),
    )


@router.post("/unmark", status_code=204)
async def unmark_exercise(
    request: MarkCompleteRequest,
    db: AsyncSession = Depends(get_db),
):
    """Desmarca un ejercicio como implementado."""
    # RLS: verify analysis belongs to club
    analysis = await _get_analysis_for_club(db, request.analysis_id, request.club_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="Análisis no encontrado.")

    await db.execute(
        delete(ExerciseTracking)
        .where(ExerciseTracking.club_id == request.club_id)
        .where(ExerciseTracking.match_analysis_id == request.analysis_id)
        .where(ExerciseTracking.exercise_name == request.exercise_name)
    )
    await db.commit()

    logger.info(
        "exercise_unmarked",
        club_id=str(request.club_id),
        analysis_id=str(request.analysis_id),
        exercise_name=request.exercise_name,
    )


@router.get("/by-analysis/{analysis_id}", response_model=ExerciseListResponse)
async def get_exercises_by_analysis(
    analysis_id: uuid.UUID,
    club_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Lista ejercicios completados para un análisis específico."""
    # RLS
    analysis = await _get_analysis_for_club(db, analysis_id, club_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="Análisis no encontrado.")

    result = await db.execute(
        select(ExerciseTracking)
        .where(ExerciseTracking.club_id == club_id)
        .where(ExerciseTracking.match_analysis_id == analysis_id)
    )
    rows = result.scalars().all()

    return ExerciseListResponse(
        exercises=[
            ExerciseStatus(
                exercise_name=r.exercise_name,
                completed=r.completed,
                completed_date=r.completed_date.isoformat() if r.completed_date else None,
            )
            for r in rows
        ]
    )


@router.get("/weekly-summary", response_model=WeeklySummaryResponse)
async def get_weekly_summary(
    club_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Resumen semanal de ejercicios completados para un club."""
    # Calculate current week boundaries (Monday to Sunday, Europe/Madrid)
    now = datetime.now()
    monday = now - timedelta(days=now.weekday())
    monday = monday.replace(hour=0, minute=0, second=0, microsecond=0)
    sunday = monday + timedelta(days=6, hours=23, minutes=59, seconds=59)

    # Count total exercises across all done analyses with training plans
    total_result = await db.execute(
        select(MatchAnalysis.training_plan_json)
        .where(MatchAnalysis.club_id == club_id)
        .where(MatchAnalysis.status == AnalysisStatus.DONE)
        .where(MatchAnalysis.training_plan_json.isnot(None))
    )
    plans = total_result.scalars().all()

    total_count = 0
    for plan in plans:
        if isinstance(plan, dict) and plan.get("contenido_md"):
            # Count #### Ejercicio headers in markdown
            md = plan["contenido_md"]
            total_count += md.count("#### Ejercicio")

    # Count completed this week
    completed_result = await db.execute(
        select(ExerciseTracking)
        .where(ExerciseTracking.club_id == club_id)
        .where(ExerciseTracking.completed == True)  # noqa: E712
        .where(ExerciseTracking.completed_date >= monday)
        .where(ExerciseTracking.completed_date <= sunday)
    )
    completed_rows = completed_result.scalars().all()

    return WeeklySummaryResponse(
        completed_count=len(completed_rows),
        total_count=total_count,
        exercises=[
            ExerciseStatus(
                exercise_name=r.exercise_name,
                completed=True,
                completed_date=r.completed_date.isoformat() if r.completed_date else None,
            )
            for r in completed_rows
        ],
    )


class ImpactResponse(BaseModel):
    has_impact: bool
    metric_name: str | None = None
    improvement_pct: float | None = None
    message: str | None = None


@router.get("/impact", response_model=ImpactResponse)
async def get_exercise_impact(
    club_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Calcula el impacto de los ejercicios completados en las métricas del equipo."""
    # Find first completed exercise date
    first_exercise = await db.execute(
        select(func.min(ExerciseTracking.completed_date))
        .where(ExerciseTracking.club_id == club_id)
        .where(ExerciseTracking.completed == True)  # noqa: E712
    )
    first_date = first_exercise.scalar()

    if not first_date:
        return ImpactResponse(has_impact=False)

    # Get analyses BEFORE first exercise
    before_result = await db.execute(
        select(MatchAnalysis.xg_local)
        .where(MatchAnalysis.club_id == club_id)
        .where(MatchAnalysis.status == AnalysisStatus.DONE)
        .where(MatchAnalysis.xg_local.isnot(None))
        .where(MatchAnalysis.created_at < first_date)
    )
    before_values = [r[0] for r in before_result.all()]

    # Get analyses AFTER first exercise
    after_result = await db.execute(
        select(MatchAnalysis.xg_local)
        .where(MatchAnalysis.club_id == club_id)
        .where(MatchAnalysis.status == AnalysisStatus.DONE)
        .where(MatchAnalysis.xg_local.isnot(None))
        .where(MatchAnalysis.created_at >= first_date)
    )
    after_values = [r[0] for r in after_result.all()]

    if len(before_values) < 2 or len(after_values) < 2:
        return ImpactResponse(has_impact=False)

    avg_before = sum(before_values) / len(before_values)
    avg_after = sum(after_values) / len(after_values)

    if avg_before == 0:
        return ImpactResponse(has_impact=False)

    improvement = round(((avg_after - avg_before) / avg_before) * 100, 1)

    return ImpactResponse(
        has_impact=True,
        metric_name="xG",
        improvement_pct=improvement,
        message=f"Tu equipo {'mejoró' if improvement > 0 else 'empeoró'} un {abs(improvement)}% en xG desde que empezaste a trabajar los ejercicios",
    )


async def _get_analysis_for_club(
    db: AsyncSession,
    analysis_id: uuid.UUID,
    club_id: uuid.UUID,
) -> MatchAnalysis | None:
    """RLS helper: verify analysis belongs to club."""
    result = await db.execute(
        select(MatchAnalysis)
        .where(MatchAnalysis.id == analysis_id)
        .where(MatchAnalysis.club_id == club_id)
    )
    return result.scalar_one_or_none()
