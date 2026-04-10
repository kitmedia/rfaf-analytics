"""Visualizaciones mplsoccer: shot maps, pass networks, xG timeline."""

import base64
import io

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import structlog
from mplsoccer import Pitch, VerticalPitch

logger = structlog.get_logger()


def _fig_to_base64(fig) -> str:
    """Convert matplotlib figure to base64 PNG string."""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=120, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("utf-8")


def generate_shot_map(shots: list[dict], equipo: str, equipo_name: str) -> str:
    """Generate vertical shot map for one team. Returns base64 PNG."""
    team_shots = [s for s in shots if s.get("equipo") == equipo]

    pitch = VerticalPitch(
        pitch_type="custom",
        pitch_length=100,
        pitch_width=100,
        half=True,
        pitch_color="#f0f0f0",
        line_color="#333333",
    )
    fig, ax = pitch.draw(figsize=(8, 6))
    ax.set_title(f"Mapa de tiros - {equipo_name}", fontsize=14, fontweight="bold", pad=10)

    if not team_shots:
        ax.text(50, 50, "Sin tiros detectados", ha="center", va="center", fontsize=12, color="gray")
        return _fig_to_base64(fig)

    for shot in team_shots:
        x = shot.get("x", 50)
        y = shot.get("y", 50)
        xg = shot.get("xg_estimado") or shot.get("xg_model") or 0.05
        is_goal = shot.get("resultado") == "gol"

        color = "#d62728" if is_goal else "#1f77b4"
        edge = "gold" if is_goal else "white"
        size = max(100, xg * 1500)

        pitch.scatter(
            x, y, ax=ax,
            s=size, color=color, edgecolors=edge, linewidths=1.5,
            zorder=3, alpha=0.8,
        )

    # Legend
    ax.scatter([], [], s=100, c="#d62728", edgecolors="gold", linewidths=1.5, label="Gol")
    ax.scatter([], [], s=100, c="#1f77b4", edgecolors="white", linewidths=1.5, label="No gol")
    ax.legend(loc="lower left", fontsize=9)

    return _fig_to_base64(fig)


def generate_pass_network(passes: list[dict], equipo_name: str) -> str:
    """Generate pass network diagram. Returns base64 PNG."""
    pitch = Pitch(
        pitch_type="custom",
        pitch_length=100,
        pitch_width=100,
        pitch_color="#f0f0f0",
        line_color="#333333",
    )
    fig, ax = pitch.draw(figsize=(10, 7))
    ax.set_title(f"Red de pases - {equipo_name}", fontsize=14, fontweight="bold", pad=10)

    if not passes:
        ax.text(50, 50, "Sin datos de pases", ha="center", va="center", fontsize=12, color="gray")
        return _fig_to_base64(fig)

    # Build node positions and edge weights
    players = set()
    for p in passes:
        players.add(p.get("de", "?"))
        players.add(p.get("a", "?"))

    player_list = sorted(players)
    n = len(player_list)

    # Distribute players in a formation-like layout
    positions = {}
    for i, player in enumerate(player_list):
        angle = 2 * np.pi * i / max(n, 1)
        x = 50 + 30 * np.cos(angle)
        y = 50 + 25 * np.sin(angle)
        positions[player] = (x, y)

    # Draw edges
    max_count = max((p.get("cantidad", 1) for p in passes), default=1)
    for p in passes:
        de = p.get("de", "?")
        a = p.get("a", "?")
        count = p.get("cantidad", 1)
        if de in positions and a in positions:
            x1, y1 = positions[de]
            x2, y2 = positions[a]
            width = max(0.5, (count / max_count) * 5)
            alpha = max(0.3, count / max_count)
            ax.plot([x1, x2], [y1, y2], color="#1f77b4", linewidth=width, alpha=alpha, zorder=1)

    # Draw nodes
    for player, (x, y) in positions.items():
        ax.scatter(x, y, s=400, color="#2ca02c", edgecolors="white", linewidths=2, zorder=3)
        ax.text(x, y, player[:8], ha="center", va="center", fontsize=7, fontweight="bold", color="white", zorder=4)

    return _fig_to_base64(fig)


def generate_xg_timeline(shots: list[dict], equipo_local: str, equipo_visitante: str) -> str:
    """Generate cumulative xG timeline chart. Returns base64 PNG."""
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.set_title("Evolución xG acumulado", fontsize=14, fontweight="bold")
    ax.set_xlabel("Minuto")
    ax.set_ylabel("xG acumulado")

    if not shots:
        ax.text(45, 0.5, "Sin datos de tiros", ha="center", va="center", fontsize=12, color="gray")
        return _fig_to_base64(fig)

    # Sort by minute
    sorted_shots = sorted(shots, key=lambda s: s.get("minuto", 0))

    local_xg, visit_xg = [0], [0]
    local_min, visit_min = [0], [0]

    for s in sorted_shots:
        minute = s.get("minuto", 0)
        xg = s.get("xg_estimado") or s.get("xg_model") or 0
        if s.get("equipo") == "local":
            local_xg.append(local_xg[-1] + xg)
            local_min.append(minute)
        elif s.get("equipo") == "visitante":
            visit_xg.append(visit_xg[-1] + xg)
            visit_min.append(minute)

    ax.step(local_min, local_xg, where="post", color="#1f77b4", linewidth=2, label=f"{equipo_local} ({local_xg[-1]:.2f})")
    ax.step(visit_min, visit_xg, where="post", color="#d62728", linewidth=2, label=f"{equipo_visitante} ({visit_xg[-1]:.2f})")

    ax.legend(fontsize=10)
    ax.set_xlim(0, 95)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()

    return _fig_to_base64(fig)


def generate_all_charts(
    tactical_data: dict,
    equipo_local: str,
    equipo_visitante: str,
) -> dict:
    """Generate all charts from tactical data. Returns dict of base64 PNGs."""
    shots = tactical_data.get("shots", [])
    passes_local = (tactical_data.get("passes_network") or {}).get("local", [])
    passes_visit = (tactical_data.get("passes_network") or {}).get("visitante", [])

    charts = {}

    try:
        charts["shot_map_local"] = generate_shot_map(shots, "local", equipo_local)
    except Exception as e:
        logger.error("chart_error", chart="shot_map_local", error=str(e))

    try:
        charts["shot_map_visitante"] = generate_shot_map(shots, "visitante", equipo_visitante)
    except Exception as e:
        logger.error("chart_error", chart="shot_map_visitante", error=str(e))

    try:
        charts["pass_network_local"] = generate_pass_network(passes_local, equipo_local)
    except Exception as e:
        logger.error("chart_error", chart="pass_network_local", error=str(e))

    try:
        charts["pass_network_visitante"] = generate_pass_network(passes_visit, equipo_visitante)
    except Exception as e:
        logger.error("chart_error", chart="pass_network_visitante", error=str(e))

    try:
        charts["xg_timeline"] = generate_xg_timeline(shots, equipo_local, equipo_visitante)
    except Exception as e:
        logger.error("chart_error", chart="xg_timeline", error=str(e))

    logger.info("charts_generated", count=len(charts), charts=list(charts.keys()))
    return charts
