# 🚀 RFAF ANALYTICS PLATFORM — CONTEXT PRIMER v2.0
## Pega este documento completo al INICIO de cualquier nueva conversación con Claude Opus 4.6

---

## 👤 QUIÉN SOY

Soy **Antonio Pallarés**, asesor estratégico de la **Real Federación Aragonesa de Fútbol (RFAF)**, con sede en Zaragoza, España. Trabajo directamente con el presidente **Manuel Torralba** en la digitalización e innovación de la federación.

---

## 🎯 EL PROYECTO

**RFAF Analytics Platform** — Primera plataforma SaaS de análisis táctico de fútbol con IA para clubes amateur y semiprofesionales aragoneses (Tercera RFEF → Regional Preferente).

**Contexto estratégico:** Zaragoza es sede FIFA 2030 + Capital Europea del Deporte 2027.

**Propuesta de valor única:**
- Analiza vídeos de YouTube **directamente** (sin descarga, sin hardware)
- Genera informes tácticos completos en **15 minutos** por ~**0.55€**
- Canal de distribución: ~280 clubes aragoneses via RFAF → **CAC = 0€**
- Margen bruto: **~95.5%**

---

## 🏗️ ARQUITECTURA DECIDIDA (NO cambiar sin consultar)

```
YouTube URL
    ↓
Gemini 2.5 Flash API    ← URL nativa, sin descarga, ~0.49€/partido, ~4 min
    ↓ JSON táctico ~800 eventos
Métricas avanzadas      ← soccer_xg, socceraction (VAEP/OBV), PPDA, Field Tilt
    ↓
Visualizaciones         ← mplsoccer: shot maps, heatmaps, pass networks, pizza radars
    ↓
Claude Sonnet 4.6       ← análisis cualitativo en español, narrativa, recomendaciones
    ↓
PDF (ReportLab) + Web (Next.js) + Email (Resend)
```

**Modelos en producción:**
- Análisis táctico: `claude-sonnet-4-6`
- Chatbot rápido: `claude-haiku-4-5-20251001`
- **NUNCA** `claude-opus-4-6` en producción automática (coste 10x)
- Vídeo: `gemini-2.5-flash` (NUNCA gemini-pro ni gemini-ultra en automático)

---

## 📦 STACK TECNOLÓGICO (FIJO)

| Capa | Tecnología |
|---|---|
| Backend | Python 3.11 + FastAPI + SQLAlchemy 2.0 |
| Base de datos | PostgreSQL 16 + AsyncPG |
| Cola asíncrona | Celery 5.x + Redis 7.x |
| Frontend | Next.js 15 + React 19 + Tailwind + Recharts |
| Pagos | Stripe |
| Email | Resend |
| Storage | Cloudflare R2 (compatible S3) |
| Deploy backend | Docker + Railway (o Render) |
| Deploy frontend | Vercel |
| Monitorización | Sentry + PostHog |

---

## 🔗 REPOS GITHUB INTEGRADOS

