# RFAF Analytics Platform - Instrucciones para Claude Code

## Contexto
Plataforma SaaS de analisis tactico de futbol con IA para la Real Federacion Aragonesa de Futbol (RFAF).
Analiza videos de YouTube con Gemini 2.5 Flash, genera metricas con soccer_xg/VAEP, y produce informes con Claude Sonnet 4.6.

## Arquitectura
YouTube URL -> Gemini 2.5 Flash (JSON tactico) -> Metricas (xG, PPDA, VAEP) -> Visualizaciones (mplsoccer) -> Claude Sonnet 4.6 (analisis) -> PDF + Web + Email

## Stack
- Backend: Python 3.11 + FastAPI + SQLAlchemy 2.0 + AsyncPG
- DB: PostgreSQL 16 + Redis 7.x
- Cola: Celery 5.x
- Frontend: Next.js 16 + React 19 + Tailwind + Recharts
- Deploy: Railway (backend) + Vercel (frontend)

## Reglas obligatorias
1. No inventar datos tacticos - si Gemini no lo detecto, mostrar "No disponible"
2. Cache siempre - URL ya analizada en 30 dias reutiliza Redis
3. Idempotencia en Celery - max_retries sin duplicados
4. RLS PostgreSQL - un club NUNCA ve datos de otro
5. Errores en espanol - mensajes claros, nunca stack traces
6. PDF en background - devolver analysis_id inmediatamente
7. Logs con structlog - campos: club_id, analysis_id, model, cost_eur, duration_s
8. mplsoccer en Agg - matplotlib.use("Agg") en servidor
9. Tests de integracion para cada endpoint
10. Validar URLs YouTube antes de encolar

## Modelos IA (produccion)
- Analisis tactico: claude-sonnet-4-6
- Chatbot rapido: claude-haiku-4-5-20251001
- NUNCA claude-opus-4-6 en produccion automatica (coste 10x)
- Video: gemini-2.5-flash (NUNCA gemini-pro ni ultra en automatico)

## Estado actual
- Fase: Sprints 1-9 COMPLETADOS
- Clubes activos: 5 | MRR: ~651 EUR | Margen: ~94%
- Siguiente paso: validacion con clubes piloto + lanzamiento publico

## Sprints completados (1-9)

### Sprint 1 — Infraestructura base DONE
- Docker Compose: Postgres 16 + Redis 7 + Backend + Celery + Flower
- 7 modelos SQLAlchemy: Club, User, Match, MatchAnalysis, Player, ScoutReport, PlayerPhysical
- Alembic migraciones (3 versiones: schema inicial, feedbacks table, widen current_step)
- Redis cache con TTL 30 dias (key = SHA256(url))

### Sprint 2 — DevOps + Celery DONE
- CI/CD GitHub Actions: lint + tests en cada PR
- Celery 5 con max_retries=3, acks_late=True, idempotente
- GET /api/health con check de DB, Redis y APIs
- Deploy Railway (backend) + Vercel (frontend) configurado

### Sprint 3 — Pipeline IA real DONE
- GeminiService: analyze_youtube_video() con cache Redis
- xG model con xgboost entrenado (data_service.py + xg_service.py)
- mplsoccer visualizations: shot map, heatmap, red de pases (PNG base64)
- Claude Sonnet 4.6: generate_match_report() con prompt 12 secciones
- analyze_match_task Celery: pipeline completo Gemini->xG->viz->Claude

### Sprint 4 — Auth + PDF + Email + Stripe DONE
- JWT Auth con python-jose + passlib[bcrypt]
- RLS: club_id en todas las queries (ningun club ve datos de otro)
- PDF con ReportLab + branding RFAF (pdf_service.py)
- Email automatico al completar analisis (email_service.py con Resend)
- Stripe Checkout: planes Basico/Pro/Federado (clubs.py)

### Sprint 5 — Stripe webhooks + Storage DONE
- Webhooks Stripe idempotentes: checkout.completed, invoice.paid, subscription.deleted
- Cloudflare R2 storage para PDFs (storage_service.py, boto3)
- Resumen semanal automatico (Celery beat)

### Sprint 6 — Frontend conectado DONE
- app/analyze/page.tsx: formulario URL + polling en tiempo real
- app/analyze/[id]/page.tsx: barra progreso + estado Celery
- lib/api.ts: cliente tipado para todos los endpoints

### Sprint 7 — Login + Chatbot + Panel admin DONE
- app/reports/page.tsx: lista informes del club con filtros
- app/reports/[id]/page.tsx: informe 12 tabs + chatbot tactico (Haiku)
- Panel administracion RFAF con datos reales (MRR, clubes, pipeline)
- BETA-01: onboarding 5 clubes piloto iniciado

