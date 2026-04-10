# RFAF ANALYTICS PLATFORM — SCRUM MASTER PLAN v1.0
## Metodología Ágil Scrum · Fase 2 → Despliegue Producción
### 8 Sprints × 2 semanas = 16 semanas (Mayo → Agosto 2026)

---

## 👥 EQUIPO SCRUM

| Rol | Persona/Tool | Responsabilidad |
|---|---|---|
| **Product Owner** | Antonio Pallarés | Priorización backlog, decisiones de negocio, feedback de clubes |
| **Scrum Master** | Claude Opus 4.6 | Facilitar ceremonias, eliminar impedimentos, mantener el proceso |
| **Dev Lead / Arquitecto** | Claude Code CLI | Implementación backend, arquitectura, código de producción |
| **Dev Frontend** | Claude Code CLI | Next.js, componentes React, conectar con backend |
| **QA / DevOps** | Claude Code CLI + Cowork | Tests, CI/CD, despliegue Railway/Vercel |
| **Stakeholder** | Manuel Torralba (RFAF) | Validación institucional, acceso a clubes piloto |

---

## 📋 DEFINICIÓN DE DONE (DoD)

Un User Story está **DONE** cuando:
- [ ] Código implementado y revisado por Claude Code
- [ ] Tests de integración pasando (mínimo 1 test real)
- [ ] Funciona con docker-compose local
- [ ] Sin errores en Sentry staging
- [ ] Documentado en CLAUDE.md si hay cambios de arquitectura
- [ ] PR mergeado a `main`

Un Sprint está **DONE** cuando:
- [ ] Todos los Stories del sprint están en DONE
- [ ] Demo funcional ejecutada con Antonio
- [ ] CLAUDE.md actualizado con el nuevo estado
- [ ] Retrospectiva completada

---

## 🗂️ PRODUCT BACKLOG COMPLETO

### 🔴 ÉPICA 1 — INFRAESTRUCTURA BASE (Sprint 1-2)

| ID | User Story | Story Points | Sprint |
|---|---|---|---|
| INF-01 | Como dev, quiero levantar el entorno completo con `docker-compose up -d` en menos de 5 minutos | 3 | 1 |
| INF-02 | Como dev, quiero que `create_tables()` cree las 7 tablas PostgreSQL (Club, User, Match, MatchAnalysis, Player, ScoutReport, PlayerPhysical) | 5 | 1 |
| INF-03 | Como dev, quiero que Alembic genere y aplique migraciones automáticamente al desplegar | 5 | 1 |
| INF-04 | Como dev, quiero que Redis caché los JSON de Gemini con TTL de 30 días y key MD5(url) | 3 | 1 |
| INF-05 | Como dev, quiero logs estructurados con structlog (campos: club_id, analysis_id, model, cost_eur, duration_s) | 3 | 2 |
| INF-06 | Como dev, quiero que Celery procese las tasks de análisis en background con max_retries=3 | 5 | 2 |
| INF-07 | Como dev, quiero health check en GET /api/health que verifique DB, Redis y APIs externas | 2 | 2 |
| INF-08 | Como dev, quiero CI/CD con GitHub Actions: lint + tests en cada PR | 5 | 2 |

**Total Épica 1: 31 story points**

---

### 🔴 ÉPICA 2 — PIPELINE IA REAL (Sprint 2-3)

| ID | User Story | Story Points | Sprint |
|---|---|---|---|
| IA-01 | Como entrenador, quiero analizar una URL de YouTube real y recibir el JSON táctico de Gemini en <6 min | 8 | 2 |
| IA-02 | Como entrenador, quiero que si la URL ya fue analizada, el sistema use el caché de Redis (sin llamar a Gemini) | 3 | 2 |
| IA-03 | Como entrenador, quiero recibir el análisis cualitativo completo de Claude (12 secciones) basado en el JSON de Gemini | 8 | 3 |
| IA-04 | Como entrenador, quiero ver las métricas xG, PPDA, Field Tilt y xG timeline calculadas con soccer_xg | 5 | 3 |
| IA-05 | Como entrenador, quiero ver los shot maps, heatmaps y red de pases generados con mplsoccer en el informe web | 5 | 3 |
| IA-06 | Como RFAF admin, quiero que el sistema detecte videos privados de YouTube y devuelva error claro en español | 2 | 3 |
| IA-07 | Como dev, quiero que el pipeline Celery registre en PostgreSQL: status, coste Gemini, coste Claude, duración | 3 | 3 |