| Repo | Servicio en el proyecto | Estado |
|---|---|---|
| mplsoccer (andrewRowlinson) | visualization_service.py | ✅ Integrado |
| soccer_xg (ML-KULeuven) | xg_service.py | ✅ Integrado |
| socceraction / VAEP (ML-KULeuven) | xg_service.py | ✅ Integrado |
| StatsBomb Open Data | data_service.py | ✅ Integrado |
| FoTD Passing Networks | visualization_service.py | ✅ Integrado |
| AthleteLoadMonitor (SaxionAMI) | injury_service.py | ✅ Integrado |
| YOLOv8 + ByteTrack | tracking_service.py | 🔮 Fase 3 |
| SoccerNet/sn-gamestate (CVPR'24) | tracking_service.py | 🔮 Fase 3 |
| football2vec | — | 🔮 Fase 4 |

---

## 📁 ESTRUCTURA DEL PROYECTO (ya construida)

```
rfaf-analytics/
├── CLAUDE.md                    ← Instrucciones maestras (leer siempre primero)
├── .env                         ← Variables de entorno (de .env.example)
├── docker-compose.yml           ← postgres + redis + backend + celery + flower
├── requirements.txt             ← 50+ dependencias
├── .gitignore
│
├── backend/
│   ├── main.py                  ← FastAPI entry point
│   ├── database.py              ← AsyncPG + create_tables()
│   ├── models.py                ← Club, User, Match, MatchAnalysis, Player, ScoutReport, PlayerPhysical
│   │
│   ├── routers/
│   │   ├── analyze.py           ← POST /api/analyze/{match|rival|scout}
│   │   ├── reports.py           ← GET /api/reports
│   │   ├── clubs.py             ← CRUD + Auth JWT + Stripe portal
│   │   └── webhooks.py          ← Stripe webhooks (idempotente)
│   │
│   ├── services/
│   │   ├── gemini_service.py    ← Gemini 2.5 Flash + caché Redis 30 días
│   │   ├── claude_service.py    ← Claude Sonnet/Haiku + system prompts dinámicos
│   │   ├── visualization_service.py  ← mplsoccer: 6 tipos de gráficas
│   │   ├── xg_service.py        ← xG XGBoost + PSxG + VAEP + PPDA + Field Tilt
│   │   ├── tracking_service.py  ← YOLOv8 + ByteTrack + K-means + perspectiva
│   │   ├── data_service.py      ← StatsBomb + benchmarks liga aragonesa
│   │   ├── injury_service.py    ← ACWR + score riesgo lesión 0-100
│   │   ├── pdf_service.py       ← ReportLab + gráficas mplsoccer en PDF
│   │   ├── email_service.py     ← Resend + HTML templates
│   │   └── storage_service.py   ← Cloudflare R2 con boto3
│   │
│   ├── workers/
│   │   └── tasks.py             ← Celery: analyze_match, analyze_rival, scout, weekly_report
│   │
│   ├── prompts/
│   │   ├── INFORME_PARTIDO.md   ← System prompt para informe de partido (12 secciones)
│   │   ├── ANALISIS_RIVAL.md    ← System prompt para P1 análisis de rivales
│   │   └── SCOUTING_FORMACION_ENTRENAMIENTO.md  ← System prompts P2+P3
│   │
│   └── ml_models/               ← Modelos ML (en .gitignore, no en Git)
│
└── frontend/                    ← Next.js 15 (conectar al backend en Sprint 5-6)
    └── [4 productos React con 12 tabs ya construidos como .jsx]
```

---

## 🛠️ LOS 4 PRODUCTOS (demos estáticas ya construidas)

| Producto | Archivo .jsx | Estado |
|---|---|---|
| P1 — Análisis de Rivales | rfaf_p1_rivales_v2.jsx (996 líneas) | ✅ Demo estática |
| P2 — Scouting de Jugadores | rfaf_p2_scouting_v2.jsx (729 líneas) | ✅ Demo estática |
| P3 — Formación Entrenadores | rfaf_p3_p4_v2.jsx (P3 parte) | ✅ Demo estática |
| P4 — SaaS Dashboard RFAF | rfaf_p3_p4_v2.jsx (P4 parte) | ✅ Demo estática |
| Informe de Partido | rfaf_ultimate_report.jsx (1.342 líneas) | ✅ Demo estática |

---

## 💳 PLANES Y PRECIOS

| Plan | Precio | Límite | Target |
|---|---|---|---|
| BÁSICO | 49€/mes | 3 informes/mes | Clubs regionales |
| PROFESIONAL | 149€/mes | Ilimitado | 3ª RFEF / Reg. Preferente |
| FEDERADO | 104€/mes (-30%) | Ilimitado | Bonificados por RFAF |

---

## 📊 ESTADO ACTUAL (Abril 2026)

- **Fase 1 COMPLETADA:** MCP Server, demos React, servicios backend, documentación
- **Clubes activos:** 5 · **MRR:** ~651€ · **ARR:** ~7.812€ · **Margen:** ~94%
- **Siguiente:** Fase 2 (backend real + beta 5 clubes)

---

## 🚨 REGLAS DE DESARROLLO OBLIGATORIAS

1. **No inventar datos tácticos.** Si Gemini no detectó el dato → mostrar "No disponible"
2. **Caché siempre.** URL ya analizada en 30 días → reutilizar JSON de Redis
3. **Idempotencia en Celery.** Tasks con max_retries no deben crear duplicados
4. **RLS PostgreSQL.** Un club NUNCA ve datos de otro. Verificar club_id en cada query
5. **Errores en español.** El entrenador ve mensajes claros, nunca stack traces
6. **PDF en background.** El endpoint devuelve `analysis_id` inmediatamente
7. **Logs estructurados.** structlog con: club_id, analysis_id, model, cost_eur, duration_s
8. **mplsoccer siempre en Agg.** `matplotlib.use("Agg")` en el servidor (sin display)
9. **Tests de integración** para cada endpoint con datos StatsBomb Open Data
10. **Validar URLs YouTube** antes de encolar. URL privada → error claro al usuario

---

## ⚙️ VARIABLES DE ENTORNO NECESARIAS

```bash
ANTHROPIC_API_KEY=sk-ant-...        # Claude Sonnet 4.6
GOOGLE_API_KEY=AIza...              # Gemini 2.5 Flash
DATABASE_URL=postgresql+asyncpg://... # PostgreSQL
REDIS_URL=redis://localhost:6379/0   # Redis + Celery
STRIPE_SECRET_KEY=sk_live_...        # Pagos
STRIPE_WEBHOOK_SECRET=whsec_...
RESEND_API_KEY=re_...               # Email automático
CLOUDFLARE_R2_ACCESS_KEY=...        # Storage
CLOUDFLARE_R2_SECRET_KEY=...
CLOUDFLARE_R2_BUCKET=rfaf-analytics
CLOUDFLARE_R2_ENDPOINT=https://....r2.cloudflarestorage.com
CLOUDFLARE_R2_PUBLIC_URL=https://cdn.rfaf-analytics.es
NEXTAUTH_SECRET=...                 # Frontend auth
JWT_SECRET=...
```

---

## 🎯 FASE ACTUAL Y PRIMERA TAREA

**Estamos en: Sprint 1 de la Fase 2**

**Primera tarea:** Completar el backend real y conectarlo con Gemini y Claude.

**Orden de implementación:**
1. `docker-compose up -d` → verificar que postgres y redis arrancan
2. Completar `database.py` → `create_tables()` async funcional
3. Test pipeline real: URL YouTube → Gemini → JSON → Claude → Markdown
4. Endpoint GET /api/reports/{id} con datos reales de PostgreSQL
5. Autenticación JWT funcional
6. Stripe checkout + webhooks
7. PDF con gráficas mplsoccer reales
8. Despliegue Railway/Vercel

---

## 📎 CONSTRAINT INSTITUCIONAL CRÍTICO

La Ciudad del Fútbol Aragonés "Óscar Fle" es **propiedad de la RFEF** (no RFAF), con uso cedido. Para financiaciones mayores (FIFA Forward 3.0, UEFA HatTrick VI, PRTR) que involucren la infraestructura, se necesita un **acuerdo formal RFEF-RFAF**. Gestionarlo antes de Q3 2026.

---

*RFAF Analytics Platform v2.0 · Zaragoza · Abril 2026*
*Este documento se actualiza con cada sesión de desarrollo*
