# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

RFAF Analytics Platform — SaaS de analisis tactico de futbol con IA para la Real Federacion Aragonesa de Futbol. Analiza videos de YouTube con Gemini 2.5 Flash, genera metricas (xG, PPDA, VAEP), visualizaciones (mplsoccer), informes con Claude Sonnet 4.6, y entrega PDF + Web + Email.

## Architecture

```
YouTube URL -> Gemini 2.5 Flash (JSON tactico) -> xG/VAEP metrics -> mplsoccer visualizations -> Claude Sonnet 4.6 (informe) -> PDF + Web + Email
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

# Train xG model (first time only)
python -m backend.scripts.train_xg_model

# Lint
ruff check backend/

# Tests (require Postgres + Redis running)
pytest backend/tests/ -v
pytest backend/tests/test_endpoints.py -v          # single file

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
npm run test:e2e  # Playwright e2e tests
```

## Mandatory Rules

1. **No inventar datos tacticos.** Si Gemini no detecto el dato -> mostrar "No disponible"
2. **Cache siempre.** URL ya analizada en 30 dias -> reutilizar JSON de Redis (key = SHA256(url))
3. **Idempotencia en Celery.** Tasks con max_retries no deben crear duplicados
4. **RLS PostgreSQL.** Un club NUNCA ve datos de otro. Verificar `club_id` en cada query
5. **Errores en espanol.** Mensajes claros para entrenadores, nunca stack traces
6. **PDF en background.** El endpoint devuelve `analysis_id` inmediatamente
7. **Logs con structlog.** Campos obligatorios: `club_id`, `analysis_id`, `model`, `cost_eur`, `duration_s`
8. **mplsoccer en Agg.** `matplotlib.use("Agg")` siempre en servidor
9. **Tests de integracion** para cada endpoint
10. **Validar URLs YouTube** antes de encolar
11. **Rate limiting.** slowapi: 60/min global, 5/min analyze, 10/min login, 3/min register

## AI Model Constraints

| Use case | Model | Notes |
|----------|-------|-------|
| Analisis tactico (informes) | `claude-sonnet-4-6` | Prompt 12 secciones en `backend/prompts/` |
| Chatbot rapido | `claude-haiku-4-5-20251001` | Preguntas sobre informes |
| Video analysis | `gemini-2.5-flash` | Extrae JSON tactico de YouTube |

**NUNCA** usar `claude-opus-4-6` ni `gemini-pro`/`gemini-ultra` en produccion automatica (coste 10x).

## Key Architecture Details

- **Auth:** JWT con `python-jose` + `passlib[bcrypt]`. Middleware Next.js protege rutas. Password reset con token JWT 1h.
- **Rate Limiting:** slowapi en FastAPI. 60/min global, 5/min analyze, 10/min login, 3/min register/forgot-password.
- **Payments:** Stripe Checkout con webhooks idempotentes. Billing portal (`POST /api/clubs/{id}/portal`). Planes: Basico (49 EUR), Profesional (149 EUR), Federado (104 EUR, -30%).
- **Storage:** PDFs en Cloudflare R2 via boto3 (S3-compatible).
- **Email:** Resend — analisis started, report ready, password reset, weekly summary.
- **Monitoring:** Sentry SDK (FastAPI+SQLAlchemy+Celery) + PostHog (8 tracked events) + structlog.
- **CI:** GitHub Actions — ruff lint -> pytest (with Postgres+Redis services) -> frontend build.
- **E2E Tests:** Playwright (public pages, auth flow, navigation).
- **Dark Mode:** Tailwind @custom-variant dark + ThemeToggle component.
- **xG Model:** XGBoost trained on StatsBomb La Liga data. Auto-trains on first use if missing.

## API Docs (disabled in production)

- Swagger UI: `/api/docs` (dev/staging only)
- ReDoc: `/api/redoc` (dev/staging only)
- OpenAPI JSON: `/api/openapi.json` (dev/staging only)

## Project Status

All 9 sprints completed (40/40 user stories, 223 story points) plus P0/P1/P2 production hardening + comprehensive admin panel + deploy guide.

### Production Hardening
- JWT_SECRET crashes if missing in production (no insecure defaults)
- Alembic migrations fail-fast (no silent fallback)
- Flower removed from Procfile (security)
- Dockerfile: non-root user + .dockerignore
- OpenAPI docs disabled in production (`ENVIRONMENT=production`)
- Uvicorn multi-worker (`WEB_CONCURRENCY` env var)
- Celery beat combined into worker process

### Deploy
- **Guide:** `docs/GUIA_DEPLOY.md` — Railway + Vercel step-by-step
- **Cost:** ~$20-60/mes (Railway Pro + Vercel Hobby)
- **Required env vars:** see `.env.example`

