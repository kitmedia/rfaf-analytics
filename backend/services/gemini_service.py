"""Gemini 2.5 Flash - Análisis táctico de vídeo YouTube.

Soporta vídeos largos (90+ min) troceándolos automáticamente con yt-dlp + ffmpeg.
"""

import hashlib
import json
import os
import subprocess
import tempfile
import time
from pathlib import Path

import google.generativeai as genai
import redis
import structlog

logger = structlog.get_logger()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CACHE_TTL_SECONDS = 30 * 24 * 3600  # 30 días
MAX_DIRECT_DURATION = 25 * 60  # 25 min — por debajo, URL directa a Gemini
CHUNK_DURATION = 20 * 60  # 20 min por trozo

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

GEMINI_CHUNK_PROMPT = """Este es el TROZO {chunk_num} de {total_chunks} de un partido de fútbol.
Este trozo corresponde a los minutos {start_min}-{end_min} del partido.
Analiza SOLO lo que ocurre en este fragmento y ajusta los minutos de los eventos sumando {start_min} al minuto detectado en el vídeo.
Devuelve el JSON táctico con la misma estructura."""


def _get_video_duration(youtube_url: str) -> int | None:
    """Get video duration in seconds using yt-dlp. Returns None on failure."""
    try:
        result = subprocess.run(
            ["yt-dlp", "--print", "duration", "--no-download", youtube_url],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode == 0 and result.stdout.strip():
            return int(float(result.stdout.strip()))
    except (subprocess.TimeoutExpired, FileNotFoundError, ValueError):
        pass
    return None


def _download_video(youtube_url: str, output_path: str) -> bool:
    """Download video with yt-dlp at 360p to minimize size."""
    try:
        result = subprocess.run(
            [
                "yt-dlp",
                "-f", "best[height<=360]",
                "--no-playlist",
                "-o", output_path,
                youtube_url,
            ],
            capture_output=True, text=True, timeout=600,
        )
        return result.returncode == 0 and os.path.exists(output_path)
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def _split_video(input_path: str, chunk_seconds: int, output_dir: str) -> list[dict]:
    """Split video into chunks with ffmpeg. Returns list of {path, start_sec, end_sec}."""
    # Get total duration
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", input_path],
        capture_output=True, text=True, timeout=30,
    )
    total_seconds = int(float(result.stdout.strip()))

    chunks = []
    start = 0
    idx = 0
    while start < total_seconds:
        end = min(start + chunk_seconds, total_seconds)
        chunk_path = os.path.join(output_dir, f"chunk_{idx:02d}.mp4")
        subprocess.run(
            [
                "ffmpeg", "-y", "-i", input_path,
                "-ss", str(start), "-to", str(end),
                "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28",
                "-c:a", "aac", "-b:a", "64k",
                chunk_path,
            ],
            capture_output=True, timeout=300,
        )
        if os.path.exists(chunk_path):
            chunks.append({"path": chunk_path, "start_sec": start, "end_sec": end})
        start = end
        idx += 1

    return chunks


def _upload_to_gemini(file_path: str) -> genai.types.File:
    """Upload a video file to Gemini File API."""
    uploaded = genai.upload_file(file_path, mime_type="video/mp4")
    # Wait for processing
    while uploaded.state.name == "PROCESSING":
        time.sleep(5)
        uploaded = genai.get_file(uploaded.name)
    if uploaded.state.name != "ACTIVE":
        raise ValueError(f"Gemini rechazó el archivo: {uploaded.state.name}")
    return uploaded


def _analyze_chunk(
    model: genai.GenerativeModel,
    file: genai.types.File,
    chunk_num: int,
    total_chunks: int,
    start_min: int,
    end_min: int,
) -> dict:
    """Analyze a single video chunk with Gemini."""
    chunk_instruction = GEMINI_CHUNK_PROMPT.format(
        chunk_num=chunk_num, total_chunks=total_chunks,
        start_min=start_min, end_min=end_min,
    )

    response = model.generate_content(
        [GEMINI_SYSTEM_PROMPT, file, chunk_instruction],
        generation_config=genai.GenerationConfig(
            temperature=0.1,
            max_output_tokens=8192,
            response_mime_type="application/json",
        ),
    )
    return json.loads(response.text.strip())