**Total Épica 2: 34 story points**

---

### 🟡 ÉPICA 3 — AUTENTICACIÓN Y CLUBES (Sprint 3-4)

| ID | User Story | Story Points | Sprint |
|---|---|---|---|
| AUTH-01 | Como entrenador, quiero registrar mi club con email + contraseña y recibir un JWT | 5 | 3 |
| AUTH-02 | Como entrenador, quiero hacer login y acceder al dashboard con mi JWT | 3 | 3 |
| AUTH-03 | Como entrenador, quiero ver mis informes del mes (paginados, filtrados por tipo) | 5 | 4 |
| AUTH-04 | Como RFAF admin, quiero ver todos los clubes, sus planes y su uso mensual | 5 | 4 |
| AUTH-05 | Como sistema, quiero que RLS en PostgreSQL impida que un club vea datos de otro | 8 | 4 |
| AUTH-06 | Como entrenador, quiero que el sistema me avise cuando esté a punto de alcanzar el límite del plan Básico (3/mes) | 3 | 4 |

**Total Épica 3: 29 story points**

---

### 🟡 ÉPICA 4 — PDF Y EMAIL (Sprint 4-5)

| ID | User Story | Story Points | Sprint |
|---|---|---|---|
| PDF-01 | Como entrenador, quiero descargar el informe como PDF con branding RFAF y gráficas de mplsoccer | 8 | 4 |
| PDF-02 | Como entrenador, quiero recibir el PDF por email automáticamente cuando el análisis esté listo | 5 | 4 |
| PDF-03 | Como entrenador, quiero recibir un email inmediato confirmando que mi análisis ha sido encolado | 2 | 5 |
| PDF-04 | Como RFAF admin, quiero que todos los PDFs se almacenen en Cloudflare R2 con URL pública | 3 | 5 |
| PDF-05 | Como entrenador, quiero recibir el resumen semanal automático todos los lunes a las 8:00 | 5 | 5 |

**Total Épica 4: 23 story points**

---

### 🟡 ÉPICA 5 — PAGOS STRIPE (Sprint 5-6)

| ID | User Story | Story Points | Sprint |
|---|---|---|---|
| PAY-01 | Como entrenador, quiero seleccionar un plan (Básico 49€, Pro 149€, Federado 104€) y pagar con Stripe Checkout | 8 | 5 |
| PAY-02 | Como sistema, quiero que los webhooks de Stripe actualicen el plan del club en PostgreSQL de forma idempotente | 8 | 5 |
| PAY-03 | Como entrenador, quiero gestionar mi facturación desde el portal de Stripe (cambiar plan, descargar facturas) | 3 | 6 |
| PAY-04 | Como RFAF admin, quiero que los clubes federados reciban automáticamente el -30% en el checkout | 5 | 6 |
| PAY-05 | Como sistema, quiero que cuando un club cancele, su acceso se limite al plan Básico al final del período | 5 | 6 |

**Total Épica 5: 29 story points**

---

### 🟢 ÉPICA 6 — FRONTEND CONECTADO (Sprint 6-7)

| ID | User Story | Story Points | Sprint |
|---|---|---|---|
| FE-01 | Como entrenador, quiero un formulario web para introducir la URL del partido y verlo analizar en tiempo real (polling) | 8 | 6 |
| FE-02 | Como entrenador, quiero ver el informe interactivo de 12 tabs con datos reales de la API | 8 | 6 |
| FE-03 | Como entrenador, quiero hacer login desde la web y ver mis informes guardados | 5 | 7 |
| FE-04 | Como entrenador, quiero poder descargar el PDF desde la web con un solo clic | 2 | 7 |
| FE-05 | Como entrenador, quiero un chatbot táctico que responda preguntas sobre el informe | 5 | 7 |
| FE-06 | Como RFAF admin, quiero el panel P4 conectado con datos reales de MRR, clubes y pipeline | 5 | 7 |

**Total Épica 6: 33 story points**

---

### 🟢 ÉPICA 7 — BETA PRIVADA 5 CLUBES (Sprint 7-8)

