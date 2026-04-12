# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

RFAF Analytics Platform — SaaS de análisis táctico de fútbol con IA para la Real Federación Aragonesa de Fútbol. Analiza vídeos de YouTube con Gemini 2.5 Flash, genera métricas (xG, PPDA, VAEP), visualizaciones (mplsoccer), informes con Claude Sonnet 4.6, y entrega PDF + Web + Email.

## Architecture

```
YouTube URL → Gemini 2.5 Flash (JSON táctico) → xG/VAEP metrics → mplsoccer visualizations → Claude Sonnet 4.6 (informe) → PDF + Web + Email
```

- **Backend:** Python 3.11 + FastAPI + SQLAlchemy 2.0 (async) + Celery 5 + Redis 7 + PostgreSQL 16
- **Frontend:** Next.js 16 + React 19 + TypeScript + Tailwind 4 + Recharts
- **Deploy:** Railway (backend + worker + beat) + Vercel (frontend)

The Celery task `analyze_match_task` orchestrates the full pipeline in 7 steps with `max_retries=3` and `acks_late=True`.

## Common Commands

### Backend
```bash
# Infrastructure
docker-compose up -d postgres redis

# Run backend (from project root)
source venv/bin/activate
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

# Celery worker (separate terminal)
celery -A backend.workers.tasks worker --loglevel=info --concurrency=4

# Database migrations
alembic upgrade head                    # apply all
alembic revision --autogenerate -m "description"  # create new

# Lint
ruff check backend/

# Tests (require Postgres + Redis running)
pytest backend/tests/ -v
pytest backend/tests/test_endpoints.py -v          # single file
pytest backend/tests/test_endpoints.py::test_name -v  # single test

# Load test
locust -f backend/tests/locustfile.py --host http://localhost:8000 --users 20 --spawn-rate 2 --run-time 120s --headless
```

### Frontend
```bash
cd frontend
npm install
npm run dev       # http://localhost:3000
npm run build     # production build
npm run lint
```

## Mandatory Rules

1. **No inventar datos tácticos.** Si Gemini no detectó el dato → mostrar "No disponible"
2. **Cache siempre.** URL ya analizada en 30 días → reutilizar JSON de Redis (key = SHA256(url))
3. **Idempotencia en Celery.** Tasks con max_retries no deben crear duplicados
4. **RLS PostgreSQL.** Un club NUNCA ve datos de otro. Verificar `club_id` en cada query
5. **Errores en español.** Mensajes claros para entrenadores, nunca stack traces
6. **PDF en background.** El endpoint devuelve `analysis_id` inmediatamente
7. **Logs con structlog.** Campos obligatorios: `club_id`, `analysis_id`, `model`, `cost_eur`, `duration_s`
8. **mplsoccer en Agg.** `matplotlib.use("Agg")` siempre en servidor
9. **Tests de integración** para cada endpoint
10. **Validar URLs YouTube** antes de encolar

## AI Model Constraints

| Use case | Model | Notes |
|----------|-------|-------|
| Análisis táctico (informes) | `claude-sonnet-4-6` | Prompt 12 secciones en `backend/prompts/` |
| Chatbot rápido | `claude-haiku-4-5-20251001` | Preguntas sobre informes |
| Video analysis | `gemini-2.5-flash` | Extrae JSON táctico de YouTube |

**NUNCA** usar `claude-opus-4-6` ni `gemini-pro`/`gemini-ultra` en producción automática (coste 10x).

## Key Architecture Details

- **Auth:** JWT con `python-jose` + `passlib[bcrypt]`. RLS enforced via `club_id` filtering in all queries.
- **Payments:** Stripe Checkout con webhooks idempotentes (signature verified). Planes: Básico (49€), Profesional (149€), Federado (104€).
- **Storage:** PDFs en Cloudflare R2 via boto3 (S3-compatible).
- **Email:** Resend — envía PDF automáticamente al completar análisis.
- **Monitoring:** Sentry SDK (FastAPI+SQLAlchemy+Celery integrations) + PostHog (8 tracked events) + structlog.
- **CI:** GitHub Actions — ruff lint → pytest (with Postgres+Redis services) → frontend build.
- **Billing Portal:** Stripe billing portal for subscription self-service (`POST /api/clubs/{id}/portal`).

## Sprint Status

All 9 sprints completed (40/40 user stories). See `.claude/worktrees/zen-mestorf/CLAUDE.md` for detailed sprint history.

## Frontend Note

This project uses **Next.js 16** which has breaking changes from earlier versions. Read `node_modules/next/dist/docs/` before writing frontend code. Heed deprecation notices.
