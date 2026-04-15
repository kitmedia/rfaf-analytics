"""Router: GET /api/players — listado de jugadores con estado de scouting."""

import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models import Player, ScoutReport, ScoutType

logger = structlog.get_logger()

router = APIRouter(prefix="/players", tags=["players"])


# --- Schemas ---


class PlayerListItem(BaseModel):
    id: uuid.UUID
    name: str
    shirt_number: int | None
    position: str | None
    has_scout_report: bool
    scout_report_id: uuid.UUID | None
    scout_status: str | None


class PlayerListResponse(BaseModel):
    players: list[PlayerListItem]
    total: int


# --- Endpoints ---


@router.get("", response_model=PlayerListResponse)
async def list_players(
    club_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Lista todos los jugadores de un club con su estado de scouting."""
    # Subquery: latest scout report per player
    latest_scout = (
        select(
            ScoutReport.player_id,
            func.max(ScoutReport.created_at).label("latest_created"),
        )
        .where(ScoutReport.club_id == club_id)
        .where(ScoutReport.scout_type == ScoutType.PLAYER_SCOUT)
        .group_by(ScoutReport.player_id)
        .subquery()
    )

    result = await db.execute(
        select(Player, ScoutReport)
        .outerjoin(
            latest_scout,
            Player.id == latest_scout.c.player_id,
        )
        .outerjoin(
            ScoutReport,
            (ScoutReport.player_id == Player.id)
            & (ScoutReport.created_at == latest_scout.c.latest_created)
            & (ScoutReport.club_id == club_id)
            & (ScoutReport.scout_type == ScoutType.PLAYER_SCOUT),
        )
        .where(Player.club_id == club_id)
        .order_by(Player.name)
    )
    rows = result.all()

    players = []
    for player, scout in rows:
        players.append(PlayerListItem(
            id=player.id,
            name=player.name,
            shirt_number=player.shirt_number,
            position=player.position.value if player.position else None,
            has_scout_report=scout is not None,
            scout_report_id=scout.id if scout else None,
            scout_status=scout.status.value if scout and hasattr(scout.status, 'value') else (scout.status if scout else None),
        ))

    return PlayerListResponse(players=players, total=len(players))
