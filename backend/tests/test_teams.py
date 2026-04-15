"""Integration tests for Teams search and analyses.

Run: pytest backend/tests/test_teams.py -v
"""

import httpx

CLUB_ID = "00000000-0000-0000-0000-000000000001"


def test_search_teams(client: httpx.Client):
    """GET teams/search devuelve lista."""
    res = client.get("/api/teams/search?q=CD")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)


def test_search_requires_min_chars(client: httpx.Client):
    """Busqueda con <2 chars devuelve 422."""
    res = client.get("/api/teams/search?q=A")
    assert res.status_code == 422


def test_team_analyses(client: httpx.Client):
    """GET team analyses devuelve estructura correcta."""
    res = client.get("/api/teams/TestTeam/analyses")
    assert res.status_code == 200
    data = res.json()
    assert "team_name" in data
    assert "analysis_count" in data
    assert "analyses" in data


def test_manual_upcoming(client: httpx.Client):
    """POST manual upcoming crea registro."""
    from datetime import datetime, timedelta
    future = (datetime.utcnow() + timedelta(days=7)).isoformat()
    res = client.post(
        "/api/upcoming-matches/manual",
        json={
            "club_id": CLUB_ID,
            "rival_name": "Test Rival FC",
            "match_date": future,
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["rival_name"] == "Test Rival FC"
    assert data["source"] == "manual_input"
