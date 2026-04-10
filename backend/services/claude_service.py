"""Claude Sonnet 4.6 - Generación de informes tácticos."""

import os
import time
from pathlib import Path

import anthropic
import structlog

logger = structlog.get_logger()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


def _load_system_prompt(filename: str) -> str:
    path = PROMPTS_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"System prompt no encontrado: {path}")
    return path.read_text(encoding="utf-8")


async def generate_match_report(
    tactical_data: dict,
    equipo_local: str,
    equipo_visitante: str,
    competicion: str | None = None,
) -> tuple[str, float]:
    """Genera informe táctico con Claude Sonnet 4.6.

    Args:
        tactical_data: JSON táctico de Gemini.
        equipo_local: Nombre del equipo local.
        equipo_visitante: Nombre del equipo visitante.
        competicion: Nombre de la competición.

    Returns:
        Tuple de (markdown del informe, coste en EUR).
    """
    start_time = time.time()

    if not ANTHROPIC_API_KEY:
        raise ValueError("ANTHROPIC_API_KEY no configurada. Añádela al .env")

    system_prompt = _load_system_prompt("INFORME_PARTIDO.md")

    user_message = (
        f"Genera el informe táctico completo del partido:\n"
        f"- Equipo local: {equipo_local}\n"
        f"- Equipo visitante: {equipo_visitante}\n"
    )
    if competicion:
        user_message += f"- Competición: {competicion}\n"
    user_message += f"\nDatos tácticos del partido (JSON):\n```json\n{_safe_json(tactical_data)}\n```"

    logger.info(
        "claude_call_start",
        model="claude-sonnet-4-6",
        equipo_local=equipo_local,
        equipo_visitante=equipo_visitante,
    )

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}],
    )

    contenido_md = response.content[0].text
    duration = time.time() - start_time

    # Cost estimation: input + output tokens
    input_tokens = response.usage.input_tokens
    output_tokens = response.usage.output_tokens
    # Claude Sonnet 4.6: $3/M input, $15/M output -> EUR (~0.92 rate)
    cost_usd = (input_tokens * 3 / 1_000_000) + (output_tokens * 15 / 1_000_000)
    cost_eur = round(cost_usd * 0.92, 4)

    logger.info(
        "claude_call_done",
        model="claude-sonnet-4-6",
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_eur=cost_eur,
        duration_s=round(duration, 2),
        report_length=len(contenido_md),
    )

    return contenido_md, cost_eur


def _safe_json(data: dict) -> str:
    """Serializa JSON truncando si es muy largo para no exceder context."""
    import json

    text = json.dumps(data, ensure_ascii=False, indent=2)
    max_chars = 50_000
    if len(text) > max_chars:
        return text[:max_chars] + "\n... (truncado por longitud)"
    return text
