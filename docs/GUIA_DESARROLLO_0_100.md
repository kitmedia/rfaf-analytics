# RFAF ANALYTICS — GUÍA COMPLETA 0 → 100
## De cero a producción paso a paso
### Setup · Desarrollo · Despliegue · Operaciones

---

## 📋 ÍNDICE
1. Prerrequisitos y setup del entorno local
2. Configuración del repositorio Git
3. Sprint 1: Base de datos y entorno
4. Sprint 2: Pipeline IA real
5. Sprint 3: Análisis completo + métricas
6. Sprint 4: PDF + Email + Admin
7. Sprint 5: Stripe y pagos
8. Sprint 6-7: Frontend conectado + chatbot
9. Sprint 8: Beta 5 clubes
10. Despliegue en producción (Railway + Vercel)
11. Operaciones y mantenimiento

---

## 📦 FASE 0 — PRERREQUISITOS

### 0.1 Software a instalar en tu máquina

```bash
# ── macOS (con Homebrew) ──────────────────────────────────────────────
brew install node python@3.11 git docker postgresql redis

# Verificar versiones
node --version          # >= 18.0.0
python3 --version       # >= 3.11.0
git --version           # >= 2.40.0
docker --version        # >= 24.0.0
docker-compose --version # >= 2.20.0

# ── Windows (con WSL2 + Ubuntu) ───────────────────────────────────────
# Instalar WSL2 desde PowerShell admin:
wsl --install
# Luego seguir las instrucciones de macOS dentro de Ubuntu WSL2
```

### 0.2 Instalar herramientas Claude

```bash
# Claude Code CLI
npm install -g @anthropic/claude-code
claude auth login    # Autenticar con cuenta Anthropic

# Cowork: descargar desde https://claude.ai/download (macOS/Windows)
# Claude in Chrome: instalar extensión desde Chrome Web Store
```

### 0.3 Obtener todas las API Keys

**Tiempo: ~45 minutos**

```bash
# 1. Anthropic (Claude) — console.anthropic.com
#    → Settings → API Keys → Create Key
#    Copiar: sk-ant-api03-...

# 2. Google AI (Gemini) — aistudio.google.com
#    → Get API Key → Create API Key in new project
#    Copiar: AIzaSy...

# 3. Stripe — dashboard.stripe.com
#    → Developers → API Keys (modo TEST primero)
#    Copiar: sk_test_... y pk_test_...

# 4. Resend (email) — resend.com
#    → API Keys → Create API Key
#    Copiar: re_...

# 5. Railway (deploy) — railway.app
#    → New Project → crear proyecto vacío
#    → Settings → API → Token
#    Copiar: ...

# 6. Cloudflare R2 — dash.cloudflare.com
#    → R2 → Create Bucket → rfaf-analytics
#    → Manage R2 API Tokens → Create Token
#    Copiar: access_key y secret_key

# 7. Sentry — sentry.io (gratuito)
#    → New Project → FastAPI → Copiar DSN

# 8. PostHog — posthog.com (gratuito hasta 1M eventos)
#    → New Project → Copiar API Key (phc_...)
```

---

## 🏗️ FASE 1 — SETUP DEL PROYECTO

### 1.1 Crear el repositorio

```bash
# En GitHub: crear repositorio privado "rfaf-analytics"
# Luego en tu máquina:
mkdir rfaf-analytics && cd rfaf-analytics
git init
git remote add origin https://github.com/[tu-usuario]/rfaf-analytics.git
```

### 1.2 Organizar todos los archivos descargados de Claude.ai

```bash
# Con Cowork (recomendado):
# Instrucción: "Copia todos los archivos de ~/Downloads/rfaf-outputs/
# a ~/Projects/rfaf-analytics/ manteniendo la estructura de carpetas"

# O manualmente:
cp ~/Downloads/CLAUDE.md ./
cp ~/Downloads/requirements.txt ./
cp ~/Downloads/docker-compose.yml ./
cp ~/Downloads/.env.example ./
cp ~/Downloads/.gitignore ./

mkdir -p backend/{services,workers,routers,prompts,ml_models,data/statsbomb,data/benchmarks}
mkdir -p frontend/{app,components}

cp ~/Downloads/backend/*.py ./backend/
cp ~/Downloads/backend/services/*.py ./backend/services/
cp ~/Downloads/backend/workers/*.py ./backend/workers/
cp ~/Downloads/backend/routers/*.py ./backend/routers/
cp ~/Downloads/backend/prompts/*.md ./backend/prompts/

# Verificar estructura
find . -type f -name "*.py" | sort
```

