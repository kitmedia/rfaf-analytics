"""xG model service — wrapper around data_service.predict_xg.

Provides a higher-level interface for xG prediction used by
the Celery pipeline and API endpoints.
"""

import structlog

from backend.services.data_service import predict_xg, train_rfaf_xg_model, XG_MODEL_PATH

logger = structlog.get_logger()


def ensure_xg_model_exists() -> bool:
    """Train the xG model if it doesn't exist yet. Returns True if model is available."""
    if XG_MODEL_PATH.exists():
        logger.info("xg_model_available", path=str(XG_MODEL_PATH))
        return True

    try:
        metrics = train_rfaf_xg_model()
        logger.info("xg_model_trained_on_demand", **metrics)
        return True
    except Exception as exc:
        logger.error("xg_model_training_failed", error=str(exc))
        return False


def calculate_xg_for_shots(shots: list[dict]) -> list[dict]:
    """Calculate xG for a list of shots. Falls back to Gemini estimates if model unavailable."""
    return predict_xg(shots)


def get_xg_totals(shots: list[dict]) -> tuple[float, float]:
    """Calculate total xG for local and visitante teams.

    Returns (xg_local, xg_visitante).
    """
    xg_local = sum(
        s.get("xg_model") or s.get("xg_estimado") or 0
        for s in shots
        if s.get("equipo") == "local"
    )
    xg_visitante = sum(
        s.get("xg_model") or s.get("xg_estimado") or 0
        for s in shots
        if s.get("equipo") == "visitante"
    )
    return round(xg_local, 2), round(xg_visitante, 2)