| ID | User Story | Story Points | Sprint |
|---|---|---|---|
| BETA-01 | Como RFAF, quiero onboardear 5 clubes piloto con el flujo completo end-to-end | 5 | 7 |
| BETA-02 | Como RFAF, quiero monitorizar el uso real en PostHog: análisis, PDFs, NPS, coste IA | 5 | 8 |
| BETA-03 | Como entrenador beta, quiero dar feedback estructurado via formulario y ver que el equipo responde en 48h | 3 | 8 |
| BETA-04 | Como RFAF admin, quiero el panel de administración completo con MRR real, pipeline y alertas | 8 | 8 |
| BETA-05 | Como dev, quiero que el sistema aguante 20 análisis simultáneos sin errores (load test) | 5 | 8 |

**Total Épica 7: 26 story points**

---

### 🟢 ÉPICA 8 — DEVOPS Y PRODUCCIÓN (Sprint 2 + 8)

| ID | User Story | Story Points | Sprint |
|---|---|---|---|
| OPS-01 | Como dev, quiero desplegar el backend en Railway con Docker automáticamente en cada push a main | 5 | 2 |
| OPS-02 | Como dev, quiero desplegar el frontend en Vercel con preview por cada PR | 3 | 2 |
| OPS-03 | Como dev, quiero que Sentry capture todos los errores en producción con contexto de club_id | 3 | 3 |
| OPS-04 | Como RFAF admin, quiero que el dominio rfaf-analytics.es apunte correctamente al frontend | 2 | 8 |
| OPS-05 | Como dev, quiero backups automáticos de PostgreSQL diarios en Cloudflare R2 | 5 | 8 |

**Total Épica 8: 18 story points**

---

**TOTAL BACKLOG: 223 story points**

---

## 📅 SPRINT PLANNING

### 🏁 SPRINT 1 — "Cimientos sólidos"
**Fechas:** Semana 1-2 (inicio Mayo 2026)
**Velocidad objetivo:** 28 story points
**Meta:** Entorno completo funcionando + base de datos lista

| Story | Puntos | Asignado a |
|---|---|---|
| INF-01 docker-compose | 3 | Claude Code |
| INF-02 create_tables() | 5 | Claude Code |
| INF-03 Alembic migraciones | 5 | Claude Code |
| INF-04 Redis caché Gemini | 3 | Claude Code |
| OPS-01 Deploy Railway | 5 | Claude Code + Cowork |
| OPS-02 Deploy Vercel preview | 3 | Claude Code |
| AUTH-01 Registro JWT | 5 | Claude Code |

**Sprint Goal:** `docker-compose up -d` funciona. Tablas creadas. Endpoint /api/health verde. Railway deployado.

**Criterios de éxito:**
```bash
docker-compose up -d               # Arranca sin errores
curl http://localhost:8000/api/health  # {"status": "ok", "db": "connected", "redis": "connected"}
docker exec rfaf_postgres psql -U rfaf_user -d rfaf_analytics -c "\dt"  # 7 tablas
```

---

### 🔥 SPRINT 2 — "El pipeline vive"
**Fechas:** Semana 3-4
**Velocidad objetivo:** 30 story points
**Meta:** URL de YouTube real → JSON Gemini → Claude → informe en PostgreSQL

| Story | Puntos | Asignado a |
|---|---|---|
| IA-01 Gemini URL real | 8 | Claude Code |
| IA-02 Caché Redis | 3 | Claude Code |
| INF-05 structlog | 3 | Claude Code |
| INF-06 Celery background | 5 | Claude Code |
| INF-07 Health check completo | 2 | Claude Code |
| INF-08 GitHub Actions CI | 5 | Cowork / Claude Code |
| OPS-03 Sentry staging | 3 | Claude Code |

**Sprint Goal:** Analizar una URL de YouTube real de un partido de Tercera RFEF. Ver el JSON táctico en PostgreSQL. Celery procesando en background.

**Demo del sprint:** Antonio introduce una URL de YouTube de un partido del CD Ejea o SD Tarazona. El sistema devuelve `analysis_id`. En 5 minutos el JSON está en la DB.

---

### ⚡ SPRINT 3 — "Claude habla fútbol"
**Fechas:** Semana 5-6
**Velocidad objetivo:** 35 story points
**Meta:** Informe completo de Claude (12 secciones) + métricas avanzadas

