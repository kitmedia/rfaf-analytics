"""Router: /api/upcoming-matches — partidos próximos."""

import uuid
from datetime import datetime

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models import Club, UpcomingMatch

logger = structlog.get_logger()

router = APIRouter(prefix="/upcoming-matches", tags=["upcoming"])


class UpcomingMatchItem(BaseModel):
    id: uuid.UUID
    rival_name: str
    match_date: str
    competition: str | None
    source: str
    auto_analysis_id: uuid.UUID | None
    notification_sent: bool


class UpcomingMatchListResponse(BaseModel):
    matches: list[UpcomingMatchItem]
    total: int


@router.get("", response_model=UpcomingMatchListResponse)
async def list_upcoming_matches(
    club_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Lista partidos próximos para un club."""
    now = datetime.utcnow()

    result = await db.execute(
        select(UpcomingMatch)
        .where(UpcomingMatch.club_id == club_id)
        .where(UpcomingMatch.match_date >= now)
        .order_by(UpcomingMatch.match_date.asc())
    )
    rows = result.scalars().all()

    return UpcomingMatchListResponse(
        matches=[
            UpcomingMatchItem(
                id=m.id,
                rival_name=m.rival_name,
                match_date=m.match_date.isoformat(),
                competition=m.competition,
                source=m.source,
                auto_analysis_id=m.auto_analysis_id,
                notification_sent=m.notification_sent,
            )
            for m in rows
        ],
        total=len(rows),
    )


class CreateManualMatchRequest(BaseModel):
    club_id: uuid.UUID
    rival_name: str
    match_date: str
    competition: str | None = None


@router.post("/manual", response_model=UpcomingMatchItem)
async def create_manual_upcoming(
    request: CreateManualMatchRequest,
    db: AsyncSession = Depends(get_db),
):
    """Crea un partido próximo manualmente (canal abierto)."""
    # Verify club
    result = await db.execute(select(Club).where(Club.id == request.club_id))
    club = result.scalar_one_or_none()
    if not club:
        raise HTTPException(status_code=404, detail="Club no encontrado.")

    try:
        match_date = datetime.fromisoformat(request.match_date)
    except ValueError:
        raise HTTPException(status_code=422, detail="Fecha no válida. Usa formato ISO.")

    upcoming = UpcomingMatch(
        club_id=request.club_id,
        rival_name=request.rival_name,
        match_date=match_date,
        competition=request.competition,
        source="manual_input",
    )
    db.add(upcoming)
    await db.commit()
    await db.refresh(upcoming)

    logger.info("manual_upcoming_created", club_id=str(request.club_id), rival=request.rival_name)

    return UpcomingMatchItem(
        id=upcoming.id,
        rival_name=upcoming.rival_name,
        match_date=upcoming.match_date.isoformat(),
        competition=upcoming.competition,
        source=upcoming.source,
        auto_analysis_id=None,
        notification_sent=False,
    )