### 1.3 Configurar variables de entorno

```bash
cp .env.example .env
nano .env   # Editar con las API keys obtenidas en Fase 0

# Verificar que están todas:
grep -E "^[A-Z]" .env | grep "=.*\w" | wc -l
# Debe mostrar al menos 15 variables configuradas
```

### 1.4 Primer arranque con Docker

```bash
docker-compose up -d

# Verificar que todos los servicios arrancan:
docker ps
# Debe mostrar: rfaf_postgres, rfaf_redis, rfaf_backend, rfaf_celery_worker

# Test de salud:
curl http://localhost:8000/api/health
# Respuesta esperada: {"status": "ok", "version": "2.0.0"}
```

### 1.5 Abrir Claude Code por primera vez

```bash
cd rfaf-analytics
claude .

# Claude Code leerá el CLAUDE.md automáticamente
# Primera instrucción dentro de Claude Code:
"Verifica que el entorno está correcto:
1. docker-compose ps — todos los servicios UP
2. curl http://localhost:8000/api/health — status OK
3. python3 -c 'import anthropic, google.generativeai, mplsoccer, soccer_xg' — sin errores
Dime si hay algún problema."
```

---

## ⚡ SPRINT 1 — BASE DE DATOS Y ENTORNO (Semana 1-2)

### Objetivo
PostgreSQL con 7 tablas creadas + Redis funcionando + Alembic migraciones + GitHub Actions CI

### Paso 1.1: Completar database.py

```bash
# En Claude Code:
"Implementa la función create_tables() en database.py de forma que:
1. Cree todas las tablas del models.py usando AsyncPG
2. Use Alembic para migraciones en producción
3. Registre con structlog las tablas creadas
4. Tenga manejo de errores claro
Ejecuta los tests con pytest después."
```

### Paso 1.2: Verificar modelos SQLAlchemy

```bash
# En Claude Code:
"Revisa models.py y verifica que los 7 modelos (Club, User, Match,
MatchAnalysis, Player, ScoutReport, PlayerPhysical) tienen:
- Todas las relaciones correctas
- Índices en columnas que se van a filtrar (club_id, youtube_url)
- CHECK constraints para los Enums
Muéstrame el CREATE TABLE SQL que generaría SQLAlchemy."
```

### Paso 1.3: Setup Alembic

```bash
# En Claude Code:
"Inicializa Alembic en el proyecto:
1. alembic init alembic
2. Configura alembic.ini con DATABASE_URL de .env
3. Genera la primera migración con todos los modelos
4. Aplica la migración
Muéstrame el output de 'alembic history'"
```

### Paso 1.4: GitHub Actions CI

```bash
# En Claude Code:
"Crea .github/workflows/ci.yml que:
1. Se ejecute en cada PR a main
2. Instale las dependencias de requirements.txt
3. Ejecute 'ruff check .' para linting
4. Ejecute 'pytest tests/' con cobertura mínima del 60%
5. Reporte el resultado como check en el PR"
```

### Paso 1.5: Deploy inicial en Railway

```bash
# En Claude Code:
"Crea el archivo Dockerfile para el backend FastAPI:
- Base: python:3.11-slim
- Instala requirements.txt
- Expone puerto 8000
- CMD: uvicorn backend.main:app --host 0.0.0.0 --port 8000

Luego crea railway.json para el deploy automático.
Instrucciones para hacer el primer deploy en Railway."
```

### ✅ Verificación Sprint 1

```bash
# Todo esto debe funcionar:
docker-compose up -d
curl http://localhost:8000/api/health
# → {"status": "ok", "db": "connected", "redis": "connected", "version": "2.0.0"}

docker exec rfaf_postgres psql -U rfaf_user -d rfaf_analytics -c "\dt"
# → 7 tablas listadas

pytest tests/ -v
# → Al menos test_health PASSED

# En Railway dashboard: proyecto desplegado y verde
```

---

## 🔥 SPRINT 2 — PIPELINE IA REAL (Semana 3-4)

### Objetivo
URL de YouTube real → Gemini JSON → PostgreSQL → Celery en background

