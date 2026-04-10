"""PostHog analytics tracking service.

Tracks key events: analysis_started, analysis_completed, analysis_failed,
pdf_downloaded, report_viewed, feedback_submitted, club_subscribed.

All events include club_id for cohort analysis and cost tracking.
"""

import os
from typing import Any

import structlog

logger = structlog.get_logger()

POSTHOG_API_KEY = os.getenv("POSTHOG_API_KEY", "")
POSTHOG_HOST = os.getenv("POSTHOG_HOST", "https://eu.posthog.com")

_client = None


def _get_client():
    """Lazy-init PostHog client. Returns None if no API key configured."""
    global _client
    if _client is not None:
        return _client
    if not POSTHOG_API_KEY:
        logger.warning("posthog_not_configured", hint="Set POSTHOG_API_KEY to enable analytics")
        return None
    try:
        from posthog import Posthog

        _client = Posthog(
            POSTHOG_API_KEY,
            host=POSTHOG_HOST,
            on_error=lambda e, items: logger.error("posthog_error", error=str(e)),
        )
        logger.info("posthog_initialized", host=POSTHOG_HOST)
        return _client
    except ImportError:
        logger.warning("posthog_not_installed", hint="pip install posthog")
        return None
    except Exception as exc:
        logger.error("posthog_init_error", error=str(exc))
        return None


def _track(distinct_id: str, event: str, properties: dict[str, Any] | None = None):
    """Send event to PostHog. Silent fail — never block the main flow."""
    client = _get_client()
    if client is None:
        return
    try:
        client.capture(
            distinct_id=distinct_id,
            event=event,
            properties=properties or {},
        )
        logger.debug("posthog_event_sent", event=event, distinct_id=distinct_id)
    except Exception as exc:
        logger.error("posthog_capture_error", event=event, error=str(exc))


def _identify(distinct_id: str, properties: dict[str, Any]):
    """Identify a club/user in PostHog for cohort analysis."""
    client = _get_client()
    if client is None:
        return
    try:
        client.identify(distinct_id=distinct_id, properties=properties)
    except Exception as exc:
        logger.error("posthog_identify_error", error=str(exc))


# ---------------------------------------------------------------------------
# Public tracking functions — called from routers and Celery tasks
# ---------------------------------------------------------------------------


def track_analysis_started(
    club_id: str,
    analysis_id: str,
    youtube_url: str,
    equipo_local: str,
    equipo_visitante: str,
    competicion: str | None = None,
):
    """Fired when POST /api/analyze/match enqueues a task."""
    _track(
        distinct_id=f"club_{club_id}",
        event="analysis_started",
        properties={
            "club_id": club_id,
            "analysis_id": analysis_id,
            "youtube_url": youtube_url,
            "equipo_local": equipo_local,
            "equipo_visitante": equipo_visitante,
            "competicion": competicion,
        },
    )


def track_analysis_completed(
    club_id: str,
    analysis_id: str,
    duration_s: float,
    cost_gemini: float,
    cost_claude: float,
    xg_local: float,
    xg_visitante: float,
):
    """Fired when Celery task finishes successfully."""
    cost_total = round(cost_gemini + cost_claude, 4)
    _track(
        distinct_id=f"club_{club_id}",
        event="analysis_completed",
        properties={
            "club_id": club_id,
            "analysis_id": analysis_id,
            "duration_s": round(duration_s, 1),
            "cost_gemini_eur": cost_gemini,
            "cost_claude_eur": cost_claude,
            "cost_total_eur": cost_total,
            "xg_local": xg_local,
            "xg_visitante": xg_visitante,
        },
    )


def track_analysis_failed(
    club_id: str,
    analysis_id: str,
    error_type: str,
    retry_count: int = 0,
):
    """Fired when Celery task fails (after max_retries)."""
    _track(
        distinct_id=f"club_{club_id}",
        event="analysis_failed",
        properties={
            "club_id": club_id,
            "analysis_id": analysis_id,
            "error_type": error_type,
            "retry_count": retry_count,
        },
    )


def track_report_viewed(
    club_id: str,
    analysis_id: str,
    report_type: str = "full",
):
    """Fired when GET /api/reports/{id} is called with status=done."""
    _track(
        distinct_id=f"club_{club_id}",
        event="report_viewed",
        properties={
            "club_id": club_id,
            "analysis_id": analysis_id,
            "report_type": report_type,
        },
    )


def track_pdf_downloaded(
    club_id: str,
    analysis_id: str,
):
    """Fired when GET /api/reports/{id}/pdf is called."""
    _track(
        distinct_id=f"club_{club_id}",
        event="pdf_downloaded",
        properties={
            "club_id": club_id,
            "analysis_id": analysis_id,
        },
    )


def track_chatbot_query(
    club_id: str,
    analysis_id: str,
    query_length: int,
):
    """Fired when POST /api/reports/{id}/chat is called."""
    _track(
        distinct_id=f"club_{club_id}",
        event="chatbot_query",
        properties={
            "club_id": club_id,
            "analysis_id": analysis_id,
            "query_length": query_length,
        },
    )


def track_feedback_submitted(
    club_id: str,
    rating: int,
    category: str,
):
    """Fired when POST /api/feedback is called."""
    _track(
        distinct_id=f"club_{club_id}",
        event="feedback_submitted",
        properties={
            "club_id": club_id,
            "rating": rating,
            "category": category,
        },
    )


def track_club_subscribed(
    club_id: str,
    plan: str,
    mrr_eur: float,
):
    """Fired when Stripe checkout.session.completed webhook is processed."""
    _track(
        distinct_id=f"club_{club_id}",
        event="club_subscribed",
        properties={
            "club_id": club_id,
            "plan": plan,
            "mrr_eur": mrr_eur,
        },
    )
    # Identify so PostHog shows plan in cohorts
    _identify(
        distinct_id=f"club_{club_id}",
        properties={"plan": plan, "mrr_eur": mrr_eur},
    )


def track_club_cancelled(
    club_id: str,
    plan: str,
):
    """Fired when Stripe subscription cancelled webhook is processed."""
    _track(
        distinct_id=f"club_{club_id}",
        event="club_cancelled",
        properties={"club_id": club_id, "plan": plan},
    )


def flush():
    """Force-flush pending events. Call on app shutdown."""
    client = _get_client()
    if client:
        try:
            client.shutdown()
        except Exception:
            pass
