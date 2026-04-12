"""Router: /api/admin — panel de administracion completo RFAF."""

import asyncio
import os
import secrets
import uuid
from datetime import datetime
from pathlib import Path

import boto3
import structlog
from celery.result import AsyncResult
from fastapi import APIRouter, Depends, HTTPException, Query
from passlib.hash import bcrypt
from pydantic import BaseModel, EmailStr
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models import (
    AnalysisStatus,
    Club,
    Feedback,
    FeedbackCategory,
    Match,
    MatchAnalysis,
    PlanType,
    User,
    UserRole,
)
from backend.routers.auth import TokenPayload, get_current_user
from backend.workers.tasks import app as celery_app

logger = structlog.get_logger()

router = APIRouter(prefix="/admin", tags=["admin"])

# Precio mensual por plan
PLAN_PRICES = {
    PlanType.BASICO: 49.0,
    PlanType.PROFESIONAL: 149.0,
    PlanType.FEDERADO: 104.0,
}

# R2 config (for backups listing)
R2_ACCESS_KEY = os.getenv("CLOUDFLARE_R2_ACCESS_KEY", "")
R2_SECRET_KEY = os.getenv("CLOUDFLARE_R2_SECRET_KEY", "")
R2_ENDPOINT = os.getenv("CLOUDFLARE_R2_ENDPOINT", "")
R2_BUCKET = os.getenv("CLOUDFLARE_R2_BUCKET", "rfaf-analytics")


# ---------------------------------------------------------------------------
# Admin dependency
# ---------------------------------------------------------------------------


async def require_admin(user: TokenPayload = Depends(get_current_user)) -> TokenPayload:
    """Verifica que el usuario autenticado sea admin. Devuelve 403 si no lo es."""
    if user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Acceso denegado. Se requiere rol de administrador.",
        )
    return user


# ---------------------------------------------------------------------------
# Pydantic response / request models
# ---------------------------------------------------------------------------


# --- Dashboard ---

class AdminDashboard(BaseModel):
    total_clubs: int
    active_clubs: int
    mrr_eur: float
    total_analyses: int
    analyses_done: int
    analyses_error: int
    total_cost_gemini: float
    total_cost_claude: float
    total_cost_eur: float
    margin_pct: float
    avg_rating: float | None
    feedback_count: int
    clubs_by_plan: dict[str, int]


# --- Clubs ---

class ClubOut(BaseModel):
    id: str
    name: str
    email: str
    plan: str
    active: bool
    analisis_mes_actual: int
    stripe_customer_id: str | None
    user_count: int
    analysis_count: int
    created_at: datetime

    model_config = {"from_attributes": True}


class ClubCreate(BaseModel):
    club_name: str
    club_email: EmailStr
    plan: PlanType = PlanType.BASICO
    admin_name: str
    admin_email: EmailStr
    admin_password: str


class ClubUpdate(BaseModel):
    name: str | None = None
    email: EmailStr | None = None
    plan: PlanType | None = None
    active: bool | None = None


class ClubListResponse(BaseModel):
    items: list[ClubOut]
    total: int
    page: int
    per_page: int


# --- Users ---

class UserOut(BaseModel):
    id: str
    club_id: str
    club_name: str
    email: str
    name: str
    role: str
    created_at: datetime

    model_config = {"from_attributes": True}


class UserCreate(BaseModel):
    club_id: str
    email: EmailStr
    name: str
    password: str
    role: UserRole = UserRole.ENTRENADOR


class UserUpdate(BaseModel):
    name: str | None = None
    role: UserRole | None = None


class UserListResponse(BaseModel):
    items: list[UserOut]
    total: int
    page: int
    per_page: int


class ResetPasswordResponse(BaseModel):
    user_id: str
    temp_password: str
    message: str


# --- Analyses ---

