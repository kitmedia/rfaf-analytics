"""Gemini 2.5 Flash - Análisis táctico de vídeo YouTube."""

import hashlib
import json
import os
import time

import google.generativeai as genai
import redis
import structlog

logger = structlog.get_logger()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CACHE_TTL_SECONDS = 30 * 24 * 3600  # 30 días

_redis_client: redis.Redis | None = None


def _get_redis() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(REDIS_URL, decode_responses=True)
    return _redis_client


def _cache_key(youtube_url: str) -> str:
    url_hash = hashlib.sha256(youtube_url.encode()).hexdigest()[:16]
    return f"gemini_cache:{url_hash}"


GEMINI_SYSTEM_PROMPT = """Eres un analista táctico de fútbol experto. Analiza el vídeo del partido de fútbol proporcionado y extrae datos tácticos estructurados en formato JSON.

Debes devolver EXCLUSIVAMENTE un JSON válido (sin markdown, sin explicaciones) con esta estructura exacta:

{
  "metadata": {
    "duracion_minutos": <int>,
    "calidad_video": "alta|media|baja",
    "confianza_global": <float 0-1>
  },
  "equipos": {
    "local": {
      "nombre_detectado": "<string>",
      "formacion": "<string, ej: 4-4-2>",
      "jugadores_detectados": <int>
    },
    "visitante": {
      "nombre_detectado": "<string>",
      "formacion": "<string>",
      "jugadores_detectados": <int>
    }
  },
  "shots": [
    {
      "minuto": <int>,
      "equipo": "local|visitante",
      "jugador": "<string o null>",
      "tipo": "pie_derecho|pie_izquierdo|cabeza|otro",
      "resultado": "gol|parada|fuera|bloqueado",
      "x": <float 0-100>,
      "y": <float 0-100>,
      "xg_estimado": <float 0-1>
    }
  ],
  "passes_network": {
    "local": [
      {
        "de": "<jugador o posicion>",
        "a": "<jugador o posicion>",
        "cantidad": <int>,
        "completados": <int>
      }
    ],
    "visitante": [
      {
        "de": "<jugador o posicion>",
        "a": "<jugador o posicion>",
        "cantidad": <int>,
        "completados": <int>
      }
    ]
  },
  "pressing": {
    "local": {
      "ppda": <float>,
      "recuperaciones_campo_rival": <int>,
      "pressing_alto_eventos": <int>
    },
    "visitante": {
      "ppda": <float>,
      "recuperaciones_campo_rival": <int>,
      "pressing_alto_eventos": <int>
    }
  },
  "eventos_clave": [
    {
      "minuto": <int>,
      "tipo": "gol|tarjeta|sustitucion|ocasion_clara|error_defensivo",
      "descripcion": "<string breve>"
    }
  ],
  "posesion": {
    "local_pct": <float>,
    "visitante_pct": <float>
  },
  "field_tilt": {
    "local_pct": <float>,
    "visitante_pct": <float>
  }
}

REGLAS:
- Si no puedes detectar un dato con confianza, usa null en vez de inventar.
- Los campos x,y de shots usan coordenadas normalizadas (0-100).
- El PPDA (Passes Per Defensive Action) debe calcularse si es posible.
- Incluye TODOS los tiros detectados, no solo los goles.
- Devuelve SOLO el JSON, sin texto adicional."""


async def analyze_youtube_video(youtube_url: str) -> dict:
    """Analiza un vídeo de YouTube con Gemini 2.5 Flash.

    Implementa caché Redis de 30 días para URLs ya analizadas.
    Retorna JSON táctico con shots, passes_network, pressing, etc.
    """
    start_time = time.time()

    # Check cache
    r = _get_redis()
    cache_k = _cache_key(youtube_url)
    cached = r.get(cache_k)
    if cached:
        duration = time.time() - start_time
        logger.info(
            "gemini_cache_hit",
            youtube_url=youtube_url,
            duration_s=round(duration, 3),
        )
        return json.loads(cached)

    # Call Gemini 2.5 Flash
    if not GOOGLE_API_KEY:
        raise ValueError("GOOGLE_API_KEY no configurada. Añádela al .env")

    genai.configure(api_key=GOOGLE_API_KEY)
    model = genai.GenerativeModel("gemini-2.5-flash")

    logger.info(
        "gemini_call_start",
        youtube_url=youtube_url,
        model="gemini-2.5-flash",
    )

    # Gemini 2.5 Flash soporta URLs de YouTube como contenido nativo
    video_part = genai.types.ContentDict(
        parts=[
            {"text": GEMINI_SYSTEM_PROMPT},
            {
                "file_data": {
                    "file_uri": youtube_url,
                    "mime_type": "video/*",
                }
            },
            {"text": "Analiza este partido de fútbol y devuelve el JSON táctico."},
        ]
    )

    response = model.generate_content(
        video_part,
        generation_config=genai.GenerationConfig(
            temperature=0.1,
            max_output_tokens=8192,
            response_mime_type="application/json",
        ),
    )

    # Parse response
    raw_text = response.text.strip()
    try:
        tactical_data = json.loads(raw_text)
    except json.JSONDecodeError:
        logger.error(
            "gemini_json_parse_error",
            youtube_url=youtube_url,
            raw_response_preview=raw_text[:500],
        )
        raise ValueError("Gemini no devolvió un JSON válido. Inténtalo de nuevo.")

    # Validate minimum structure
    required_keys = {"shots", "passes_network", "pressing"}
    missing = required_keys - set(tactical_data.keys())
    if missing:
        logger.warning(
            "gemini_missing_keys",
            youtube_url=youtube_url,
            missing_keys=list(missing),
        )

    duration = time.time() - start_time
    cost_eur = 0.49

    # Cache result in Redis for 30 days
    r.setex(cache_k, CACHE_TTL_SECONDS, json.dumps(tactical_data, ensure_ascii=False))

    logger.info(
        "gemini_call_done",
        youtube_url=youtube_url,
        model="gemini-2.5-flash",
        cost_eur=cost_eur,
        duration_s=round(duration, 2),
        shots_count=len(tactical_data.get("shots", [])),
        has_passes=bool(tactical_data.get("passes_network")),
        has_pressing=bool(tactical_data.get("pressing")),
    )

    return tactical_data