### Frontend Pages
| Route | Description | Auth |
|-------|-------------|------|
| `/` | Landing (public) / Dashboard (authenticated) | Public |
| `/login` | Login form | Public |
| `/signup` | Club registration | Public |
| `/pricing` | 3 plans with Stripe CTA | Public |
| `/forgot-password` | Request password reset | Public |
| `/reset-password` | Set new password (token) | Public |
| `/analyze` | New match analysis form | Protected |
| `/analyze/[id]` | Analysis progress tracker | Protected |
| `/reports` | Reports list with filters | Protected |
| `/reports/[id]` | Full report (12 tabs + chatbot) | Protected |
| `/feedback` | Beta feedback form | Protected |
| `/settings` | Change password, account info | Protected |
| `/admin` | Admin dashboard (MRR, costs) | Admin only |
| `/admin/clubs` | Club CRUD + onboard | Admin only |
| `/admin/users` | User management + password reset | Admin only |
| `/admin/analyses` | Analysis monitoring + retry | Admin only |
| `/admin/tasks` | Celery task monitor (live) | Admin only |
| `/admin/operations` | Backups + xG model training | Admin only |
| `/admin/feedback-admin` | Feedback overview | Admin only |
| `/club/dashboard` | Club dashboard | Protected |
| `/federation/dashboard` | Federation dashboard (RFAF) | Protected |
| `/players` | Players management | Protected |
| `/rivals` | Rivals / upcoming matches | Protected |
| `/upload` | Video upload (alternative to YouTube URL) | Protected |
| `/reports/scouting/[id]` | Scouting report detail | Protected |

### Backend Endpoints
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/auth/register` | Register club + user |
| POST | `/api/auth/login` | JWT login |
| GET | `/api/auth/me` | Current user info |
| POST | `/api/auth/forgot-password` | Request reset email |
| POST | `/api/auth/reset-password` | Reset with token |
| POST | `/api/auth/change-password` | Change (authenticated) |
| POST | `/api/analyze/match` | Queue match analysis |
| GET | `/api/analyze/status/{id}` | Check analysis status |
| GET | `/api/reports` | List reports |
| GET | `/api/reports/{id}` | Report detail |
| POST | `/api/reports/{id}/chat` | Chatbot (Haiku) |
| GET | `/api/reports/{id}/pdf` | Download PDF |
| GET | `/api/clubs/{id}` | Club info |
| POST | `/api/clubs` | Create club |
| POST | `/api/clubs/{id}/checkout` | Stripe Checkout |
| POST | `/api/clubs/{id}/portal` | Stripe billing portal |
| GET | `/api/admin/dashboard` | Admin metrics |
| GET | `/api/admin/clubs` | List clubs (paginated) |
| POST | `/api/admin/clubs` | Onboard club + admin user |
| PUT | `/api/admin/clubs/{id}` | Update club |
| PATCH | `/api/admin/clubs/{id}/toggle` | Toggle active |
| GET | `/api/admin/users` | List users (filter by club) |
| POST | `/api/admin/users` | Create user |
| PUT | `/api/admin/users/{id}` | Update user |
| POST | `/api/admin/users/{id}/reset-password` | Admin reset password |
| GET | `/api/admin/analyses` | List analyses (filter status/club) |
| POST | `/api/admin/analyses/{id}/retry` | Retry failed analysis |
| GET | `/api/admin/tasks` | Celery inspect (active/reserved/scheduled) |
| GET | `/api/admin/tasks/{id}` | Celery task status |
| POST | `/api/admin/backups/trigger` | Trigger DB backup to R2 |
| GET | `/api/admin/backups` | List backups in R2 |
| POST | `/api/admin/ml/train-xg` | Trigger xG model retrain |
| GET | `/api/admin/ml/status` | xG model file status |
| GET | `/api/admin/feedbacks` | List all feedback (paginated) |
| POST | `/api/feedback` | Submit feedback |
| GET | `/api/feedback` | List feedback |
| POST | `/api/webhooks/stripe` | Stripe webhooks |
| GET | `/api/health` | Health check |
| GET | `/api/players` | List players |
| GET | `/api/teams/search` | Search teams |
| GET | `/api/teams/{name}/analyses` | Team analyses history |
| GET | `/api/federation/dashboard` | Federation metrics |
| GET | `/api/federation/export-pdf` | Federation dashboard PDF |
| GET | `/api/federation/conventions` | List federation conventions |
| POST | `/api/federation/conventions` | Create convention |
| GET | `/api/federation/validate-code/{code}` | Validate federation code |
| GET | `/api/federation/channel-metrics` | Channel metrics |
| GET | `/api/upcoming-matches` | List upcoming matches |
| POST | `/api/upcoming-matches/manual` | Add match manually |
| POST | `/api/exercises/mark-complete` | Mark exercise done |
| POST | `/api/exercises/unmark` | Unmark exercise |
| GET | `/api/exercises/by-analysis/{id}` | Exercises for analysis |
| GET | `/api/exercises/weekly-summary` | Weekly exercise summary |
| GET | `/api/exercises/impact` | Exercise impact metrics |
| POST | `/api/upload/video` | Upload video file (alt to YouTube URL) |

## Frontend Note

This project uses **Next.js 16** which has breaking changes from earlier versions. Read `node_modules/next/dist/docs/` before writing frontend code. Heed deprecation notices.