| Story | Puntos | Asignado a |
|---|---|---|
| IA-03 Claude 12 secciones | 8 | Claude Code |
| IA-04 xG, PPDA, Field Tilt | 5 | Claude Code |
| IA-05 mplsoccer charts | 5 | Claude Code |
| IA-06 Detección vídeo privado | 2 | Claude Code |
| IA-07 Registro costes DB | 3 | Claude Code |
| AUTH-02 Login JWT | 3 | Claude Code |
| AUTH-01 Registro (resto) | 4 | Claude Code |
| OPS-03 Sentry prod | 3 | Claude Code |
| IA-StatsBomb | 2 | Claude Code |

**Sprint Goal:** Informe completo end-to-end. El PDF tiene gráficas reales de mplsoccer. El entrenador recibe el email.

---

### 📊 SPRINT 4 — "El dinero entra"
**Fechas:** Semana 7-8
**Velocidad objetivo:** 31 story points
**Meta:** Stripe funcionando + PDF profesional + email automático

| Story | Puntos | Asignado a |
|---|---|---|
| PDF-01 PDF branding RFAF | 8 | Claude Code |
| PDF-02 Email automático | 5 | Claude Code |
| AUTH-03 Ver mis informes | 5 | Claude Code |
| AUTH-04 RFAF admin vista | 5 | Claude Code |
| AUTH-05 RLS PostgreSQL | 8 | Claude Code |

**Sprint Goal:** Un entrenador puede recibir un PDF profesional con gráficas en su email. El admin RFAF puede ver todos los clubes.

---

### 💳 SPRINT 5 — "Cobra sin tocar nada"
**Fechas:** Semana 9-10
**Velocidad objetivo:** 28 story points
**Meta:** Stripe Checkout + webhooks idempotentes + email confirmación

| Story | Puntos | Asignado a |
|---|---|---|
| PAY-01 Stripe Checkout | 8 | Claude Code |
| PAY-02 Webhooks idempotentes | 8 | Claude Code |
| PDF-03 Email encolado | 2 | Claude Code |
| PDF-04 R2 storage | 3 | Claude Code |
| PDF-05 Resumen semanal | 5 | Claude Code |
| AUTH-06 Alerta límite plan | 3 | Claude Code |

**Sprint Goal:** Un club puede suscribirse a un plan y pagar. El webhook activa el plan. El resumen semanal se envía automáticamente los lunes.

---

### 🎨 SPRINT 6 — "La web respira"
**Fechas:** Semana 11-12
**Velocidad objetivo:** 31 story points
**Meta:** Frontend Next.js conectado al backend real

| Story | Puntos | Asignado a |
|---|---|---|
| FE-01 Formulario análisis | 8 | Claude Code |
| FE-02 Informe interactivo real | 8 | Claude Code |
| PAY-03 Portal Stripe | 3 | Claude Code |
| PAY-04 -30% federados | 5 | Claude Code |
| PAY-05 Cancelación automática | 5 | Claude Code |
| AUTH-05 RLS resto | 2 | Claude Code |

**Sprint Goal:** Un entrenador puede ir a rfaf-analytics.es, hacer login, introducir una URL de YouTube y ver su informe completo en la web.

---

### 🤖 SPRINT 7 — "El chat táctico"
**Fechas:** Semana 13-14
**Velocidad objetivo:** 30 story points
**Meta:** Chatbot táctico + panel admin real + beta onboarding

| Story | Puntos | Asignado a |
|---|---|---|
| FE-03 Login + mis informes | 5 | Claude Code |
| FE-04 Descargar PDF | 2 | Claude Code |
| FE-05 Chatbot táctico | 5 | Claude Code |
| FE-06 Panel P4 real | 5 | Claude Code |
| BETA-01 Onboarding 5 clubes | 5 | Antonio + Claude |
| BETA-02 PostHog tracking | 5 | Claude Code |

**Sprint Goal:** Los 5 clubes piloto están usando la plataforma con datos reales. El chatbot responde preguntas tácticas sobre el informe.

---

### 🚀 SPRINT 8 — "Producción y métricas"
**Fechas:** Semana 15-16
**Velocidad objetivo:** 28 story points
**Meta:** Plataforma en producción con 5 clubes activos + métricas

| Story | Puntos | Asignado a |
|---|---|---|
| BETA-03 Formulario feedback | 3 | Antonio + Claude |
| BETA-04 Panel admin completo | 8 | Claude Code |
| BETA-05 Load test 20 análisis | 5 | Claude Code |
| OPS-04 Dominio rfaf-analytics.es | 2 | Cowork |
| OPS-05 Backup PostgreSQL | 5 | Claude Code |
| FE-Iteraciones-feedback | 5 | Claude Code |