def _merge_tactical_data(chunks_data: list[dict]) -> dict:
    """Merge tactical data from multiple video chunks into a single result."""
    if len(chunks_data) == 1:
        return chunks_data[0]

    merged = {
        "metadata": chunks_data[0].get("metadata", {}),
        "equipos": chunks_data[0].get("equipos", {}),
        "shots": [],
        "passes_network": {"local": [], "visitante": []},
        "pressing": chunks_data[0].get("pressing", {}),
        "eventos_clave": [],
        "posesion": {"local_pct": 0, "visitante_pct": 0},
        "field_tilt": {"local_pct": 0, "visitante_pct": 0},
    }

    # Update metadata duration
    total_min = sum(c.get("metadata", {}).get("duracion_minutos", 0) for c in chunks_data)
    if total_min:
        merged["metadata"]["duracion_minutos"] = total_min

    # Merge shots and events (already have correct minutes from chunk prompt)
    for chunk in chunks_data:
        merged["shots"].extend(chunk.get("shots", []))
        merged["eventos_clave"].extend(chunk.get("eventos_clave", []))

    # Merge pass networks — aggregate by player pair
    for side in ("local", "visitante"):
        pass_map: dict[tuple, dict] = {}
        for chunk in chunks_data:
            for p in (chunk.get("passes_network") or {}).get(side, []):
                key = (p.get("de", "?"), p.get("a", "?"))
                if key in pass_map:
                    pass_map[key]["cantidad"] += p.get("cantidad", 0)
                    pass_map[key]["completados"] += p.get("completados", 0)
                else:
                    pass_map[key] = {**p}
        merged["passes_network"][side] = list(pass_map.values())

    # Average posesion and field_tilt
    n = len(chunks_data)
    for field in ("posesion", "field_tilt"):
        for key in ("local_pct", "visitante_pct"):
            vals = [c.get(field, {}).get(key, 0) or 0 for c in chunks_data]
            merged[field][key] = round(sum(vals) / max(n, 1), 1)

    # Average pressing
    for side in ("local", "visitante"):
        pressing_data = [c.get("pressing", {}).get(side, {}) for c in chunks_data]
        if pressing_data:
            for key in ("ppda", "recuperaciones_campo_rival", "pressing_alto_eventos"):
                vals = [p.get(key, 0) or 0 for p in pressing_data]
                if key == "ppda":
                    merged["pressing"][side][key] = round(sum(vals) / max(n, 1), 1)
                else:
                    merged["pressing"][side][key] = sum(vals)

    # Sort events by minute
    merged["shots"].sort(key=lambda s: s.get("minuto", 0))
    merged["eventos_clave"].sort(key=lambda e: e.get("minuto", 0))

    return merged


