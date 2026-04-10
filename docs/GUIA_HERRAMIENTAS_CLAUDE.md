# GUÍA DE HERRAMIENTAS CLAUDE PARA RFAF ANALYTICS
## Claude Code CLI · Cowork · Claude in Chrome · Claude.ai
### Cómo sacar el máximo partido a cada herramienta en el desarrollo

---

## 🛠️ HERRAMIENTA 1: CLAUDE CODE CLI

### Qué es
CLI que lanza Claude directamente en tu terminal con acceso al sistema de archivos. Lee el `CLAUDE.md` automáticamente al arrancar. Ejecuta comandos, escribe código, hace commits y gestiona el proyecto end-to-end.

### Instalación
```bash
# Requisitos: Node.js 18+
node --version   # Debe ser >=18.0.0

# Instalar Claude Code
npm install -g @anthropic/claude-code

# Verificar instalación
claude --version

# Iniciar sesión (necesitas cuenta Anthropic o API key)
claude auth login
```

### Uso en RFAF Analytics

```bash
# ── Arrancar el proyecto ──────────────────────────────────────────────
cd rfaf-analytics          # Ir a la raíz del proyecto
claude .                   # Lanza Claude Code — lee CLAUDE.md automáticamente

# ── Con modelo específico ─────────────────────────────────────────────
claude . --model claude-opus-4-6        # Máxima capacidad (para arquitectura)
claude . --model claude-sonnet-4-6      # Balance calidad/velocidad (dev diario)

# ── Para tarea específica sin modo interactivo ─────────────────────────
claude "Implementa el endpoint GET /api/reports/{id} con SQLAlchemy"
claude "Escribe los tests de integración para analyze_match_task"
claude "Revisa si hay errores en xg_service.py"
```

### Comandos útiles dentro de Claude Code
```
/help              → Ver todos los comandos disponibles
/status            → Estado del proyecto actual
/commit            → Commit de los cambios actuales con mensaje generado
/pr                → Crear Pull Request
/test              → Ejecutar los tests
/diff              → Ver cambios pendientes
```

### Flujo de trabajo diario con Claude Code

```bash
# 1. Abrir el proyecto
cd rfaf-analytics && claude .

# 2. Daily standup (dentro de Claude Code)
"Daily standup Sprint [N]:
- Completé ayer: [X]
- Hoy haré: [Y]
- Bloqueos: [Z]
Continuamos con story [ID]."

# 3. Implementar el story
"Implementa la story INF-02: función create_tables() async en database.py
que cree las 7 tablas del modelo SQLAlchemy. Incluye logs con structlog."

# 4. Tests
"Escribe los tests de integración para create_tables() usando pytest-asyncio
con una base de datos de test en PostgreSQL"

# 5. Commit
/commit   # Claude genera el mensaje de commit automáticamente

# 6. Deploy (si es Sprint 1-2)
"Despliega el backend en Railway usando railway up"
```

### Prompts más efectivos para Claude Code

```bash
# ✅ BUENOS prompts (específicos y contextualizados):
"En backend/services/xg_service.py, implementa estimate_xg_from_shot()
usando el modelo soccer_xg XGBoost. Si el modelo no está en ml_models/,
descárgalo con soccer_xg.XGModel.load_model('openplay_xgboost_basic').
Añade manejo de errores y fallback a _approximate_xg()."

# ✅ Para tests:
"Escribe test_analyze_match_task() en tests/test_tasks.py usando
un JSON real de StatsBomb (carga statsbombpy para el partido 2500098).
El test debe verificar que xg_local y xg_visitante se calculan correctamente."

# ✅ Para debugging:
"El endpoint POST /api/analyze/match devuelve 500.
Revisa el stack trace en backend/logs/ y dime qué está fallando en tasks.py"

# ❌ MALOS prompts (vagos):
"Arregla los errores"
"Implementa el backend"
"Haz que funcione"
```

---

## 🤖 HERRAMIENTA 2: COWORK

### Qué es
Herramienta desktop de Anthropic para automatizar tareas de archivos y flujos de trabajo sin escribir código. Ideal para tareas repetitivas, reorganización de archivos, y scripts batch.

### Instalación
```bash
# Descargar Cowork desde: https://claude.ai/download
# Instalar en macOS o Windows
# Abrir la app y hacer login con tu cuenta Anthropic
```

### Casos de uso en RFAF Analytics