**Sprint Goal:** rfaf-analytics.es en producción. 5 clubes activos pagando. MRR real. Métricas en PostHog. Load test superado.

---

## 🎭 CEREMONIAS SCRUM

### Sprint Planning (inicio de cada sprint)
```
Duración: 1-2 horas (una sesión con Opus 4.6)
Participantes: Antonio (PO) + Claude Opus 4.6 (SM) + Claude Code (Dev)

Prompt para iniciar Sprint Planning:
"Claude, vamos a hacer el Sprint Planning del Sprint [N].
El sprint anterior terminó con: [resumen estado].
Los stories seleccionados para este sprint son: [lista].
Por favor, desglosa cada story en tareas técnicas concretas con Claude Code."
```

### Daily Standup (cada sesión de trabajo)
```
Duración: 5 minutos
Formato — responder siempre estas 3 preguntas:

1. ¿QUÉ COMPLETÉ desde la última sesión?
   → [listado de tareas completadas]

2. ¿QUÉ VOY A HACER HOY?
   → [listado de tareas del día]

3. ¿QUÉ IMPEDIMENTOS TENGO?
   → [bloqueos: falta de API key, error en deploy, duda de arquitectura]

Cómo iniciar cada sesión:
"Claude, daily standup. [responder las 3 preguntas].
Continuemos con el Sprint [N], story [ID]."
```

### Sprint Review (fin de cada sprint)
```
Duración: 30-60 minutos (con demo funcional)
Formato:
1. Demo del increment funcionando (no slides, producto real)
2. Repaso de stories: Done / Not Done / Parcial
3. Actualizar el backlog si hay nuevas prioridades
4. Actualizar CLAUDE.md con el nuevo estado

Prompt:
"Claude, Sprint Review Sprint [N].
Demo realizada. Stories completados: [lista].
Stories no completados: [lista + razón].
Actualiza el CLAUDE.md con el nuevo estado del proyecto."
```

### Sprint Retrospective (fin de cada sprint)
```
Duración: 20 minutos
Formato — responder:
1. ¿QUÉ SALIÓ BIEN? (mantener)
2. ¿QUÉ SALIÓ MAL? (mejorar)
3. ¿QUÉ VAMOS A CAMBIAR para el próximo sprint?

Clave: Si Claude Code tardó demasiado en algo, ajustar la estimación.
Si algo no se pudo testear, añadir test al siguiente sprint.
```

---

## 📊 KANBAN BOARD

```
BACKLOG → TODO (sprint) → IN PROGRESS → REVIEW → DONE

Formato de cada tarjeta:
┌─────────────────────────┐
│ [ID] INF-01             │
│ Story: docker-compose   │
│ Puntos: 3               │
│ Sprint: 1               │
│ Asignado: Claude Code   │
│ Status: IN PROGRESS     │
└─────────────────────────┘
```

---

## 📈 BURNDOWN CHART (objetivo)

```
Sprint 1: 28 pts → Velocidad real: [medir]
Sprint 2: 30 pts → Velocidad acumulada: [medir]
...

Velocidad objetivo: 28-35 pts/sprint
Si la velocidad baja de 20 pts: revisar impedimentos en retro
Si supera 35 pts: ajustar estimaciones al alza
```

---

## 🔗 INTEGRACIONES HERRAMIENTAS CLAUDE

### Claude Opus 4.6 (claude.ai)
- Rol: Scrum Master + Arquitecto + Revisor de código
- Cuándo usarlo: Planning, diseño de arquitectura, revisión de decisiones, retros
- Prompt de apertura: Pegar `INICIO_RFAF_OPUS46.md` completo

### Claude Code CLI
- Rol: Implementación técnica
- Cuándo usarlo: Escribir código, ejecutar tests, hacer commits, modificar archivos
- Arrancar con: `claude . --model claude-opus-4-6` desde la raíz del proyecto

### Cowork
- Rol: Automatización de tareas repetitivas y orquestación
- Cuándo usarlo: Deploy automático, reorganización de archivos, ejecutar scripts batch
- Ver guía específica en `GUIA_HERRAMIENTAS_CLAUDE.md`

---

*RFAF Analytics Platform · Plan Scrum v1.0 · Abril 2026*