async def analyze_youtube_video(youtube_url: str) -> dict:
    """Analiza un vídeo de YouTube con Gemini 2.5 Flash.

    - Vídeos cortos (<25 min): URL directa a Gemini.
    - Vídeos largos (>25 min): descarga, trocea, analiza por partes, fusiona.
    - Caché Redis 30 días para URLs ya analizadas.
    """
    start_time = time.time()

    # Check cache
    r = _get_redis()
    cache_k = _cache_key(youtube_url)
    cached = r.get(cache_k)
    if cached:
        duration = time.time() - start_time
        logger.info("gemini_cache_hit", youtube_url=youtube_url, duration_s=round(duration, 3))
        return json.loads(cached)

    if not GOOGLE_API_KEY:
        raise ValueError("GOOGLE_API_KEY no configurada. Añádela al .env")

    genai.configure(api_key=GOOGLE_API_KEY)
    model = genai.GenerativeModel("gemini-2.5-flash")

    # Check video duration
    video_duration = _get_video_duration(youtube_url)
    is_long = video_duration is not None and video_duration > MAX_DIRECT_DURATION

    logger.info(
        "gemini_call_start",
        youtube_url=youtube_url,
        model="gemini-2.5-flash",
        video_duration_s=video_duration,
        chunked=is_long,
    )

    if is_long:
        tactical_data = _analyze_long_video(model, youtube_url, video_duration)
    else:
        try:
            tactical_data = _analyze_short_video(model, youtube_url)
        except ValueError as e:
            if "demasiado largo" in str(e) or "token" in str(e).lower():
                # Fallback: download + chunk
                logger.info("gemini_fallback_to_chunking", youtube_url=youtube_url)
                # Re-check duration with download
                video_duration = video_duration or 5400  # assume 90 min
                is_long = True
                tactical_data = _analyze_long_video(model, youtube_url, video_duration)
            else:
                raise

    duration = time.time() - start_time
    # Cost: ~0.49€ for short, ~0.15€ per chunk for long
    num_chunks = (video_duration // CHUNK_DURATION + 1) if is_long and video_duration else 1
    cost_eur = round(0.15 * num_chunks, 2) if is_long else 0.49

    # Cache
    r.setex(cache_k, CACHE_TTL_SECONDS, json.dumps(tactical_data, ensure_ascii=False))

    logger.info(
        "gemini_call_done",
        youtube_url=youtube_url,
        model="gemini-2.5-flash",
        cost_eur=cost_eur,
        duration_s=round(duration, 2),
        shots_count=len(tactical_data.get("shots", [])),
        chunked=is_long,
        num_chunks=num_chunks,
    )

    return tactical_data


def _analyze_short_video(model: genai.GenerativeModel, youtube_url: str) -> dict:
    """Analyze a short video (<25 min) using direct YouTube URL."""
    video_part = genai.types.ContentDict(
        parts=[
            {"text": GEMINI_SYSTEM_PROMPT},
            {"file_data": {"file_uri": youtube_url, "mime_type": "video/*"}},
            {"text": "Analiza este partido de fútbol y devuelve el JSON táctico."},
        ]
    )

    try:
        response = model.generate_content(
            video_part,
            generation_config=genai.GenerationConfig(
                temperature=0.1,
                max_output_tokens=8192,
                response_mime_type="application/json",
            ),
        )
    except Exception as api_err:
        err_msg = str(api_err)
        if "token count exceeds" in err_msg or "too long" in err_msg.lower():
            raise ValueError(
                "El vídeo es demasiado largo para analizar directamente. "
                "Reintentando con descarga y troceado..."
            )
        raise

    raw_text = response.text.strip()
    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        logger.error("gemini_json_parse_error", raw_response_preview=raw_text[:500])
        raise ValueError("Gemini no devolvió un JSON válido. Inténtalo de nuevo.")


def _analyze_long_video(
    model: genai.GenerativeModel, youtube_url: str, duration_s: int
) -> dict:
    """Download, split, and analyze a long video in chunks."""
    with tempfile.TemporaryDirectory(prefix="rfaf_") as tmpdir:
        video_path = os.path.join(tmpdir, "match.mp4")

        logger.info("gemini_downloading_video", youtube_url=youtube_url)
        if not _download_video(youtube_url, video_path):
            raise ValueError(
                "No se pudo descargar el vídeo. Verifica que la URL es pública y accesible."
            )

        logger.info("gemini_splitting_video", duration_s=duration_s, chunk_s=CHUNK_DURATION)
        chunks = _split_video(video_path, CHUNK_DURATION, tmpdir)

        if not chunks:
            raise ValueError("Error al dividir el vídeo en trozos.")

        logger.info("gemini_analyzing_chunks", total_chunks=len(chunks))
        chunks_data = []

        for i, chunk in enumerate(chunks):
            start_min = chunk["start_sec"] // 60
            end_min = chunk["end_sec"] // 60

            logger.info(
                "gemini_chunk_upload",
                chunk=i + 1,
                total=len(chunks),
                minutes=f"{start_min}-{end_min}",
            )

            uploaded_file = _upload_to_gemini(chunk["path"])

            try:
                chunk_data = _analyze_chunk(
                    model, uploaded_file,
                    chunk_num=i + 1, total_chunks=len(chunks),
                    start_min=start_min, end_min=end_min,
                )
                chunks_data.append(chunk_data)
            except Exception as e:
                logger.error("gemini_chunk_error", chunk=i + 1, error=str(e))
                # Continue with other chunks
            finally:
                try:
                    genai.delete_file(uploaded_file.name)
                except Exception:
                    pass

        if not chunks_data:
            raise ValueError("No se pudo analizar ningún trozo del vídeo.")

        return _merge_tactical_data(chunks_data)