### Paso 2.1: Test Gemini con URL real

```bash
# En Claude Code:
"En gemini_service.py, implementa el test de integración:
1. Coge una URL pública de YouTube de un partido de fútbol
   (puedes usar: https://www.youtube.com/watch?v=bnVZdRzVqIc)
2. Llama a analyze_youtube_video() con esa URL
3. Verifica que el JSON resultante tiene: shots, passes_network, pressing
4. Guarda el JSON en backend/data/test_match_gemini.json para referencia
Muéstrame los primeros 20 shots detectados."
```

### Paso 2.2: Verificar caché Redis

```bash
# En Claude Code:
"Verifica que la caché Redis funciona:
1. Llama a analyze_youtube_video() con la misma URL dos veces
2. La segunda llamada debe usar la caché (no llamar a Gemini)
3. Verifica en los logs que aparece 'Cache hit para [url]'
4. Verifica la key en Redis: redis-cli GET 'gemini_cache:[hash]'
Muéstrame el tiempo de cada llamada."
```

### Paso 2.3: Pipeline Celery completo

```bash
# En Claude Code:
"Completa analyze_match_task() en tasks.py:
1. Llama a analyze_youtube_video() con la URL
2. Guarda el tactical_data en PostgreSQL (tabla matches)
3. Actualiza el status en match_analyses: pending → processing → done
4. Maneja los errores con self.retry()
5. Escribe un test que encole la task y espere el resultado con task.get()"
```

### Paso 2.4: Endpoint con polling

```bash
# En Claude Code:
"Implementa GET /api/analyze/status/{analysis_id} que:
1. Consulte match_analyses en PostgreSQL por el analysis_id
2. Devuelva: status, progress_pct, current_step, estimated_remaining_seconds
3. Si status=done, incluya también: xg_local, xg_visitante, pdf_url
4. Test: POST /api/analyze/match → obtener analysis_id → polling status cada 5s"
```

### ✅ Verificación Sprint 2

```bash
# Test manual completo:
curl -X POST http://localhost:8000/api/analyze/match \
  -H "Content-Type: application/json" \
  -d '{"youtube_url": "https://youtube.com/watch?v=...",
       "equipo_local": "CD Ejea",
       "equipo_visitante": "SD Tarazona",
       "competicion": "Tercera RFEF Grupo XVII",
       "club_id": "00000000-0000-0000-0000-000000000001"}'

# Respuesta esperada:
# {"analysis_id": "abc123...", "status": "pending", "check_url": "/api/analyze/status/abc123"}

# Polling hasta done:
watch -n 5 curl http://localhost:8000/api/analyze/status/abc123
```

---

## 📊 SPRINT 3 — ANÁLISIS CLAUDE + MÉTRICAS (Semana 5-6)

### Paso 3.1: Claude genera el informe completo

```bash
# En Claude Code:
"En claude_service.py, implementa generate_match_report() completo:
1. Carga el system prompt de backend/prompts/INFORME_PARTIDO.md
2. Formatea el JSON táctico de Gemini + métricas de xg_service.py
3. Llama a claude-sonnet-4-6 con max_tokens=4096
4. El output debe seguir exactamente la estructura de 12 secciones del prompt
5. Guarda el Markdown resultante en PostgreSQL (tabla match_analyses.contenido_md)
Prueba con el JSON de test_match_gemini.json."
```

### Paso 3.2: Modelo xG con StatsBomb

```bash
# En Claude Code:
"En data_service.py, ejecuta load_statsbomb_shots_for_xg_training():
1. Descarga los tiros de La Liga 2015/16 con statsbombpy
2. Guarda el CSV en backend/data/benchmarks/shots_xg_comp11_s4.parquet
3. Luego entrena el modelo con train_rfaf_xg_model()
4. Verifica que rfaf_xg_model.pkl se crea en backend/ml_models/
5. Muéstrame el Brier Score y AUC del modelo"
```

### Paso 3.3: Gráficas mplsoccer en el pipeline

```bash
# En Claude Code:
"Integra generate_all_charts() en el pipeline de analyze_match_task():
1. Después de calcular métricas, llama a generate_all_charts(tactical_data)
2. Las gráficas son PNG en base64 — guardarlas en PostgreSQL como JSON
3. Verifica que shot_map_local, pass_network_local y xg_timeline se generan
4. Si mplsoccer falla (matplotlib Agg issue), añade matplotlib.use('Agg') al inicio"
```