#### Caso 1: Reorganizar archivos descargados a la estructura del proyecto
```
Instrucción a Cowork:
"Tengo en ~/Downloads/ los siguientes archivos descargados de Claude.ai:
- CLAUDE.md
- requirements.txt
- docker-compose.yml
- backend/main.py
- backend/models.py
[...etc]

Muévelos a ~/Projects/rfaf-analytics/ manteniendo la estructura de carpetas.
Crea las carpetas que no existan."
```

#### Caso 2: Gestión de archivos de datos StatsBomb
```
Instrucción a Cowork:
"Descarga los datos de StatsBomb Open Data desde GitHub
(https://github.com/statsbomb/open-data) y colócalos en
backend/data/statsbomb/ con la estructura correcta."
```

#### Caso 3: Backup diario del proyecto
```
Instrucción a Cowork:
"Cada día a las 22:00, crea un ZIP de backend/ y súbelo a
~/RFAF_Backups/ con el nombre RFAF_backup_YYYY-MM-DD.zip.
Mantén solo los últimos 7 backups."
```

#### Caso 4: Actualizar el CLAUDE.md tras cada sprint
```
Instrucción a Cowork:
"Actualiza la sección 'Estado actual' de CLAUDE.md:
- Cambia 'Sprint 1' a 'Sprint 2'
- Añade al listado de archivos: backend/auth/middleware.py
- Actualiza el MRR de 651€ a [nuevo_valor]"
```

#### Caso 5: Preparar archivos para nueva sesión de Claude
```
Instrucción a Cowork:
"Antes de cada sesión de desarrollo:
1. Lee el CLAUDE.md y extrae el estado actual del sprint
2. Genera un resumen de 3 bullets de los cambios del día anterior (git log)
3. Crea el archivo DAILY_CONTEXT.md con ese resumen listo para pegar en Claude"
```

### ⚠️ Limitaciones de Cowork
- No ejecuta código Python ni comandos de terminal complejos (para eso usa Claude Code)
- No se conecta a APIs externas directamente
- Mejor para: organizar archivos, leer/escribir documentos, preparar contexto

---

## 🌐 HERRAMIENTA 3: CLAUDE IN CHROME

### Qué es
Extensión de Chrome que permite a Claude ver la página web actual y ayudarte con lo que estás viendo.

### Instalación
```bash
# Instalar desde Chrome Web Store: buscar "Claude - Chrome Extension by Anthropic"
# O ir a: https://chrome.google.com/webstore → buscar "Claude Anthropic"
# Hacer login con tu cuenta Anthropic
```

### Casos de uso en RFAF Analytics

#### Caso 1: Revisar la documentación de Gemini en tiempo real
```
1. Abre https://ai.google.dev/gemini-api/docs/models/gemini
2. Claude in Chrome ve la página
3. Pregunta: "¿Cuál es el coste actual de Gemini 2.5 Flash por millón de tokens
   para vídeo? Compáralo con nuestro cálculo de 0.49€/partido de 90 min"
```

#### Caso 2: Revisar Railway/Vercel durante el deploy
```
1. Abre https://railway.app/project/[tu-proyecto]
2. Claude in Chrome ve los logs en tiempo real
3. Pregunta: "Los logs muestran un error. ¿Cuál es la causa y cómo lo arreglo?"
```

#### Caso 3: Revisar Sentry en producción
```
1. Abre https://sentry.io/organizations/rfaf/issues/
2. Claude in Chrome ve los errores
3. Pregunta: "¿Cuáles son los 3 errores más frecuentes? Dime en qué archivo
   del proyecto están y cómo arreglarlos"
```

#### Caso 4: Revisar Stripe Dashboard
```
1. Abre https://dashboard.stripe.com/payments
2. Claude in Chrome ve los pagos
3. Pregunta: "Hay un pago fallido de CD Cuarte. ¿Cuál puede ser la causa
   y qué debo comunicarle al club?"
```

#### Caso 5: Revisar estadísticas PostHog
```
1. Abre https://eu.posthog.com/dashboard
2. Pregunta: "¿Qué feature de la plataforma tiene el mayor engagement esta semana?
   ¿Qué recomendarías priorizar en el próximo sprint basándote en estos datos?"
```

---

## 💬 HERRAMIENTA 4: CLAUDE.AI (Opus 4.6)

