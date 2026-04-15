"""Router: /api/teams — búsqueda de equipos y análisis disponibles."""

import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, union, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models import AnalysisStatus, Match, MatchAnalysis

logger = structlog.get_logger()

router = APIRouter(prefix="/teams", tags=["teams"])


class TeamSearchResult(BaseModel):
    name: str
    match_count: int


class TeamAnalysisItem(BaseModel):
    analysis_id: uuid.UUID
    date: str
    opponent: str


class TeamAnalysesResponse(BaseModel):
    team_name: str
    analysis_count: int
    latest_analysis_date: str | None
    analyses: list[TeamAnalysisItem]


@router.get("/search", response_model=list[TeamSearchResult])
async def search_teams(
    q: str,
    db: AsyncSession = Depends(get_db),
):
    """Busca equipos por nombre en partidos existentes."""
    if len(q) < 2:
        raise HTTPException(status_code=422, detail="Mínimo 2 caracteres para buscar.")

    # Get unique team names from matches
    local_q = select(Match.equipo_local.label("name")).where(Match.equipo_local.ilike(f"%{q}%"))
    visit_q = select(Match.equipo_visitante.label("name")).where(Match.equipo_visitante.ilike(f"%{q}%"))
    combined = union(local_q, visit_q).subquery()

    result = await db.execute(
        select(combined.c.name, func.count().label("cnt"))
        .select_from(combined)
        .group_by(combined.c.name)
        .order_by(func.count().desc())
        .limit(20)
    )
    rows = result.all()

    return [TeamSearchResult(name=name, match_count=cnt) for name, cnt in rows]


@router.get("/{team_name}/analyses", response_model=TeamAnalysesResponse)
async def get_team_analyses(
    team_name: str,
    db: AsyncSession = Depends(get_db),
):
    """Obtiene análisis disponibles para un equipo."""
    result = await db.execute(
        select(MatchAnalysis, Match)
        .join(Match, MatchAnalysis.match_id == Match.id)
        .where(MatchAnalysis.status == AnalysisStatus.DONE)
        .where(or_(
            Match.equipo_local.ilike(f"%{team_name}%"),
            Match.equipo_visitante.ilike(f"%{team_name}%"),
        ))
        .order_by(MatchAnalysis.created_at.desc())
        .limit(10)
    )
    rows = result.all()

    analyses = []
    for analysis, match in rows:
        opponent = match.equipo_visitante if match.equipo_local.lower() in team_name.lower() else match.equipo_local
        analyses.append(TeamAnalysisItem(
            analysis_id=analysis.id,
            date=analysis.created_at.isoformat(),
            opponent=opponent,
        ))

    return TeamAnalysesResponse(
        team_name=team_name,
        analysis_count=len(analyses),
        latest_analysis_date=analyses[0].date if analyses else None,
        analyses=analyses,
    )