### ✅ Verificación Sprint 3

```bash
# El informe completo debe estar en PostgreSQL:
docker exec rfaf_postgres psql -U rfaf_user -d rfaf_analytics \
  -c "SELECT analysis_id, status, xg_local, xg_visitante, 
             LEFT(contenido_md, 200), pdf_url 
      FROM match_analyses WHERE status='done' LIMIT 1;"
```

---

## 📄 SPRINT 4 — PDF + EMAIL + ADMIN (Semana 7-8)

### Paso 4.1: PDF con ReportLab

```bash
# En Claude Code:
"En pdf_service.py, implementa _generate_with_reportlab() completo:
1. Portada con logo RFAF, datos del partido
2. Gráficas mplsoccer embebidas (shot map, pass network, xG timeline)
3. Análisis Claude formateado (### → H2, **bold** → Bold, - bullet → lista)
4. Footer con fecha y numeración de páginas
5. Prueba con el informe de test y abre el PDF resultante"
```

### Paso 4.2: Email automático con Resend

```bash
# En Claude Code:
"Implementa el flujo completo de email en email_service.py:
1. send_analysis_started_email() al encolar (inmediato)
2. send_report_email() cuando el análisis termine (con PDF URL)
3. Usa el template HTML de _render_report_email_html()
4. Test: envia un email de prueba a antoniodepaos@gmail.com con Resend"
```

### Paso 4.3: RLS PostgreSQL

```bash
# En Claude Code:
"Implementa Row Level Security en PostgreSQL:
1. Habilita RLS en las tablas: matches, match_analyses, scout_reports
2. Política: solo el club propietario puede ver sus datos
3. Crea función get_current_club_id() que lea el JWT del contexto
4. Test: crea 2 clubs, verifica que Club A no ve datos de Club B"
```

---

## 💳 SPRINT 5 — STRIPE (Semana 9-10)

### Paso 5.1: Stripe Checkout

```bash
# En Claude Code:
"Implementa el flujo de checkout en clubs.py:
1. POST /api/clubs/{id}/checkout → crea Stripe Checkout Session
2. Parámetros: price_id según el plan (Básico/Pro/Federado)
3. metadata: club_id para el webhook
4. success_url: https://rfaf-analytics.es/dashboard?payment=success
5. Test con Stripe CLI: stripe listen --forward-to localhost:8000/api/webhooks/stripe"
```

### Paso 5.2: Webhooks idempotentes

```bash
# En Claude Code:
"Verifica que webhooks.py maneja correctamente:
1. checkout.session.completed → activar suscripción
2. invoice.payment_succeeded → renovar suscripción (reset analisis_mes_actual=0)
3. customer.subscription.deleted → downgrade a Básico
4. Idempotencia: ejecutar el mismo webhook 2 veces no debe crear duplicados
5. Test con: stripe trigger checkout.session.completed"
```

### Paso 5.3: Límites de plan

```bash
# En Claude Code:
"En analyze.py, añade verificación del límite del plan antes de encolar:
1. Plan Básico: máximo 3 análisis por mes
2. Si el club ha agotado sus análisis: devolver error 429 con mensaje claro en español
3. El contador analisis_mes_actual se resetea el 1 de cada mes (Celery beat)
4. Plan Pro/Federado: sin límite
5. Test: crear un club Básico, hacer 3 análisis, verificar que el 4º falla"
```

---

## 🎨 SPRINT 6-7 — FRONTEND CONECTADO (Semana 11-14)

### Paso 6.1: Setup Next.js

```bash
# En Claude Code:
"Inicializa Next.js 15 en la carpeta frontend/:
npx create-next-app@latest frontend --typescript --tailwind --app
Instala: recharts @anthropic/sdk stripe

Configura next.config.ts con:
- NEXT_PUBLIC_API_URL=http://localhost:8000 (dev)
- NEXT_PUBLIC_API_URL=https://api.rfaf-analytics.es (prod)"
```

### Paso 6.2: Conectar los productos React al backend

```bash
# En Claude Code:
"Toma los archivos rfaf_p1_rivales_v2.jsx y rfaf_ultimate_report.jsx
(que son demos estáticas) y conéctalos al backend real:
1. Crea frontend/lib/api.ts con fetch wrapper para /api/*
2. Los datos estáticos de ejemplo → sustituir por llamadas a la API
3. Añadir estado de loading y error handling
4. El análisis nuevo → formulario → encolar → polling → mostrar informe"
```

