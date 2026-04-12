# Guia de Despliegue — RFAF Analytics Platform

## Arquitectura de produccion

```
Usuario -> Vercel (Next.js) -> Railway (FastAPI + Celery + PostgreSQL + Redis)
                                  |
                          Cloudflare R2 (PDFs)
                          Resend (emails)
                          Stripe (pagos)
```

**Coste estimado: ~$20-60/mes** | MRR actual: ~651 EUR | Margen: >90%

---

## Paso 1: Crear cuenta en Railway

1. Ve a [railway.app](https://railway.app) y crea cuenta con GitHub
2. Crea un nuevo proyecto: **"RFAF Analytics"**

### 1a. Anadir PostgreSQL

1. En el proyecto, pulsa **"+ New"** → **"Database"** → **"PostgreSQL"**
2. Railway crea la instancia automaticamente
3. Ve a la pestana **"Variables"** del servicio PostgreSQL
4. Copia el valor de `DATABASE_URL` (lo necesitaras despues)

### 1b. Anadir Redis

1. Pulsa **"+ New"** → **"Database"** → **"Redis"**
2. Copia el valor de `REDIS_URL`

### 1c. Desplegar Backend (web)

1. Pulsa **"+ New"** → **"GitHub Repo"** → selecciona tu repositorio
2. Railway detecta el `Procfile` automaticamente
3. En **Settings**:
   - **Start Command**: deja que use el Procfile (`web`)
   - **Root Directory**: `/` (raiz)
4. En **Variables**, configura TODAS estas variables:

```env
# Base de datos (copiar de PostgreSQL service)
DATABASE_URL=postgresql+asyncpg://...

# Redis (copiar de Redis service)
REDIS_URL=redis://...

# Seguridad
JWT_SECRET=<genera con: openssl rand -hex 32>
ENVIRONMENT=production

# APIs de IA
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=AIza...

# Stripe
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRICE_BASICO=price_...
STRIPE_PRICE_PROFESIONAL=price_...
STRIPE_PRICE_FEDERADO=price_...
STRIPE_PORTAL_RETURN_URL=https://tu-dominio.vercel.app/settings

# Cloudflare R2 (storage PDFs)
CLOUDFLARE_R2_ACCESS_KEY=...
CLOUDFLARE_R2_SECRET_KEY=...
CLOUDFLARE_R2_ENDPOINT=https://xxx.r2.cloudflarestorage.com
CLOUDFLARE_R2_BUCKET=rfaf-analytics
CLOUDFLARE_R2_PUBLIC_URL=https://pub-xxx.r2.dev

# Email
RESEND_API_KEY=re_...
RESEND_FROM_EMAIL=RFAF Analytics <notificaciones@tu-dominio.es>

# Frontend URL (para emails y CORS)
FRONTEND_URL=https://tu-dominio.vercel.app
ALLOWED_ORIGINS=https://tu-dominio.vercel.app

# Monitoring (opcional pero recomendado)
SENTRY_DSN=https://xxx@sentry.io/xxx
SENTRY_TRACES_SAMPLE_RATE=0.2
POSTHOG_API_KEY=phc_...
POSTHOG_HOST=https://eu.posthog.com
```

5. En **Networking**, genera un dominio publico (ej: `rfaf-api.up.railway.app`)

### 1d. Desplegar Worker (Celery)

1. En el mismo proyecto, pulsa **"+ New"** → **"GitHub Repo"** → mismo repositorio
2. En **Settings**:
   - **Start Command**: `celery -A backend.workers.tasks worker --beat --loglevel=info --concurrency=4`
3. Copia las MISMAS variables de entorno del servicio web
4. **No** generes dominio publico (el worker no recibe HTTP)

---

## Paso 2: Crear cuenta en Vercel

1. Ve a [vercel.com](https://vercel.com) y crea cuenta con GitHub
2. Pulsa **"Add New Project"** → importa tu repositorio

### 2a. Configurar proyecto

1. **Framework Preset**: Next.js (detectado automaticamente)
2. **Root Directory**: `frontend`
3. **Build Command**: `next build` (default)
4. **Output Directory**: `.next` (default)

### 2b. Variables de entorno

```env
NEXT_PUBLIC_API_URL=https://rfaf-api.up.railway.app
```

3. Pulsa **"Deploy"**

---

## Paso 3: Configurar Stripe

### 3a. Productos y precios

En [dashboard.stripe.com](https://dashboard.stripe.com):

1. **Products** → **Add Product**:
   - "Plan Basico" → 49 EUR/mes → copia `price_id`
   - "Plan Profesional" → 149 EUR/mes → copia `price_id`
   - "Plan Federado" → 104 EUR/mes → copia `price_id`

2. Pon los `price_id` en las variables `STRIPE_PRICE_*` de Railway

### 3b. Webhook

1. **Developers** → **Webhooks** → **Add endpoint**
2. URL: `https://rfaf-api.up.railway.app/api/webhooks/stripe`
3. Eventos a escuchar:
   - `checkout.session.completed`
   - `invoice.paid`
   - `customer.subscription.deleted`
4. Copia el **Signing Secret** (`whsec_...`) a `STRIPE_WEBHOOK_SECRET`

### 3c. Billing Portal

1. **Settings** → **Billing** → **Customer portal**
2. Activa: actualizar plan, cancelar suscripcion, historial facturas
3. Pon la URL de retorno en `STRIPE_PORTAL_RETURN_URL`

---

## Paso 4: Configurar Cloudflare R2

1. En [dash.cloudflare.com](https://dash.cloudflare.com) → **R2 Object Storage**
2. Crea bucket: `rfaf-analytics`
3. **Settings** → **R2 API Tokens** → crea token con permisos Read+Write
4. Copia Access Key, Secret Key y Endpoint a las variables de Railway

---

## Paso 5: Configurar Resend (email)

1. En [resend.com](https://resend.com) → crea cuenta
2. **API Keys** → crea key → copia a `RESEND_API_KEY`
3. **Domains** → anade tu dominio y configura DNS (SPF, DKIM)

---

## Paso 6: Verificacion post-deploy

### Checklist

```bash
# 1. Health check
curl https://rfaf-api.up.railway.app/api/health
# Debe devolver: {"version":"2.0.0","status":"ok","db":"connected","redis":"connected"}

# 2. Frontend carga
# Abre https://tu-dominio.vercel.app en el navegador

# 3. Login funciona
curl -X POST https://rfaf-api.up.railway.app/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@rfaf.es","password":"tu-password"}'

# 4. Stripe webhook test
# En Stripe Dashboard: Webhooks → Send test webhook → checkout.session.completed

# 5. Celery worker activo
# En Railway: verifica los logs del servicio worker
```

### Crear primer usuario admin

```bash
# Opcion A: desde el panel admin (si ya tienes un admin)
# Ve a /admin/users → Crear usuario

# Opcion B: via API directa (primera vez)
curl -X POST https://rfaf-api.up.railway.app/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@rfaf.es","password":"tu-password-seguro","name":"Admin RFAF","club_id":"..."}'
```

---

## Paso 7: Dominio personalizado (opcional)

### Railway (API)
1. **Settings** → **Networking** → **Custom Domain**
2. Anade `api.rfaf-analytics.es`
3. Configura CNAME en tu DNS

### Vercel (Frontend)
1. **Settings** → **Domains** → anade `rfaf-analytics.es`
2. Configura los registros DNS que Vercel te indique

Actualiza `ALLOWED_ORIGINS` y `FRONTEND_URL` en Railway con el nuevo dominio.

---

## Monitorizacion

| Servicio | Que monitoriza | URL |
|----------|---------------|-----|
| **Sentry** | Errores backend + Celery | sentry.io |
| **PostHog** | Analytics usuario | posthog.com |
| **Railway** | Logs + metricas servidor | railway.app |
| **Vercel** | Logs + metricas frontend | vercel.com |
| **Admin Panel** | MRR, costes IA, analisis | /admin |

---

## Costes mensuales estimados

| Servicio | Plan | Coste |
|----------|------|-------|
| Railway (web + worker + DB + Redis) | Pro | ~$20-40/mes |
| Vercel (frontend) | Hobby/Pro | $0-20/mes |
| Cloudflare R2 | Pay-as-you-go | ~$1/mes |
| Resend | Free tier | $0 |
| Sentry | Free tier | $0 |
| PostHog | Free tier | $0 |
| **Total** | | **~$20-60/mes** |

Con MRR de ~651 EUR → **margen >90%**