### Sprint 8 — Produccion y metricas DONE
- BETA-03: backend/routers/feedback.py — POST /api/feedback + GET /api/feedback con filtro club
- BETA-03: frontend/app/feedback/page.tsx — formulario feedback con categorias y estrellas
- BETA-04: backend/routers/admin.py — GET /api/admin/dashboard (MRR real, costes IA, margen, avg_rating)
- BETA-05: backend/tests/locustfile.py — load test Locust 20 usuarios simultaneos
- OPS-05: backend/scripts/backup_postgres.py — backup pg_dump + gzip + upload R2
- CLI: backend/scripts/onboard_club.py — onboarding completo (Club + User + email bienvenida)
- Modelo Feedback en models.py + migracion Alembic 3cd6c35f

### Sprint 9 — PostHog tracking en vivo + Production hardening DONE
- BETA-02: backend/services/tracking_service.py — PostHog completo (8 eventos: analysis_started/completed/failed, report_viewed, pdf_downloaded, chatbot_query, feedback_submitted, club_subscribed/cancelled)
- Tracking integrado en: analyze.py, reports.py, feedback.py, webhooks.py, workers/tasks.py
- POST /api/reports/{id}/chat — chatbot tactico Haiku con tracking y logs
- GET /api/health mejorado — check real de DB + Redis + estado PostHog
- frontend/lib/posthog.ts — cliente PostHog frontend (lazy-init, no SSR)
- railway.toml — config deployment Railway (backend + worker + beat)
- .env.example actualizado — POSTHOG_HOST, ALLOWED_ORIGINS, NEXT_PUBLIC_* vars
- backend/tests/test_sprint9.py — tests integracion (health, chat 404, tracking silent-fail)
- CORS mejorado — ALLOWED_ORIGINS configurable desde env (no mas wildcard en prod)

## Archivos clave por funcionalidad

### Backend API
- backend/main.py — FastAPI app, CORS, lifespan, routers
- backend/models.py — 8 modelos SQLAlchemy (+ Feedback, FeedbackCategory)
- backend/database.py — AsyncEngine, get_db, create_tables, drop_tables
- backend/routers/analyze.py — POST /api/analyze/match + GET /api/analyze/status/{id}
- backend/routers/clubs.py — CRUD clubes + Stripe Checkout
- backend/routers/reports.py — lista + detalle + PDF download + POST /chat (chatbot Haiku)
- backend/routers/admin.py — GET /api/admin/dashboard
- backend/routers/feedback.py — POST/GET /api/feedback
- backend/routers/webhooks.py — POST /api/webhooks/stripe (idempotente)

### Servicios
- backend/services/gemini_service.py — analyze_youtube_video() con cache Redis
- backend/services/claude_service.py — generate_match_report() Sonnet 4.6
- backend/services/xg_service.py — modelo xG XGBoost
- backend/services/visualization_service.py — mplsoccer charts PNG base64
- backend/services/pdf_service.py — ReportLab PDF con branding RFAF
- backend/services/email_service.py — Resend email con adjunto PDF
- backend/services/storage_service.py — Cloudflare R2 (boto3)
- backend/services/data_service.py — predict_xg, post-procesado shots
- backend/services/injury_service.py — ACWR injury risk model
- backend/services/tracking_service.py — PostHog analytics

### Workers
- backend/workers/tasks.py — analyze_match_task Celery (7 pasos, max_retries=3)

### Scripts operaciones
- backend/scripts/onboard_club.py — CLI onboarding club nuevo
- backend/scripts/backup_postgres.py — backup pg_dump -> gzip -> R2

### Tests / QA
- backend/tests/locustfile.py — load test Locust 20 usuarios

### Frontend
- frontend/app/page.tsx — landing/dashboard
- frontend/app/analyze/page.tsx — formulario + polling
- frontend/app/analyze/[id]/page.tsx — progreso analisis
- frontend/app/reports/page.tsx — lista informes
- frontend/app/reports/[id]/page.tsx — informe 12 tabs + chatbot Haiku
- frontend/app/feedback/page.tsx — formulario feedback beta
- frontend/lib/api.ts — cliente API tipado

## Documentacion
- docs/RFAF_SCRUM_PLAN.md - Plan Scrum completo (8 sprints)
- docs/GUIA_DESARROLLO_0_100.md - Guia paso a paso
- docs/GUIA_HERRAMIENTAS_CLAUDE.md - Como usar Claude Code, Cowork, etc.
- docs/RFAF_ONBOARDING_OPUS46.docx - Onboarding
- INICIO_RFAF_OPUS46.md - Context primer para sesiones Claude.ai
