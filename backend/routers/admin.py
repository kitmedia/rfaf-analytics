"""Router: /api/admin — panel admin con métricas reales."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models import (
    AnalysisStatus,
    Club,
    Feedback,
    MatchAnalysis,
    PlanType,
)

router = APIRouter(prefix="/admin", tags=["admin"])

# Precio mensual por plan
PLAN_PRICES = {
    PlanType.BASICO: 49.0,
    PlanType.PROFESIONAL: 149.0,
    PlanType.FEDERADO: 104.0,
}


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


@router.get("/dashboard", response_model=AdminDashboard)
async def admin_dashboard(db: AsyncSession = Depends(get_db)):
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