### Paso 6.3: Chatbot táctico

```bash
# En Claude Code:
"Implementa el chatbot táctico en el informe web:
1. POST /api/chat/{analysis_id} — recibe pregunta del entrenador
2. claude_service.chat_with_report() — usa claude-haiku con el informe como contexto
3. Interfaz web: chat bubble en la esquina del informe
4. Test: abrir el informe de un partido real y preguntar:
   '¿Cómo neutralizo al #9 rival en el próximo partido?'"
```

---

## 🧪 SPRINT 8 — BETA 5 CLUBES Y PRODUCCIÓN (Semana 15-16)

### Paso 8.1: Selección de clubes piloto

```bash
# Antonio hace esto con Manuel Torralba:
# Criterios de selección:
# - 2 clubes Tercera RFEF (Plan Pro)
# - 2 clubes Regional Preferente (Plan Básico)
# - 1 club con acuerdo especial RFAF (Plan Federado)
# - Entrenadores con cierta familiaridad con tecnología
# - Partidos con vídeos de YouTube disponibles

# Ejemplos: CD Cuarte, CF Borja, SD Ejea B, UD Barbastro, CF Utebo
```

### Paso 8.2: Onboarding de clubes

```bash
# En Claude Code:
"Crea el script de onboarding en backend/scripts/onboard_club.py:
1. Crea el club en PostgreSQL
2. Crea el usuario admin (entrenador)
3. Genera la URL de checkout de Stripe
4. Envía email de bienvenida con instrucciones paso a paso
5. Ejecutar: python backend/scripts/onboard_club.py --nombre 'CD Cuarte' --email 'entrenador@cdcuarte.es' --plan profesional"
```

### Paso 8.3: Load test

```bash
# En Claude Code:
"Crea un load test con locust:
pip install locust

Escenario: 20 usuarios simultáneos haciendo POST /api/analyze/match
- Cada request usa una URL de YouTube diferente
- Medir: latencia P95, tasa de éxito, errores
- Target: < 5% de errores, P95 < 30s para el análisis completo (con caché)
Ejecutar: locust -f tests/load_test.py --headless -u 20 -r 5 --run-time 5m"
```

---

## 🚀 DESPLIEGUE EN PRODUCCIÓN

### Backend en Railway

```bash
# En Claude Code (con Claude in Chrome abierto en railway.app):
"Configura el deploy de producción en Railway:
1. Variables de entorno desde .env (copiar todas excepto las de desarrollo)
2. Dockerfile build automático en cada push a main
3. PostgreSQL addon de Railway (no docker local)
4. Redis addon de Railway
5. Worker de Celery como servicio separado en Railway
Instrucciones detalladas para hacer el primer deploy."
```

```bash
# Comandos manuales:
npm install -g @railway/cli
railway login
railway init --name rfaf-analytics-backend
railway up                              # Primer deploy
railway domain                          # Asignar dominio: api.rfaf-analytics.es
```

### Frontend en Vercel

```bash
npm install -g vercel
cd frontend/
vercel                                  # Seguir el wizard
# Framework: Next.js
# Directorio: frontend/
# Variables de entorno: NEXT_PUBLIC_API_URL=https://api.rfaf-analytics.es
vercel --prod                           # Deploy a producción
# Dominio: rfaf-analytics.es → apuntar a Vercel en el DNS de Cloudflare
```

### Dominio y DNS

```bash
# En Cloudflare (dash.cloudflare.com):
# Añadir dominio: rfaf-analytics.es
# DNS Records:
#   A    rfaf-analytics.es        → IP de Vercel
#   A    api.rfaf-analytics.es    → IP de Railway
#   CNAME cdn.rfaf-analytics.es   → tu-bucket.r2.cloudflarestorage.com

# Verificar SSL automático (Cloudflare)
curl https://rfaf-analytics.es/         # → Frontend Next.js
curl https://api.rfaf-analytics.es/api/health  # → {"status": "ok"}
```

### Stripe en producción

