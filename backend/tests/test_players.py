"""Integration tests for Players listing endpoint.

Requires: docker-compose up -d (backend running on localhost:8000)
Run: pytest backend/tests/test_players.py -v
"""

import httpx

CLUB_ID = "00000000-0000-0000-0000-000000000001"
OTHER_CLUB_ID = "00000000-0000-0000-0000-000000000002"


def test_list_players(client: httpx.Client):
    """GET players devuelve lista para club."""
    res = client.get(f"/api/players?club_id={CLUB_ID}")
    assert res.status_code == 200
    data = res.json()
    assert "players" in data
    assert "total" in data
    assert isinstance(data["players"], list)


def test_list_players_rls(client: httpx.Client):
    """Cada club solo ve sus propios jugadores."""
    res1 = client.get(f"/api/players?club_id={CLUB_ID}")
    res2 = client.get(f"/api/players?club_id={OTHER_CLUB_ID}")
    assert res1.status_code == 200
    assert res2.status_code == 200
    # Different clubs should have different (or empty) player lists
    ids1 = {p["id"] for p in res1.json()["players"]}
    ids2 = {p["id"] for p in res2.json()["players"]}
    assert ids1.isdisjoint(ids2), "RLS violation: clubs share players"
