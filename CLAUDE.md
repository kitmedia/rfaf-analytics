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
- Fase: Sprint 8 de Fase 2 (EN CURSO)
- Clubes activos: 5 | MRR: ~651 EUR | Margen: ~94%
- Sprint Goal: rfaf-analytics.es en produccion. 5 clubes activos pagando. MRR real. Metricas en PostHog. Load test superado.

## Sprints completados (1-7)

### Sprint 1 — Infraestructura base DONE
- Docker Compose: Postgres 16 + Redis 7 + Backend + Celery + Flower
- 7 modelos SQLAlchemy: Club, User, Match, MatchAnalysis, Player, ScoutReport, PlayerPhysical
- Alembic migraciones
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

## Sprint 8 — Produccion y metricas (EN CURSO)

### Stories pendientes:
- BETA-03: Formulario feedback estructurado -> POST /api/feedback + app/feedback/page.tsx
- BETA-04: Panel admin completo -> GET /api/admin/dashboard (MRR real, costes IA, alertas)
- BETA-05: Load test -> locust 20 usuarios simultaneos sin errores
- OPS-05: Backup PostgreSQL automatico -> backend/scripts/backup_postgres.py
- FE-Iteraciones-feedback: mejoras frontend basadas en feedback clubes

### Archivos Sprint 8 a crear/completar:
- backend/routers/admin.py — panel admin con metricas reales
- backend/routers/feedback.py — endpoint POST /api/feedback
- backend/scripts/onboard_club.py — script CLI onboarding completo
- backend/scripts/backup_postgres.py — backup pg_dump a Cloudflare R2
- backend/tests/locustfile.py — load test Locust
- frontend/app/feedback/page.tsx — formulario feedback beta

## Documentacion
- docs/RFAF_SCRUM_PLAN.md - Plan Scrum completo (8 sprints)
- docs/GUIA_DESARROLLO_0_100.md - Guia paso a paso
- docs/GUIA_HERRAMIENTAS_CLAUDE.md - Como usar Claude Code, Cowork, etc.
- docs/RFAF_ONBOARDING_OPUS46.docx - Onboarding
- INICIO_RFAF_OPUS46.md - Context primer para sesiones Claude.ai