```bash
# En dashboard.stripe.com:
# 1. Cambiar a modo Live (no Test)
# 2. Crear los 3 products: Básico, Profesional, Federado
# 3. Actualizar .env con sk_live_... y pk_live_...
# 4. Actualizar webhook endpoint a: https://api.rfaf-analytics.es/api/webhooks/stripe
# 5. Copiar el nuevo STRIPE_WEBHOOK_SECRET
```

---

## 🔧 OPERACIONES Y MANTENIMIENTO

### Monitorización diaria

```bash
# Dashboard recomendado de operaciones (abrir en Chrome con Claude in Chrome):
# 1. Sentry: https://sentry.io → errores nuevos
# 2. Railway: https://railway.app → uso CPU/memoria
# 3. PostHog: https://eu.posthog.com → análisis del día
# 4. Stripe: https://dashboard.stripe.com → pagos
# 5. Resend: https://resend.com → emails enviados/bounced
```

### Backup PostgreSQL

```bash
# Automático (configurado en Sprint 8 con Celery beat):
# Cada día a las 3:00 AM → dump PostgreSQL → subir a R2

# Manual cuando necesario:
docker exec rfaf_postgres pg_dump -U rfaf_user rfaf_analytics | gzip > backup_$(date +%Y%m%d).sql.gz
```

### Actualizar el modelo xG con datos nuevos

```bash
# Cada mes con los nuevos datos de la plataforma:
python3 -c "
from backend.services.data_service import train_rfaf_xg_model
from backend.services.data_service import load_platform_shots

shots = load_platform_shots()  # Carga tiros de la plataforma
train_rfaf_xg_model(shots)     # Re-entrena el modelo
print('Modelo xG actualizado')
"
```

### Responder al feedback de los clubes

```bash
# En Claude.ai Opus 4.6 con contexto del proyecto:
"Revisando el feedback de esta semana de los 5 clubes piloto:
- CD Cuarte: 'Los heatmaps no muestran correctamente la zona del pivote'
- CF Borja: 'El PDF tarda más de 20 minutos en llegar'
- SD Ejea B: 'El chatbot no responde preguntas sobre el rival'

Prioriza estos bugs para el próximo sprint. Para cada uno:
1. Identifica el archivo/función causante
2. Estima el esfuerzo (story points)
3. Sugiere la solución técnica"
```

---

## 📊 MÉTRICAS DE ÉXITO A MONITORIZAR

| KPI | Objetivo Sprint 8 | Objetivo Q4 2026 |
|---|---|---|
| Clubes activos | 5 (beta) | 25 |
| MRR | 651€ (actual) | 3.100€ |
| Análisis/mes | 20 | 200 |
| Tiempo análisis | < 18 min | < 12 min |
| NPS medio | ≥ 7.5 | ≥ 8.5 |
| Uptime | ≥ 99% | ≥ 99.5% |
| Tasa error análisis | < 5% | < 2% |
| Coste IA/análisis | < 0.60€ | < 0.55€ |

---

## 🆘 TROUBLESHOOTING FRECUENTE

```bash
# ── Gemini devuelve JSON inválido ─────────────────────────────────────
# Problema: El vídeo de YouTube es muy largo o baja calidad
# Solución: Comprobar que el vídeo es público y tiene >= 720p
# En gemini_service.py, añadir validación de duración: < 120 minutos

# ── Celery task no se ejecuta ─────────────────────────────────────────
# Problema: Redis no está corriendo o el worker está caído
docker ps | grep celery     # Ver si el worker está UP
docker logs rfaf_celery_worker --tail 50  # Ver errores
docker-compose restart celery_worker       # Reiniciar

# ── mplsoccer falla en el servidor ───────────────────────────────────
# Problema: matplotlib intenta usar display GUI
# Solución: Añadir al inicio de visualization_service.py:
import matplotlib
matplotlib.use("Agg")  # ← Debe ir ANTES de importar pyplot

# ── Error de conexión a PostgreSQL ───────────────────────────────────
docker exec rfaf_postgres pg_isready -U rfaf_user -d rfaf_analytics
# Si falla: docker-compose restart postgres
# Verificar DATABASE_URL en .env

# ── PDF no llega por email ────────────────────────────────────────────
# Verificar en Resend dashboard: https://resend.com/emails
# Revisar logs: docker logs rfaf_backend | grep "email"
# Verificar RESEND_API_KEY en .env
```

---

*RFAF Analytics Platform · Guía 0→100 v1.0 · Abril 2026*
*Actualizar con cada sprint completado*
