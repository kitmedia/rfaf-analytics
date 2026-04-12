"""Router: /api/auth — Login JWT + token verification."""

import os
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from jose import JWTError, jwt
from passlib.hash import bcrypt
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models import Club, User

router = APIRouter(prefix="/auth", tags=["auth"])

JWT_SECRET = os.getenv("JWT_SECRET", "cambiar-en-produccion")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = 24


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    club_id: str
    club_name: str
    user_name: str
    plan: str
    expires_in: int


class TokenPayload(BaseModel):
    user_id: str
    club_id: str
    role: str
    exp: int


def _create_token(user_id: str, club_id: str, role: str) -> tuple[str, int]:
    """Create JWT token. Returns (token, expires_in_seconds)."""
    expire = datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRE_HOURS)
    payload = {
        "sub": user_id,
        "club_id": club_id,
        "role": role,
        "exp": expire,
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token, JWT_EXPIRE_HOURS * 3600


def verify_token(token: str) -> TokenPayload:
    """Verify and decode JWT token."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return TokenPayload(
            user_id=payload["sub"],
            club_id=payload["club_id"],
            role=payload["role"],
            exp=payload["exp"],
        )
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido o expirado.")


async def get_current_user(request: Request) -> TokenPayload:
    """FastAPI dependency: extract and verify JWT from Authorization header."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token de autenticación requerido.")
    token = auth_header.removeprefix("Bearer ")
    return verify_token(token)


async def get_current_club_id(user: TokenPayload = Depends(get_current_user)) -> uuid.UUID:
    """FastAPI dependency: extract club_id from authenticated user."""
    return uuid.UUID(user.club_id)


@router.post("/login", response_model=LoginResponse)
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """Authenticate user with email/password. Returns JWT token."""
    result = await db.execute(select(User).where(User.email == request.email))
    user = result.scalar_one_or_none()

    if not user or not bcrypt.verify(request.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Email o contraseña incorrectos.")

    # Get club info
    club_result = await db.execute(select(Club).where(Club.id == user.club_id))
    club = club_result.scalar_one_or_none()

    if not club or not club.active:
        raise HTTPException(status_code=403, detail="La suscripción del club no está activa.")

    role = user.role.value if hasattr(user.role, "value") else str(user.role)
    token, expires_in = _create_token(
        user_id=str(user.id),
        club_id=str(user.club_id),
        role=role,
    )

    plan = club.plan.value if hasattr(club.plan, "value") else str(club.plan)

    return LoginResponse(
        access_token=token,
        club_id=str(club.id),
        club_name=club.name,
        user_name=user.name,
        plan=plan,
        expires_in=expires_in,
    )


@router.get("/me")
async def get_me(user: TokenPayload = Depends(get_current_user)):
    """Return current authenticated user info from token."""
    return {
        "user_id": user.user_id,
        "club_id": user.club_id,
        "role": user.role,
    }