### Cuándo usarlo vs Claude Code
| Usar Claude.ai | Usar Claude Code |
|---|---|
| Sprint Planning y diseño arquitectura | Implementar código |
| Decisiones de negocio y estrategia | Ejecutar tests |
| Revisar un bloque de código complejo | Hacer commits y PRs |
| Redactar documentación | Modificar archivos |
| Análisis de métricas de negocio | Debugging con logs |
| Este tipo de conversación | Desarrollo diario |

### Prompt de apertura para nueva sesión Opus 4.6
```
1. Copia el contenido de INICIO_RFAF_OPUS46.md
2. Pégalo al inicio de la nueva conversación
3. Añade a continuación:

"Estoy en el [Sprint N], story [ID].
Completé en la última sesión: [X, Y, Z]
Impedimento actual: [descripción o 'ninguno']
Necesito: [lo que necesitas de Claude hoy]"
```

---

## 🔄 FLUJO DE TRABAJO INTEGRADO: CÓMO USAR TODAS LAS HERRAMIENTAS JUNTAS

```
┌─────────────────────────────────────────────────────────────┐
│                    FLUJO DIARIO RFAF DEV                   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. PLANIFICACIÓN (Claude.ai Opus 4.6 — 15 min)            │
│     → Pegar INICIO_RFAF_OPUS46.md                          │
│     → Daily standup                                         │
│     → Decidir qué stories atacar hoy                        │
│                                                             │
│  2. PREPARACIÓN (Cowork — 5 min)                           │
│     → Reorganizar archivos si hay nuevos downloads          │
│     → Generar DAILY_CONTEXT.md con resumen de ayer          │
│                                                             │
│  3. IMPLEMENTACIÓN (Claude Code CLI — principal)            │
│     cd rfaf-analytics && claude .                           │
│     → Implementar stories del sprint                        │
│     → Tests → Commit → Push                                 │
│                                                             │
│  4. MONITORIZACIÓN (Claude in Chrome — cuando se necesita)  │
│     → Revisar Railway logs durante deploy                   │
│     → Analizar errores en Sentry                            │
│     → Ver métricas en PostHog                               │
│                                                             │
│  5. CIERRE (Claude.ai Opus 4.6 — 10 min)                   │
│     → Sprint Review si toca                                 │
│     → Actualizar CLAUDE.md                                  │
│     → Preparar contexto para mañana                         │
└─────────────────────────────────────────────────────────────┘
```

---

## 🧪 SETUP INICIAL COMPLETO (Primera vez)

```bash
# ── PASO 1: Instalar herramientas ─────────────────────────────────────
npm install -g @anthropic/claude-code    # Claude Code CLI
# Instalar Cowork desktop desde claude.ai/download
# Instalar extensión Claude en Chrome

# ── PASO 2: Configurar autenticación ─────────────────────────────────
claude auth login               # Claude Code
# Cowork: login desde la app desktop
# Chrome extension: login desde la extensión

# ── PASO 3: Crear el proyecto ─────────────────────────────────────────
mkdir rfaf-analytics && cd rfaf-analytics
git init
git remote add origin https://github.com/[tu-usuario]/rfaf-analytics.git

# ── PASO 4: Copiar todos los archivos del proyecto ────────────────────
# (desde los archivos descargados de Claude.ai)
# Usar Cowork para organizar automáticamente

# ── PASO 5: Configurar variables de entorno ───────────────────────────
cp .env.example .env
nano .env   # Rellenar con tus API keys reales

# ── PASO 6: Primera ejecución con Claude Code ─────────────────────────
claude .    # Claude Code leerá el CLAUDE.md automáticamente
# Primer mensaje dentro de Claude Code:
# "Verifica que el entorno está correcto y ejecuta docker-compose up -d"
```

---

## 🔑 API KEYS QUE NECESITAS (ANTES DE EMPEZAR)

| Servicio | Dónde obtenerla | Para qué |
|---|---|---|
| Anthropic | console.anthropic.com | Claude Sonnet + Haiku |
| Google AI | aistudio.google.com | Gemini 2.5 Flash |
| Stripe | dashboard.stripe.com | Pagos |
| Resend | resend.com | Emails automáticos |
| Cloudflare R2 | dash.cloudflare.com | Storage PDFs |
| Railway | railway.app | Deploy backend |
| Sentry | sentry.io | Monitorización errores |
| PostHog | posthog.com | Analytics de uso |

**Tiempo estimado para obtenerlas todas:** 45-60 minutos
**Coste mensual estimado (arranque):** ~15-25€/mes todas las herramientas juntas

---

*RFAF Analytics Platform · Guía de Herramientas Claude v1.0 · Abril 2026*
