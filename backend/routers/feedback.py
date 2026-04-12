"""Router: /api/feedback — feedback estructurado de clubes beta."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models import Club, Feedback, FeedbackCategory
from backend.routers.auth import TokenPayload, get_current_user
from backend.services.tracking_service import track_feedback_submitted

router = APIRouter(prefix="/feedback", tags=["feedback"])


class FeedbackRequest(BaseModel):
    club_id: uuid.UUID
    analysis_id: uuid.UUID | None = None
    category: str
    rating: int
    comment: str | None = None

    @field_validator("rating")
    @classmethod
    def validate_rating(cls, v: int) -> int:
        if v < 1 or v > 5:
            raise ValueError("La puntuación debe ser entre 1 y 5.")
        return v

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        valid = [c.value for c in FeedbackCategory]
        if v not in valid:
            raise ValueError(f"Categoría no válida. Opciones: {valid}")
        return v


class FeedbackResponse(BaseModel):
    id: uuid.UUID
    club_id: uuid.UUID
    category: str
    rating: int
    comment: str | None
    created_at: str


class FeedbackListResponse(BaseModel):
    feedbacks: list[FeedbackResponse]
    total: int
    avg_rating: float | None


@router.post("", response_model=FeedbackResponse, status_code=201)
async def create_feedback(
    request: FeedbackRequest,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_user),
):
    """Enviar feedback estructurado."""
    if str(request.club_id) != current_user.club_id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="No puedes enviar feedback en nombre de otro club.")

    result = await db.execute(select(Club).where(Club.id == request.club_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Club no encontrado.")

    fb = Feedback(
        club_id=request.club_id,
        analysis_id=request.analysis_id,
        category=FeedbackCategory(request.category),
        rating=request.rating,
        comment=request.comment,
    )
    db.add(fb)
    await db.flush()

    track_feedback_submitted(
        club_id=str(request.club_id),
        rating=request.rating,
        category=request.category,
    )

    return FeedbackResponse(
        id=fb.id,
        club_id=fb.club_id,
        category=request.category,
        rating=fb.rating,
        comment=fb.comment,
        created_at=fb.created_at.isoformat(),
    )


@router.get("", response_model=FeedbackListResponse)
async def list_feedback(
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_user),
):
    """Listar feedback del club autenticado (admins ven todo)."""
    query = select(Feedback).order_by(Feedback.created_at.desc())
    if current_user.role != "admin":
        query = query.where(Feedback.club_id == uuid.UUID(current_user.club_id))

    result = await db.execute(query)
    feedbacks = result.scalars().all()

    items = [
        FeedbackResponse(
            id=fb.id,
            club_id=fb.club_id,
            category=fb.category.value if isinstance(fb.category, FeedbackCategory) else fb.category,
            rating=fb.rating,
            comment=fb.comment,
            created_at=fb.created_at.isoformat(),
        )
        for fb in feedbacks
    ]

    ratings = [fb.rating for fb in feedbacks]
    avg = round(sum(ratings) / len(ratings), 2) if ratings else None

    return FeedbackListResponse(feedbacks=items, total=len(items), avg_rating=avg)
