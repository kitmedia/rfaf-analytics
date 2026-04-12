"""RFAF Analytics Platform - FastAPI Entry Point"""

import os
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from backend.database import create_tables

logger = structlog.get_logger()

# --- Sentry (OPS-03) ---
SENTRY_DSN = os.getenv("SENTRY_DSN", "")
if SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
    from sentry_sdk.integrations.celery import CeleryIntegration

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        traces_sample_rate=float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.2")),
        environment=os.getenv("ENVIRONMENT", "production"),
        release=os.getenv("RAILWAY_GIT_COMMIT_SHA", "local"),
        integrations=[
            FastApiIntegration(),
            SqlalchemyIntegration(),
            CeleryIntegration(),
        ],
    )
    logger.info("sentry_initialized", dsn=SENTRY_DSN[:20] + "...")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: init tracking. Shutdown: flush PostHog."""
    # En produccion, Alembic gestiona las migraciones via start.sh.
    # create_tables() solo como fallback en desarrollo local.
    if os.getenv("ENVIRONMENT", "development") != "production":
        await create_tables()
    logger.info("rfaf_startup", version="2.0.0")
    yield
    # Flush PostHog events on shutdown
    from backend.services.tracking_service import flush
    flush()
    logger.info("rfaf_shutdown")


app = FastAPI(
    title="RFAF Analytics Platform",
    version="2.0.0",
    description=(
        "Plataforma SaaS de analisis tactico de futbol con IA para la "
        "Real Federacion Aragonesa de Futbol (RFAF).\n\n"
        "## Funcionalidades\n"
        "- Analisis de video YouTube con Gemini 2.5 Flash\n"
        "- Metricas xG, PPDA, Field Tilt con XGBoost\n"
        "- Informes tacticos de 12 secciones con Claude Sonnet 4.6\n"
        "- Chatbot tactico con Claude Haiku 4.5\n"
        "- PDF con branding RFAF + email automatico\n"
        "- Stripe Checkout + billing portal\n\n"
        "## Autenticacion\n"
        "Usa JWT Bearer tokens. Obten un token via `POST /api/auth/login`.\n"
        "Incluye el header `Authorization: Bearer <token>` en cada request protegido."
    ),
    lifespan=lifespan,
    docs_url="/api/docs" if os.getenv("ENVIRONMENT") != "production" else None,
    redoc_url="/api/redoc" if os.getenv("ENVIRONMENT") != "production" else None,
    openapi_url="/api/openapi.json" if os.getenv("ENVIRONMENT") != "production" else None,
    openapi_tags=[
        {"name": "auth", "description": "Autenticacion: login, registro, password reset"},
        {"name": "analyze", "description": "Analisis de partidos via YouTube URL"},
        {"name": "reports", "description": "Informes tacticos completados + chatbot"},
        {"name": "clubs", "description": "CRUD clubes + Stripe Checkout + billing portal"},
        {"name": "admin", "description": "Panel administracion RFAF (MRR, costes, metricas)"},
        {"name": "feedback", "description": "Feedback de clubes beta"},
        {"name": "webhooks", "description": "Webhooks Stripe (idempotentes)"},
    ],
)

# --- Rate Limiting ---
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["60/minute"],
    storage_uri=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
)
app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"detail": "Demasiadas solicitudes. Intenta de nuevo en unos segundos."},
    )

ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:3000,https://rfaf-analytics.es,https://www.rfaf-analytics.es",
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health_check():
    """Health check con estado de dependencias."""
    import redis.asyncio as aioredis
    from backend.database import engine

    checks: dict = {"version": "2.0.0", "status": "ok"}

    # DB check
    try:
        async with engine.connect() as conn:
            await conn.execute(__import__("sqlalchemy").text("SELECT 1"))
        checks["db"] = "connected"
    except Exception as exc:
        checks["db"] = f"error: {exc}"
        checks["status"] = "degraded"

    # Redis check
    redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
    try:
        r = aioredis.from_url(redis_url, socket_connect_timeout=2)
        await r.ping()
        await r.aclose()
        checks["redis"] = "connected"
    except Exception as exc:
        checks["redis"] = f"error: {exc}"
        checks["status"] = "degraded"

    # PostHog configured?
    checks["posthog"] = "configured" if os.getenv("POSTHOG_API_KEY") else "not_configured"

    return checks


from backend.routers import admin, analyze, auth, clubs, feedback, reports, webhooks

app.include_router(auth.router, prefix="/api")
app.include_router(analyze.router, prefix="/api")
app.include_router(reports.router, prefix="/api")
app.include_router(clubs.router, prefix="/api")
app.include_router(webhooks.router, prefix="/api")
app.include_router(admin.router, prefix="/api")
app.include_router(feedback.router, prefix="/api")