class AnalysisOut(BaseModel):
    id: str
    match_id: str
    club_id: str
    club_name: str
    equipo_local: str
    equipo_visitante: str
    status: str
    progress_pct: int
    current_step: str | None
    xg_local: float | None
    xg_visitante: float | None
    cost_gemini: float | None
    cost_claude: float | None
    duration_s: float | None
    pdf_url: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class AnalysisListResponse(BaseModel):
    items: list[AnalysisOut]
    total: int
    page: int
    per_page: int


# --- Celery tasks ---

class CeleryTaskInfo(BaseModel):
    task_id: str
    status: str
    result: str | None = None
    traceback: str | None = None


class CeleryInspectResponse(BaseModel):
    active: dict
    reserved: dict
    scheduled: dict


# --- Backups ---

class BackupFile(BaseModel):
    key: str
    size_bytes: int
    last_modified: datetime


class BackupListResponse(BaseModel):
    items: list[BackupFile]
    total: int


class TaskEnqueuedResponse(BaseModel):
    task_id: str
    message: str


# --- ML ---

class MLModelStatus(BaseModel):
    exists: bool
    path: str
    size_bytes: int | None
    last_modified: datetime | None


# --- Feedback ---

class FeedbackOut(BaseModel):
    id: str
    club_id: str
    club_name: str
    analysis_id: str | None
    category: str
    rating: int
    comment: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class FeedbackListResponse(BaseModel):
    items: list[FeedbackOut]
    total: int
    page: int
    per_page: int


# ---------------------------------------------------------------------------
# 1. Dashboard (existing, now protected)
# ---------------------------------------------------------------------------


