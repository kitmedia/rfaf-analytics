"""Sprint 9 integration tests.

Tests:
- GET /api/health returns all checks
- POST /api/feedback tracks correctly (smoke)
- POST /api/reports/{id}/chat returns 404 for unknown id
- tracking_service silent-fails without POSTHOG_API_KEY
"""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from backend.main import app


@pytest.mark.asyncio
async def test_health_check_structure():
    """Health check debe devolver version, status, db y redis."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert "version" in data
    assert "status" in data
    # db y redis can be "connected" or "error: ..." depending on env
    assert "db" in data
    assert "redis" in data


@pytest.mark.asyncio
async def test_chat_unknown_analysis():
    """Chat on unknown analysis_id must return 404."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            f"/api/reports/{uuid.uuid4()}/chat",
            json={"question": "¿Cuál fue el xG del equipo local?", "club_id": str(uuid.uuid4())},
        )
    assert response.status_code == 404
    assert "no encontrado" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_feedback_invalid_rating():
    """Rating fuera de rango debe devolver 422."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/feedback",
            json={
                "club_id": str(uuid.uuid4()),
                "category": "analisis",
                "rating": 10,  # invalid
                "comment": "test",
            },
        )
    assert response.status_code == 422


def test_tracking_silent_fail_without_key(monkeypatch):
    """tracking_service debe fallar silenciosamente si no hay POSTHOG_API_KEY."""
    monkeypatch.setenv("POSTHOG_API_KEY", "")

    # Force re-init
    import backend.services.tracking_service as ts
    ts._client = None

    # These should not raise
    ts.track_analysis_started(
        club_id="test-club",
        analysis_id="test-analysis",
        youtube_url="https://youtube.com/watch?v=test",
        equipo_local="SD Huesca",
        equipo_visitante="Real Zaragoza",
    )
    ts.track_feedback_submitted(club_id="test-club", rating=5, category="analisis")
    ts.track_pdf_downloaded(club_id="test-club", analysis_id="test-analysis")
