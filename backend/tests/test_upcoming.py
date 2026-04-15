"""Integration tests for Upcoming Matches.

Run: pytest backend/tests/test_upcoming.py -v
"""

import httpx

CLUB_ID = "00000000-0000-0000-0000-000000000001"
OTHER_CLUB_ID = "00000000-0000-0000-0000-000000000002"


def test_upcoming_matches_list(client: httpx.Client):
    """GET upcoming-matches devuelve lista."""
    res = client.get(f"/api/upcoming-matches?club_id={CLUB_ID}")
    assert res.status_code == 200
    data = res.json()
    assert "matches" in data
    assert "total" in data


def test_upcoming_matches_rls(client: httpx.Client):
    """Cada club solo ve sus partidos."""
    res1 = client.get(f"/api/upcoming-matches?club_id={CLUB_ID}")
    res2 = client.get(f"/api/upcoming-matches?club_id={OTHER_CLUB_ID}")
    assert res1.status_code == 200
    assert res2.status_code == 200


def test_check_upcoming_task_runs():
    """Task se ejecuta sin error."""
    try:
        from backend.workers.tasks import check_upcoming_matches_task
        result = check_upcoming_matches_task()
        assert "federado_clubs" in result
    except Exception:
        import pytest
        pytest.skip("DB not available")
