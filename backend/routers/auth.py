"""Router: /api/auth — Login, register, password reset, JWT verification."""

import os
import uuid
from datetime import datetime, timedelta, timezone

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request
from jose import JWTError, jwt
from slowapi import Limiter
from slowapi.util import get_remote_address
from passlib.hash import bcrypt
from pydantic import BaseModel, EmailStr
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models import Club, User

logger = structlog.get_logger()

router = APIRouter(prefix="/auth", tags=["auth"])
limiter = Limiter(key_func=get_remote_address)

JWT_SECRET = os.getenv("JWT_SECRET", "")
if not JWT_SECRET:
    import warnings
    if os.getenv("ENVIRONMENT", "development") == "production":
        raise RuntimeError("JWT_SECRET no esta configurado. Imposible arrancar en produccion.")
    JWT_SECRET = "dev-only-insecure-secret-do-not-use-in-production"
    warnings.warn("JWT_SECRET no configurado. Usando secreto de desarrollo inseguro.", stacklevel=2)
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
    role: str
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


class RegisterRequest(BaseModel):
    club_name: str
    name: str
    email: EmailStr
    password: str


@router.post("/register", response_model=LoginResponse, status_code=201)
@limiter.limit("3/minute")
async def register(
    request: RegisterRequest,
    req: Request,
    db: AsyncSession = Depends(get_db),
):
    """Register a new club + user. Returns JWT token immediately."""
    # Check duplicate email
    existing = await db.execute(select(User).where(User.email == request.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Ya existe una cuenta con ese email.")

    # Create club (Básico plan by default)
    club = Club(name=request.club_name, email=request.email)
    db.add(club)
    await db.flush()

    # Create user
    user = User(
        club_id=club.id,
        email=request.email,
        password_hash=bcrypt.hash(request.password),
        name=request.name,
    )
    db.add(user)
    await db.flush()

    token, expires_in = _create_token(
        user_id=str(user.id),
        club_id=str(club.id),
        role=user.role.value,
    )

    return LoginResponse(
        access_token=token,
        club_id=str(club.id),
        club_name=club.name,
        user_name=user.name,
        role=user.role.value,
        plan=club.plan.value,
        expires_in=expires_in,
    )


@router.post("/login", response_model=LoginResponse)
@limiter.limit("10/minute")
async def login(
    request: LoginRequest,
    req: Request,
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
        role=role,
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


# --- Password Reset ---

RESET_TOKEN_EXPIRE_HOURS = 1


def _create_reset_token(user_id: str) -> str:
    """Create a short-lived JWT for password reset."""
    expire = datetime.now(timezone.utc) + timedelta(hours=RESET_TOKEN_EXPIRE_HOURS)
    return jwt.encode(
        {"sub": user_id, "purpose": "reset", "exp": expire},
        JWT_SECRET,
        algorithm=JWT_ALGORITHM,
    )


def _verify_reset_token(token: str) -> str:
    """Verify reset token, return user_id."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        if payload.get("purpose") != "reset":
            raise JWTError("Not a reset token")
        return payload["sub"]
    except JWTError:
        raise HTTPException(status_code=400, detail="Enlace de recuperacion invalido o expirado.")


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


@router.post("/forgot-password")
@limiter.limit("3/minute")
async def forgot_password(
    request: ForgotPasswordRequest,
    req: Request,
    db: AsyncSession = Depends(get_db),
):
    """Send password reset email. Always returns 200 (no email enumeration)."""
    result = await db.execute(select(User).where(User.email == request.email))
    user = result.scalar_one_or_none()

    if user:
        reset_token = _create_reset_token(str(user.id))
        reset_url = os.getenv(
            "FRONTEND_URL", "https://rfaf-analytics.es"
        ) + f"/reset-password?token={reset_token}"

        try:
            from backend.services.email_service import send_password_reset_email
            send_password_reset_email(request.email, reset_url)
        except Exception as exc:
            logger.warning("password_reset_email_failed", error=str(exc))

    # Always 200 to prevent email enumeration
    return {"message": "Si el email existe, recibiras un enlace de recuperacion."}


@router.post("/reset-password")
@limiter.limit("5/minute")
async def reset_password(
    request: ResetPasswordRequest,
    req: Request,
    db: AsyncSession = Depends(get_db),
):
    """Reset password using token from email."""
    user_id = _verify_reset_token(request.token)

    if len(request.new_password) < 8:
        raise HTTPException(status_code=400, detail="La contrasena debe tener al menos 8 caracteres.")

    new_hash = bcrypt.hash(request.new_password)
    await db.execute(
        update(User).where(User.id == uuid.UUID(user_id)).values(password_hash=new_hash)
    )
    await db.commit()

    logger.info("password_reset_success", user_id=user_id)
    return {"message": "Contrasena actualizada correctamente. Ya puedes iniciar sesion."}


# --- Change Password (authenticated) ---


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


@router.post("/change-password")
async def change_password(
    request: ChangePasswordRequest,
    user: TokenPayload = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Change password for authenticated user."""
    if len(request.new_password) < 8:
        raise HTTPException(status_code=400, detail="La nueva contrasena debe tener al menos 8 caracteres.")

    result = await db.execute(select(User).where(User.id == uuid.UUID(user.user_id)))
    db_user = result.scalar_one_or_none()

    if not db_user or not bcrypt.verify(request.current_password, db_user.password_hash):
        raise HTTPException(status_code=401, detail="La contrasena actual es incorrecta.")

    db_user.password_hash = bcrypt.hash(request.new_password)
    await db.commit()

    logger.info("password_changed", user_id=user.user_id)
    return {"message": "Contrasena actualizada correctamente."}
