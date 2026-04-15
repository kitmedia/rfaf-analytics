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


async def generate_training_plan(
    tactical_data: dict,
    equipo_local: str,
    equipo_visitante: str,
    competicion: str | None = None,
) -> tuple[str, float]:
    """Genera plan de entrenamiento (P3) con Claude Sonnet 4.6.

    Args:
        tactical_data: JSON táctico de Gemini.
        equipo_local: Nombre del equipo local.
        equipo_visitante: Nombre del equipo visitante.
        competicion: Nombre de la competición.

    Returns:
        Tuple de (markdown del plan, coste en EUR).
    """
    start_time = time.time()

    if not ANTHROPIC_API_KEY:
        raise ValueError("ANTHROPIC_API_KEY no configurada. Añádela al .env")

    system_prompt = _load_system_prompt("FORMACION_ENTRENAMIENTO.md")

    user_message = (
        f"Genera el plan de entrenamiento basado en el análisis táctico del partido:\n"
        f"- Equipo local: {equipo_local}\n"
        f"- Equipo visitante: {equipo_visitante}\n"
    )
    if competicion:
        user_message += f"- Competición: {competicion}\n"
    user_message += f"\nDatos tácticos del partido (JSON):\n```json\n{_safe_json(tactical_data)}\n```"

    logger.info(
        "claude_training_plan_start",
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

    input_tokens = response.usage.input_tokens
    output_tokens = response.usage.output_tokens
    cost_usd = (input_tokens * 3 / 1_000_000) + (output_tokens * 15 / 1_000_000)
    cost_eur = round(cost_usd * 0.92, 4)

    logger.info(
        "claude_training_plan_done",
        model="claude-sonnet-4-6",
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_eur=cost_eur,
        duration_s=round(duration, 2),
        plan_length=len(contenido_md),
    )

    return contenido_md, cost_eur


async def generate_scout_report(
    tactical_data: dict,
    player_name: str,
    player_number: int | None,
    equipo: str,
    competicion: str | None = None,
    player_stats: dict | None = None,
) -> tuple[str, float]:
    """Genera informe de scouting (P2) con Claude Sonnet 4.6.

    Returns:
        Tuple de (markdown del informe, coste en EUR).
    """
    start_time = time.time()

    if not ANTHROPIC_API_KEY:
        raise ValueError("ANTHROPIC_API_KEY no configurada. Añádela al .env")

    # Load only Parte A of the combined prompt
    full_prompt = _load_system_prompt("SCOUTING_FORMACION_ENTRENAMIENTO.md")
    scout_prompt = full_prompt.split("## PARTE B")[0].strip()

    user_message = (
        f"Genera el informe de scouting individual del jugador:\n"
        f"- Nombre: {player_name}\n"
    )
    if player_number is not None:
        user_message += f"- Dorsal: {player_number}\n"
    user_message += f"- Equipo: {equipo}\n"
    if competicion:
        user_message += f"- Competición: {competicion}\n"
    if player_stats:
        import json
        user_message += f"\nEstadísticas del jugador:\n```json\n{json.dumps(player_stats, ensure_ascii=False, indent=2)}\n```\n"
    user_message += f"\nDatos tácticos del partido (JSON):\n```json\n{_safe_json(tactical_data)}\n```"

    logger.info(
        "claude_scout_start",
        model="claude-sonnet-4-6",
        player_name=player_name,
        equipo=equipo,
    )

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        system=scout_prompt,
        messages=[{"role": "user", "content": user_message}],
    )

    contenido_md = response.content[0].text
    duration = time.time() - start_time

    input_tokens = response.usage.input_tokens
    output_tokens = response.usage.output_tokens
    cost_usd = (input_tokens * 3 / 1_000_000) + (output_tokens * 15 / 1_000_000)
    cost_eur = round(cost_usd * 0.92, 4)

    logger.info(
        "claude_scout_done",
        model="claude-sonnet-4-6",
        player_name=player_name,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_eur=cost_eur,
        duration_s=round(duration, 2),
    )

    return contenido_md, cost_eur


async def generate_rival_analysis(
    tactical_data_list: list[dict],
    rival_name: str,
    competicion: str | None = None,
) -> tuple[str, float]:
    """Genera análisis del rival (P1) con Claude Sonnet 4.6.

    Args:
        tactical_data_list: Lista de JSONs tácticos de partidos del rival.
        rival_name: Nombre del equipo rival.
        competicion: Competición.

    Returns:
        Tuple de (markdown del análisis, coste en EUR).
    """
    start_time = time.time()

    if not ANTHROPIC_API_KEY:
        raise ValueError("ANTHROPIC_API_KEY no configurada. Añádela al .env")

    system_prompt = _load_system_prompt("ANALISIS_RIVAL.md")

    user_message = (
        f"Genera el análisis táctico del rival:\n"
        f"- Rival: {rival_name}\n"
    )
    if competicion:
        user_message += f"- Competición: {competicion}\n"
    user_message += f"\nPartidos analizados del rival ({len(tactical_data_list)}):\n"
    for i, td in enumerate(tactical_data_list[:3]):
        user_message += f"\n### Partido {i + 1}\n```json\n{_safe_json(td)}\n```\n"

    logger.info(
        "claude_rival_start",
        model="claude-sonnet-4-6",
        rival_name=rival_name,
        matches_count=len(tactical_data_list),
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

    input_tokens = response.usage.input_tokens
    output_tokens = response.usage.output_tokens
    cost_usd = (input_tokens * 3 / 1_000_000) + (output_tokens * 15 / 1_000_000)
    cost_eur = round(cost_usd * 0.92, 4)

    logger.info(
        "claude_rival_done",
        model="claude-sonnet-4-6",
        rival_name=rival_name,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_eur=cost_eur,
        duration_s=round(duration, 2),
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
