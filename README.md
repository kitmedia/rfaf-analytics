# RFAF Analytics Platform

Plataforma SaaS de análisis táctico de fútbol con IA para la Real Federación Aragonesa de Fútbol (RFAF). Analiza vídeos de YouTube de partidos, genera métricas avanzadas (xG, PPDA, Field Tilt) con modelos propios, crea visualizaciones con mplsoccer y produce informes PDF con Claude Sonnet 4.6.

**Estado:** Sprint 8 en curso · 5 clubes activos · MRR ~651 EUR

---

## Stack tecnológico

| Capa | Tecnología |
|------|-----------|
| Backend API | Python 3.11 + FastAPI 0.115 |
| Base de datos | PostgreSQL 16 + SQLAlchemy 2.0 (async) |
| Migraciones | Alembic |
| Cola de tareas | Celery 5 + Redis 7 |
| Análisis IA | Gemini 2.5 Flash (vídeo) + Claude Sonnet 4.6 (informes) |
| Métricas fútbol | mplsoccer + socceraction + xgboost |
| PDF | ReportLab |
| Email | Resend |
| Pagos | Stripe Checkout + Webhooks |
| Storage | Cloudflare R2 (S3-compatible) |
| Frontend | Next.js 16 + React 19 + TypeScript + Tailwind 4 + Recharts |
| Monitoring | Sentry + PostHog + structlog |
| Deploy | Railway (backend + Celery) + Vercel (frontend) |

---

## Arquitectura del pipeline

```
YouTube URL
    │
    ▼
Gemini 2.5 Flash ──► JSON táctico (shots, passes, formations)
    │                    │
    │                    ▼
    │              Redis cache (30 días, key=SHA256(url))
    │
    ▼
xG model (xgboost)  ──► xG por disparo calibrado
    │
    ▼
mplsoccer ──► shot map + heatmap + red de pases (PNG base64)
    │
    ▼
Claude Sonnet 4.6 ──► Informe táctico markdown (12 secciones)
    │
    ▼
ReportLab ──► PDF con branding RFAF
    │
    ├──► Cloudflare R2 (almacenamiento)
    ├──► Email Resend (entrega automática)
    └──► PostgreSQL (estado, métricas, coste)
```

---

## Estructura del proyecto

```
rfaf-analytics/
├── backend/
│   ├── main.py                  # FastAPI app, lifespan, CORS
│   ├── models.py                # 7 modelos SQLAlchemy: Club, User, Match, MatchAnalysis, Player, ScoutReport, PlayerPhysical
│   ├── database.py              # AsyncEngine + get_db dependency
│   ├── routers/
│   │   ├── analyze.py           # POST /api/analyze/match + GET /api/analyze/status/{id}
│   │   ├── clubs.py             # CRUD clubes + Stripe Checkout
│   │   ├── reports.py           # GET /api/reports + /api/reports/{id} + PDF
│   │   ├── admin.py             # GET /api/admin/dashboard (Sprint 8)
│   │   └── webhooks.py          # POST /api/webhooks/stripe (idempotente)
│   ├── services/
│   │   ├── gemini_service.py    # Análisis vídeo YouTube con Gemini 2.5 Flash
│   │   ├── claude_service.py    # Generación informes con Claude Sonnet 4.6
│   │   ├── xg_service.py        # Modelo xG con xgboost
│   │   ├── visualization_service.py  # mplsoccer: shot maps, heatmaps, pases
│   │   ├── pdf_service.py       # ReportLab → PDF con branding RFAF
│   │   ├── email_service.py     # Resend: email con PDF adjunto
│   │   ├── storage_service.py   # Cloudflare R2 upload/download
│   │   ├── data_service.py      # Predicción xG + post-procesado
│   │   ├── injury_service.py    # ACWR injury risk model
│   │   └── tracking_service.py  # PostHog analytics
│   ├── workers/
│   │   └── tasks.py             # Celery tasks: analyze_match (pipeline completo, max_retries=3)
│   ├── prompts/
│   │   ├── INFORME_PARTIDO.md   # System prompt para informe táctico (12 secciones)
│   │   ├── ANALISIS_RIVAL.md    # System prompt análisis de rival
│   │   └── SCOUTING_FORMACION_ENTRENAMIENTO.md
│   ├── scripts/
│   │   ├── onboard_club.py      # Onboarding clubes piloto (Sprint 8)
│   │   └── backup_postgres.py   # Backup automático PostgreSQL (Sprint 8)
│   └── tests/
├── frontend/
│   ├── app/
│   │   ├── page.tsx             # Landing / Dashboard
│   │   ├── analyze/
│   │   │   ├── page.tsx         # Formulario análisis + polling en tiempo real
│   │   │   └── [id]/page.tsx    # Resultado análisis con progreso
│   │   ├── reports/
│   │   │   ├── page.tsx         # Lista de informes del club
│   │   │   └── [id]/page.tsx    # Informe completo: 12 tabs + chatbot
│   │   └── feedback/
│   │       └── page.tsx         # Formulario de feedback beta (Sprint 8)
│   └── lib/
│       └── api.ts               # Cliente API tipado para todos los endpoints
├── alembic/                     # Migraciones Alembic
├── docs/
│   ├── RFAF_SCRUM_PLAN.md       # Plan Scrum completo (8 sprints)
│   └── GUIA_DESARROLLO_0_100.md
├── docker-compose.yml           # Postgres 16 + Redis 7 + Backend + Celery + Flower
├── requirements.txt
├── .env.example
└── CLAUDE.md                    # Instrucciones para Claude Code
```

---

## Levantar el entorno local

### Requisitos previos
- Docker Desktop instalado y corriendo
- Python 3.11+
- Node.js 20+

