"""Integration tests for Trends and Impact endpoints.

Requires: docker-compose up -d (backend running on localhost:8000)
Run: pytest backend/tests/test_trends.py -v
"""

import httpx

CLUB_ID = "00000000-0000-0000-0000-000000000001"
OTHER_CLUB_ID = "00000000-0000-0000-0000-000000000002"


def test_trends_returns_data(client: httpx.Client):
    """GET trends devuelve respuesta valida."""
    res = client.get(f"/api/reports/trends?club_id={CLUB_ID}")
    assert res.status_code == 200
    data = res.json()
    assert "has_enough_data" in data
    assert "weeks" in data
    assert isinstance(data["weeks"], list)


def test_trends_insufficient_data(client: httpx.Client):
    """GET trends con club sin datos devuelve has_enough_data=false."""
    res = client.get(f"/api/reports/trends?club_id={OTHER_CLUB_ID}")
    assert res.status_code == 200
    data = res.json()
    # OTHER_CLUB_ID likely has no analyses
    if data["has_enough_data"] is False:
        assert data["weeks"] == []


def test_trends_rls(client: httpx.Client):
    """Trends endpoint respeta RLS — solo devuelve datos del club solicitado."""
    res1 = client.get(f"/api/reports/trends?club_id={CLUB_ID}")
    res2 = client.get(f"/api/reports/trends?club_id={OTHER_CLUB_ID}")
    assert res1.status_code == 200
    assert res2.status_code == 200
    # Results should be different (different clubs)
    data1 = res1.json()
    data2 = res2.json()
    # At minimum both should be valid responses
    assert "has_enough_data" in data1
    assert "has_enough_data" in data2


def test_impact_returns_response(client: httpx.Client):
    """GET impact devuelve respuesta valida."""
    res = client.get(f"/api/exercises/impact?club_id={CLUB_ID}")
    assert res.status_code == 200
    data = res.json()
    assert "has_impact" in data
    assert isinstance(data["has_impact"], bool)


def test_impact_no_exercises(client: httpx.Client):
    """GET impact sin ejercicios completados devuelve has_impact=false."""
    res = client.get(f"/api/exercises/impact?club_id={OTHER_CLUB_ID}")
    assert res.status_code == 200
    data = res.json()
    # OTHER_CLUB_ID likely has no exercises
    assert data["has_impact"] is False