@router.get("/dashboard", response_model=AdminDashboard)
async def admin_dashboard(
    _admin: TokenPayload = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Panel admin: MRR real, costes IA, alertas, clubes activos."""

    # Clubs
    clubs_result = await db.execute(select(Club))
    clubs = clubs_result.scalars().all()

    total_clubs = len(clubs)
    active_clubs = sum(1 for c in clubs if c.active)

    clubs_by_plan: dict[str, int] = {}
    mrr = 0.0
    for c in clubs:
        plan_val = c.plan.value if isinstance(c.plan, PlanType) else c.plan
        clubs_by_plan[plan_val] = clubs_by_plan.get(plan_val, 0) + 1
        if c.active:
            mrr += PLAN_PRICES.get(c.plan, 0)

    # Analyses
    analyses_result = await db.execute(
        select(
            func.count(MatchAnalysis.id),
            func.count(MatchAnalysis.id).filter(MatchAnalysis.status == AnalysisStatus.DONE),
            func.count(MatchAnalysis.id).filter(MatchAnalysis.status == AnalysisStatus.ERROR),
            func.coalesce(func.sum(MatchAnalysis.cost_gemini), 0),
            func.coalesce(func.sum(MatchAnalysis.cost_claude), 0),
        )
    )
    row = analyses_result.one()
    total_analyses = row[0]
    analyses_done = row[1]
    analyses_error = row[2]
    total_cost_gemini = float(row[3])
    total_cost_claude = float(row[4])
    total_cost = total_cost_gemini + total_cost_claude

    margin_pct = ((mrr - total_cost) / mrr * 100) if mrr > 0 else 0

    # Feedback
    feedback_result = await db.execute(
        select(
            func.count(Feedback.id),
            func.avg(Feedback.rating),
        )
    )
    fb_row = feedback_result.one()
    feedback_count = fb_row[0]
    avg_rating = round(float(fb_row[1]), 2) if fb_row[1] else None

    return AdminDashboard(
        total_clubs=total_clubs,
        active_clubs=active_clubs,
        mrr_eur=round(mrr, 2),
        total_analyses=total_analyses,
        analyses_done=analyses_done,
        analyses_error=analyses_error,
        total_cost_gemini=round(total_cost_gemini, 4),
        total_cost_claude=round(total_cost_claude, 4),
        total_cost_eur=round(total_cost, 4),
        margin_pct=round(margin_pct, 1),
        avg_rating=avg_rating,
        feedback_count=feedback_count,
        clubs_by_plan=clubs_by_plan,
    )


# ---------------------------------------------------------------------------
# 2. Club Management
# ---------------------------------------------------------------------------


@router.get("/clubs", response_model=ClubListResponse)
async def list_clubs(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    _admin: TokenPayload = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Lista todos los clubes con user_count y analysis_count."""

    # Total count
    total_result = await db.execute(select(func.count(Club.id)))
    total = total_result.scalar_one()

    # Clubs with counts via subqueries
    user_count_sub = (
        select(func.count(User.id))
        .where(User.club_id == Club.id)
        .correlate(Club)
        .scalar_subquery()
    )
    analysis_count_sub = (
        select(func.count(MatchAnalysis.id))
        .where(MatchAnalysis.club_id == Club.id)
        .correlate(Club)
        .scalar_subquery()
    )

    stmt = (
        select(Club, user_count_sub.label("user_count"), analysis_count_sub.label("analysis_count"))
        .order_by(Club.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    result = await db.execute(stmt)
    rows = result.all()

    items = [
        ClubOut(
            id=str(club.id),
            name=club.name,
            email=club.email,
            plan=club.plan.value if isinstance(club.plan, PlanType) else str(club.plan),
            active=club.active,
            analisis_mes_actual=club.analisis_mes_actual,
            stripe_customer_id=club.stripe_customer_id,
            user_count=uc or 0,
            analysis_count=ac or 0,
            created_at=club.created_at,
        )
        for club, uc, ac in rows
    ]

    return ClubListResponse(items=items, total=total, page=page, per_page=per_page)


@router.post("/clubs", response_model=ClubOut, status_code=201)
async def create_club(
    payload: ClubCreate,
    _admin: TokenPayload = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Onboard nuevo club: crea Club + User administrador con bcrypt hash."""

    # Check duplicate club email
    existing_club = await db.execute(select(Club).where(Club.email == payload.club_email))
    if existing_club.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Ya existe un club con ese email.")

    # Check duplicate user email
    existing_user = await db.execute(select(User).where(User.email == payload.admin_email))
    if existing_user.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Ya existe un usuario con ese email.")

    club = Club(
        name=payload.club_name,
        email=payload.club_email,
        plan=payload.plan,
        active=True,
    )
    db.add(club)
    await db.flush()

    user = User(
        club_id=club.id,
        email=payload.admin_email,
        password_hash=bcrypt.hash(payload.admin_password),
        name=payload.admin_name,
        role=UserRole.ADMIN,
    )
    db.add(user)
    await db.flush()

    logger.info("admin_club_created", club_id=str(club.id), club_name=club.name)

    return ClubOut(
        id=str(club.id),
        name=club.name,
        email=club.email,
        plan=club.plan.value if isinstance(club.plan, PlanType) else str(club.plan),
        active=club.active,
        analisis_mes_actual=club.analisis_mes_actual,
        stripe_customer_id=club.stripe_customer_id,
        user_count=1,
        analysis_count=0,
        created_at=club.created_at,
    )


@router.put("/clubs/{club_id}", response_model=ClubOut)
async def update_club(
    club_id: uuid.UUID,
    payload: ClubUpdate,
    _admin: TokenPayload = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Actualizar club (nombre, email, plan, activo)."""

    result = await db.execute(select(Club).where(Club.id == club_id))
    club = result.scalar_one_or_none()
    if not club:
        raise HTTPException(status_code=404, detail="Club no encontrado.")

    if payload.name is not None:
        club.name = payload.name
    if payload.email is not None:
        club.email = payload.email
    if payload.plan is not None:
        club.plan = payload.plan
    if payload.active is not None:
        club.active = payload.active

    await db.flush()

    # Fetch counts
    uc_result = await db.execute(
        select(func.count(User.id)).where(User.club_id == club_id)
    )
    ac_result = await db.execute(
        select(func.count(MatchAnalysis.id)).where(MatchAnalysis.club_id == club_id)
    )

    logger.info("admin_club_updated", club_id=str(club_id))

    return ClubOut(
        id=str(club.id),
        name=club.name,
        email=club.email,
        plan=club.plan.value if isinstance(club.plan, PlanType) else str(club.plan),
        active=club.active,
        analisis_mes_actual=club.analisis_mes_actual,
        stripe_customer_id=club.stripe_customer_id,
        user_count=uc_result.scalar_one() or 0,
        analysis_count=ac_result.scalar_one() or 0,
        created_at=club.created_at,
    )


@router.patch("/clubs/{club_id}/toggle", response_model=ClubOut)
async def toggle_club_active(
    club_id: uuid.UUID,
    _admin: TokenPayload = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Activar/desactivar un club (toggle)."""

    result = await db.execute(select(Club).where(Club.id == club_id))
    club = result.scalar_one_or_none()
    if not club:
        raise HTTPException(status_code=404, detail="Club no encontrado.")

    club.active = not club.active
    await db.flush()

    uc_result = await db.execute(
        select(func.count(User.id)).where(User.club_id == club_id)
    )
    ac_result = await db.execute(
        select(func.count(MatchAnalysis.id)).where(MatchAnalysis.club_id == club_id)
    )

    logger.info("admin_club_toggled", club_id=str(club_id), active=club.active)

    return ClubOut(
        id=str(club.id),
        name=club.name,
        email=club.email,
        plan=club.plan.value if isinstance(club.plan, PlanType) else str(club.plan),
        active=club.active,
        analisis_mes_actual=club.analisis_mes_actual,
        stripe_customer_id=club.stripe_customer_id,
        user_count=uc_result.scalar_one() or 0,
        analysis_count=ac_result.scalar_one() or 0,
        created_at=club.created_at,
    )


# ---------------------------------------------------------------------------
# 3. User Management
# ---------------------------------------------------------------------------


@router.get("/users", response_model=UserListResponse)
async def list_users(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    club_id: uuid.UUID | None = None,
    _admin: TokenPayload = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Lista todos los usuarios con nombre de club. Filtrable por club_id."""

    count_stmt = select(func.count(User.id))
    if club_id:
        count_stmt = count_stmt.where(User.club_id == club_id)
    total_result = await db.execute(count_stmt)
    total = total_result.scalar_one()

    stmt = (
        select(User, Club.name.label("club_name"))
        .join(Club, User.club_id == Club.id)
        .order_by(User.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    if club_id:
        stmt = stmt.where(User.club_id == club_id)
    result = await db.execute(stmt)
    rows = result.all()

    items = [
        UserOut(
            id=str(user.id),
            club_id=str(user.club_id),
            club_name=club_name,
            email=user.email,
            name=user.name,
            role=user.role.value if isinstance(user.role, UserRole) else str(user.role),
            created_at=user.created_at,
        )
        for user, club_name in rows
    ]

    return UserListResponse(items=items, total=total, page=page, per_page=per_page)


@router.post("/users", response_model=UserOut, status_code=201)
async def create_user(
    payload: UserCreate,
    _admin: TokenPayload = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Crear usuario para un club existente."""

    # Verify club exists
    club_result = await db.execute(select(Club).where(Club.id == uuid.UUID(payload.club_id)))
    club = club_result.scalar_one_or_none()
    if not club:
        raise HTTPException(status_code=404, detail="Club no encontrado.")

    # Check duplicate email
    existing = await db.execute(select(User).where(User.email == payload.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Ya existe un usuario con ese email.")

    user = User(
        club_id=club.id,
        email=payload.email,
        password_hash=bcrypt.hash(payload.password),
        name=payload.name,
        role=payload.role,
    )
    db.add(user)
    await db.flush()

    logger.info("admin_user_created", user_id=str(user.id), club_id=str(club.id))

    return UserOut(
        id=str(user.id),
        club_id=str(user.club_id),
        club_name=club.name,
        email=user.email,
        name=user.name,
        role=user.role.value if isinstance(user.role, UserRole) else str(user.role),
        created_at=user.created_at,
    )


@router.put("/users/{user_id}", response_model=UserOut)
async def update_user(
    user_id: uuid.UUID,
    payload: UserUpdate,
    _admin: TokenPayload = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Actualizar usuario (nombre, rol)."""

    result = await db.execute(
        select(User, Club.name.label("club_name"))
        .join(Club, User.club_id == Club.id)
        .where(User.id == user_id)
    )
    row = result.one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")

    user, club_name = row

    if payload.name is not None:
        user.name = payload.name
    if payload.role is not None:
        user.role = payload.role

    await db.flush()

    logger.info("admin_user_updated", user_id=str(user_id))

    return UserOut(
        id=str(user.id),
        club_id=str(user.club_id),
        club_name=club_name,
        email=user.email,
        name=user.name,
        role=user.role.value if isinstance(user.role, UserRole) else str(user.role),
        created_at=user.created_at,
    )


@router.post("/users/{user_id}/reset-password", response_model=ResetPasswordResponse)
async def reset_user_password(
    user_id: uuid.UUID,
    _admin: TokenPayload = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Generar contrasena temporal para un usuario. Devuelve la contrasena en texto plano."""

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")

    temp_password = secrets.token_urlsafe(12)
    user.password_hash = bcrypt.hash(temp_password)
    await db.flush()

    logger.info("admin_password_reset", user_id=str(user_id))

    return ResetPasswordResponse(
        user_id=str(user_id),
        temp_password=temp_password,
        message="Contrasena temporal generada. El usuario debe cambiarla en el primer inicio de sesion.",
    )


# ---------------------------------------------------------------------------
# 4. Analysis Management
# ---------------------------------------------------------------------------


@router.get("/analyses", response_model=AnalysisListResponse)
async def list_analyses(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status: AnalysisStatus | None = None,
    club_id: uuid.UUID | None = None,
    _admin: TokenPayload = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Lista todos los analisis con nombre de club y equipos. Filtrable por status y club_id."""

    # Base count query
    count_stmt = select(func.count(MatchAnalysis.id))
    if status:
        count_stmt = count_stmt.where(MatchAnalysis.status == status)
    if club_id:
        count_stmt = count_stmt.where(MatchAnalysis.club_id == club_id)

    total_result = await db.execute(count_stmt)
    total = total_result.scalar_one()

    # Data query with joins
    stmt = (
        select(
            MatchAnalysis,
            Club.name.label("club_name"),
            Match.equipo_local,
            Match.equipo_visitante,
        )
        .join(Club, MatchAnalysis.club_id == Club.id)
        .join(Match, MatchAnalysis.match_id == Match.id)
    )

    if status:
        stmt = stmt.where(MatchAnalysis.status == status)
    if club_id:
        stmt = stmt.where(MatchAnalysis.club_id == club_id)

    stmt = (
        stmt.order_by(MatchAnalysis.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )

    result = await db.execute(stmt)
    rows = result.all()

    items = [
        AnalysisOut(
            id=str(analysis.id),
            match_id=str(analysis.match_id),
            club_id=str(analysis.club_id),
            club_name=club_name,
            equipo_local=equipo_local,
            equipo_visitante=equipo_visitante,
            status=analysis.status.value if isinstance(analysis.status, AnalysisStatus) else str(analysis.status),
            progress_pct=analysis.progress_pct,
            current_step=analysis.current_step,
            xg_local=analysis.xg_local,
            xg_visitante=analysis.xg_visitante,
            cost_gemini=analysis.cost_gemini,
            cost_claude=analysis.cost_claude,
            duration_s=analysis.duration_s,
            pdf_url=analysis.pdf_url,
            created_at=analysis.created_at,
        )
        for analysis, club_name, equipo_local, equipo_visitante in rows
    ]

    return AnalysisListResponse(items=items, total=total, page=page, per_page=per_page)


@router.post("/analyses/{analysis_id}/retry", response_model=TaskEnqueuedResponse)
async def retry_analysis(
    analysis_id: uuid.UUID,
    _admin: TokenPayload = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Reintentar un analisis: resetear a pending y re-encolar tarea Celery."""

    result = await db.execute(
        select(MatchAnalysis).where(MatchAnalysis.id == analysis_id)
    )
    analysis = result.scalar_one_or_none()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analisis no encontrado.")

    # Fetch match data for re-enqueue
    match_result = await db.execute(select(Match).where(Match.id == analysis.match_id))
    match = match_result.scalar_one_or_none()
    if not match:
        raise HTTPException(status_code=404, detail="Partido asociado no encontrado.")

    # Reset status
    analysis.status = AnalysisStatus.PENDING
    analysis.progress_pct = 0
    analysis.current_step = "Reintentando analisis..."
    analysis.contenido_md = None
    analysis.pdf_url = None
    analysis.charts_json = None
    analysis.cost_gemini = None
    analysis.cost_claude = None
    analysis.duration_s = None
    await db.flush()

    # Re-enqueue Celery task
    from backend.workers.tasks import analyze_match_task

    task = analyze_match_task.delay(
        analysis_id=str(analysis.id),
        match_id=str(match.id),
        youtube_url=match.youtube_url,
        equipo_local=match.equipo_local,
        equipo_visitante=match.equipo_visitante,
        competicion=match.competicion,
        club_id=str(analysis.club_id),
    )

    logger.info("admin_analysis_retry", analysis_id=str(analysis_id), task_id=task.id)

    return TaskEnqueuedResponse(
        task_id=task.id,
        message=f"Analisis {analysis_id} re-encolado correctamente.",
    )


# ---------------------------------------------------------------------------
# 5. Celery Tasks
# ---------------------------------------------------------------------------


def _celery_inspect_active() -> dict:
    """Blocking call: inspect active Celery tasks."""
    inspector = celery_app.control.inspect()
    return inspector.active() or {}


def _celery_inspect_reserved() -> dict:
    """Blocking call: inspect reserved Celery tasks."""
    inspector = celery_app.control.inspect()
    return inspector.reserved() or {}


def _celery_inspect_scheduled() -> dict:
    """Blocking call: inspect scheduled Celery tasks."""
    inspector = celery_app.control.inspect()
    return inspector.scheduled() or {}


@router.get("/tasks", response_model=CeleryInspectResponse)
async def list_celery_tasks(
    _admin: TokenPayload = Depends(require_admin),
):
    """Inspeccionar tareas activas, reservadas y programadas de Celery."""

    active, reserved, scheduled = await asyncio.gather(
        asyncio.to_thread(_celery_inspect_active),
        asyncio.to_thread(_celery_inspect_reserved),
        asyncio.to_thread(_celery_inspect_scheduled),
    )

    return CeleryInspectResponse(
        active=active,
        reserved=reserved,
        scheduled=scheduled,
    )


@router.get("/tasks/{task_id}", response_model=CeleryTaskInfo)
async def get_celery_task(
    task_id: str,
    _admin: TokenPayload = Depends(require_admin),
):
    """Consultar estado de una tarea Celery por task_id via AsyncResult."""

    result = await asyncio.to_thread(lambda: AsyncResult(task_id, app=celery_app))

    task_result = None
    task_traceback = None
    try:
        if result.ready():
            res = result.result
            task_result = str(res) if res is not None else None
        if result.traceback:
            task_traceback = str(result.traceback)
    except Exception:
        pass

    return CeleryTaskInfo(
        task_id=task_id,
        status=result.status,
        result=task_result,
        traceback=task_traceback,
    )


# ---------------------------------------------------------------------------
# 6. Backups
# ---------------------------------------------------------------------------


@router.post("/backups/trigger", response_model=TaskEnqueuedResponse)
async def trigger_backup(
    _admin: TokenPayload = Depends(require_admin),
):
    """Encolar tarea de backup de PostgreSQL a R2 via Celery."""

    # Register the backup task dynamically if not already registered
    @celery_app.task(name="backup_postgres_task", bind=True, max_retries=1)
    def backup_postgres_task(self):
        from backend.scripts.backup_postgres import backup_postgres
        return backup_postgres()

    task = backup_postgres_task.delay()

    logger.info("admin_backup_triggered", task_id=task.id)

    return TaskEnqueuedResponse(
        task_id=task.id,
        message="Backup de PostgreSQL encolado correctamente.",
    )


@router.get("/backups", response_model=BackupListResponse)
async def list_backups(
    _admin: TokenPayload = Depends(require_admin),
):
    """Listar archivos de backup en R2 (prefijo backups/)."""

    if not R2_ACCESS_KEY or not R2_ENDPOINT:
        return BackupListResponse(items=[], total=0)

    def _list_from_r2() -> list[BackupFile]:
        s3 = boto3.client(
            "s3",
            endpoint_url=R2_ENDPOINT,
            aws_access_key_id=R2_ACCESS_KEY,
            aws_secret_access_key=R2_SECRET_KEY,
        )
        response = s3.list_objects_v2(Bucket=R2_BUCKET, Prefix="backups/")
        items = []
        for obj in response.get("Contents", []):
            items.append(
                BackupFile(
                    key=obj["Key"],
                    size_bytes=obj["Size"],
                    last_modified=obj["LastModified"],
                )
            )
        return sorted(items, key=lambda x: x.last_modified, reverse=True)

    try:
        items = await asyncio.to_thread(_list_from_r2)
    except Exception as exc:
        logger.error("admin_backup_list_error", error=str(exc))
        raise HTTPException(status_code=502, detail=f"Error listando backups en R2: {str(exc)}")

    return BackupListResponse(items=items, total=len(items))


# ---------------------------------------------------------------------------
# 7. ML Models
# ---------------------------------------------------------------------------


@router.post("/ml/train-xg", response_model=TaskEnqueuedResponse)
async def train_xg_model(
    _admin: TokenPayload = Depends(require_admin),
):
    """Encolar entrenamiento del modelo xG via Celery."""

    @celery_app.task(name="train_xg_model_task", bind=True, max_retries=0)
    def train_xg_model_task(self):
        from backend.services.data_service import train_rfaf_xg_model
        return train_rfaf_xg_model()

    task = train_xg_model_task.delay()

    logger.info("admin_xg_train_triggered", task_id=task.id)

    return TaskEnqueuedResponse(
        task_id=task.id,
        message="Entrenamiento del modelo xG encolado correctamente.",
    )


@router.get("/ml/status", response_model=MLModelStatus)
async def ml_model_status(
    _admin: TokenPayload = Depends(require_admin),
):
    """Verificar si el modelo xG existe, tamano y fecha de modificacion."""

    from backend.services.data_service import XG_MODEL_PATH

    model_path = Path(XG_MODEL_PATH)

    if not model_path.exists():
        return MLModelStatus(
            exists=False,
            path=str(model_path),
            size_bytes=None,
            last_modified=None,
        )

    stat = model_path.stat()

    return MLModelStatus(
        exists=True,
        path=str(model_path),
        size_bytes=stat.st_size,
        last_modified=datetime.fromtimestamp(stat.st_mtime),
    )


# ---------------------------------------------------------------------------
# 8. Feedback
# ---------------------------------------------------------------------------


@router.get("/feedbacks", response_model=FeedbackListResponse)
async def list_feedbacks(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    _admin: TokenPayload = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Listar todo el feedback con nombre de club."""

    total_result = await db.execute(select(func.count(Feedback.id)))
    total = total_result.scalar_one()

    stmt = (
        select(Feedback, Club.name.label("club_name"))
        .join(Club, Feedback.club_id == Club.id)
        .order_by(Feedback.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    result = await db.execute(stmt)
    rows = result.all()

    items = [
        FeedbackOut(
            id=str(fb.id),
            club_id=str(fb.club_id),
            club_name=club_name,
            analysis_id=str(fb.analysis_id) if fb.analysis_id else None,
            category=fb.category.value if isinstance(fb.category, FeedbackCategory) else str(fb.category),
            rating=fb.rating,
            comment=fb.comment,
            created_at=fb.created_at,
        )
        for fb, club_name in rows
    ]

    return FeedbackListResponse(items=items, total=total, page=page, per_page=per_page)
