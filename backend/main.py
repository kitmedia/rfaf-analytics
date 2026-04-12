"""RFAF Analytics Platform - FastAPI Entry Point"""

import os
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler

from backend.database import create_tables
from backend.limiter import limiter

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
    """Startup: create tables + init tracking. Shutdown: flush PostHog."""
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
    description="Plataforma SaaS de analisis tactico de futbol con IA",
    lifespan=lifespan,
)

# --- Rate limiting ---
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

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


# --- Global exception handler ---
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch unhandled exceptions. Log full details, return safe Spanish message."""
    logger.error(
        "unhandled_exception",
        path=str(request.url.path),
        method=request.method,
        error=str(exc),
        exc_info=True,
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Ha ocurrido un error interno. Por favor, inténtalo de nuevo más tarde."},
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