### 1. Variables de entorno

```bash
cp .env.example .env
# Edita .env con tus API keys:
# ANTHROPIC_API_KEY, GOOGLE_API_KEY, STRIPE_SECRET_KEY, RESEND_API_KEY
```

### 2. Levantar infraestructura con Docker

```bash
docker-compose up -d postgres redis
# Esperar ~10s a que Postgres esté healthy
```

### 3. Backend (desarrollo local)

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Crear tablas (via lifespan al arrancar, o con Alembic)
alembic upgrade head

# Arrancar FastAPI
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

# En otro terminal: arrancar Celery worker
celery -A backend.workers.tasks worker --loglevel=info --concurrency=4
```

### 4. Frontend

```bash
cd frontend
npm install
npm run dev
# → http://localhost:3000
```

### 5. Todo con Docker (opción completa)

```bash
docker-compose up -d
# Backend:  http://localhost:8000
# Frontend: http://localhost:3000  (arrancar manualmente)
# Flower:   http://localhost:5555  (monitor Celery)
# Postgres: localhost:5432
```

---

## API Endpoints

### Análisis de partidos

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `POST` | `/api/analyze/match` | Encola análisis de partido. Devuelve `analysis_id` inmediatamente. |
| `GET` | `/api/analyze/status/{analysis_id}` | Estado del análisis + progreso (0-100%) |

**Ejemplo POST /api/analyze/match:**
```json
{
  "youtube_url": "https://www.youtube.com/watch?v=XXXXXXXXXXX",
  "equipo_local": "SD Huesca B",
  "equipo_visitante": "Real Zaragoza B",
  "competicion": "Segunda RFEF Grupo 4",
  "club_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

### Informes

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `GET` | `/api/reports?club_id={id}` | Lista informes del club (paginados) |
| `GET` | `/api/reports/{analysis_id}` | Informe completo con contenido markdown + charts |
| `GET` | `/api/reports/{analysis_id}/pdf` | Descarga PDF con branding RFAF |

### Clubes y pagos

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `POST` | `/api/clubs` | Crear nuevo club |
| `GET` | `/api/clubs/{club_id}` | Datos del club |
| `POST` | `/api/clubs/{club_id}/checkout` | Crear sesión Stripe Checkout |
| `POST` | `/api/webhooks/stripe` | Webhook Stripe (idempotente) |

### Admin y monitoring (Sprint 8)

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `GET` | `/api/admin/dashboard` | MRR, clubes activos, análisis del mes, costes IA |
| `POST` | `/api/feedback` | Enviar feedback de club beta |

### Sistema

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `GET` | `/api/health` | Health check |

**Documentación interactiva:** [http://localhost:8000/docs](http://localhost:8000/docs) (Swagger UI)

---

## Planes de suscripción

| Plan | Precio | Análisis/mes | Destinatario |
|------|--------|-------------|-------------|
| Básico | 49 EUR/mes | 3 | Clubes pequeños |
| Profesional | 149 EUR/mes | Ilimitado | Clubes semiprofesionales |
| Federado | 104 EUR/mes (-30%) | Ilimitado | Clubes afiliados RFAF |

---

## Modelos IA utilizados

| Servicio | Modelo | Uso |
|---------|--------|-----|
| Video analysis | `gemini-2.5-flash` | Extrae JSON táctico de vídeos YouTube |
| Informes tácticos | `claude-sonnet-4-6` | Genera informe markdown de 12 secciones |
| Chatbot rápido | `claude-haiku-4-5-20251001` | Responde preguntas sobre el informe |
| xG model | XGBoost local | Calibra probabilidad de gol por disparo |

> **Importante:** `claude-opus-4-6` y `gemini-ultra` **nunca** se usan en producción automática (coste 10x).

---

## Seguridad

- **RLS PostgreSQL:** cada club solo ve sus propios datos (club_id en todas las queries)
- **JWT Auth:** tokens con `python-jose` + `passlib[bcrypt]`
- **Stripe webhooks:** verificación de firma HMAC obligatoria
- **URLs YouTube:** validación con regex antes de encolar
- **CORS:** restringir `allow_origins` en producción

---

## Testing

```bash
# Tests de integración (requiere Postgres + Redis running)
pytest backend/tests/ -v

# Load test con Locust (Sprint 8) — 20 análisis simultáneos
locust -f backend/tests/locustfile.py --host http://localhost:8000 \
  --users 20 --spawn-rate 2 --run-time 120s --headless
```

---

## Sprints completados

| Sprint | Épica | Estado |
|--------|-------|--------|
| Sprint 1 | Infraestructura base (Docker, Postgres, Redis, Alembic) | ✅ Done |
| Sprint 2 | CI/CD, Celery, health check, deploy Railway/Vercel | ✅ Done |
| Sprint 3 | Pipeline IA real: Gemini + xG + mplsoccer + Claude | ✅ Done |
| Sprint 4 | Auth JWT, RLS, PDF + Email, Stripe Checkout | ✅ Done |
| Sprint 5 | Stripe webhooks, Cloudflare R2, resumen semanal | ✅ Done |
| Sprint 6 | Frontend conectado: formulario análisis + polling | ✅ Done |
| Sprint 7 | Login, mis informes, chatbot táctico, panel admin | ✅ Done |
| Sprint 8 | Onboarding beta, admin completo, load test, backup | 🔄 En curso |

---

## Contribuir / Desplegar

- **Backend (Railway):** push a `main` → build Docker automático
- **Frontend (Vercel):** push a `main` → deploy automático, PR → preview URL
- **Variables de entorno en Railway:** igual que `.env.example`

---

*RFAF Analytics Platform · v2.0 · Abril 2026*
