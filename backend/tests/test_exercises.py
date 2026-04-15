"""Integration tests for Exercise Tracking endpoints.

Requires: docker-compose up -d (backend running on localhost:8000)
Run: pytest backend/tests/test_exercises.py -v
"""

import httpx

CLUB_ID = "00000000-0000-0000-0000-000000000001"
OTHER_CLUB_ID = "00000000-0000-0000-0000-000000000002"


def _find_done_analysis(client: httpx.Client) -> str | None:
    """Find a done analysis for CLUB_ID."""
    res = client.get(f"/api/reports?club_id={CLUB_ID}")
    if res.status_code != 200:
        return None
    reports = res.json()
    done = [r for r in reports if r["status"] == "done"]
    return done[0]["analysis_id"] if done else None


def test_mark_complete_and_get(client: httpx.Client):
    """POST mark-complete crea registro y GET by-analysis lo devuelve."""
    analysis_id = _find_done_analysis(client)
    if not analysis_id:
        import pytest
        pytest.skip("No done analysis available")

    # Mark exercise
    res = client.post(
        "/api/exercises/mark-complete",
        json={
            "club_id": CLUB_ID,
            "analysis_id": analysis_id,
            "exercise_name": "Rondo de Salida Test",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["exercise_name"] == "Rondo de Salida Test"
    assert data["completed"] is True
    assert data["completed_date"] is not None

    # Verify via GET
    get_res = client.get(f"/api/exercises/by-analysis/{analysis_id}?club_id={CLUB_ID}")
    assert get_res.status_code == 200
    exercises = get_res.json()["exercises"]
    names = [e["exercise_name"] for e in exercises]
    assert "Rondo de Salida Test" in names


def test_unmark_exercise(client: httpx.Client):
    """POST unmark elimina registro."""
    analysis_id = _find_done_analysis(client)
    if not analysis_id:
        import pytest
        pytest.skip("No done analysis available")

    # First mark
    client.post(
        "/api/exercises/mark-complete",
        json={
            "club_id": CLUB_ID,
            "analysis_id": analysis_id,
            "exercise_name": "Pressing Coordinado Test",
        },
    )

    # Then unmark
    res = client.post(
        "/api/exercises/unmark",
        json={
            "club_id": CLUB_ID,
            "analysis_id": analysis_id,
            "exercise_name": "Pressing Coordinado Test",
        },
    )
    assert res.status_code == 204

    # Verify removed
    get_res = client.get(f"/api/exercises/by-analysis/{analysis_id}?club_id={CLUB_ID}")
    assert get_res.status_code == 200
    names = [e["exercise_name"] for e in get_res.json()["exercises"]]
    assert "Pressing Coordinado Test" not in names


def test_rls_blocks_other_club(client: httpx.Client):
    """Un club no puede acceder a ejercicios de otro club."""
    analysis_id = _find_done_analysis(client)
    if not analysis_id:
        import pytest
        pytest.skip("No done analysis available")

    # Try to mark with wrong club_id
    res = client.post(
        "/api/exercises/mark-complete",
        json={
            "club_id": OTHER_CLUB_ID,
            "analysis_id": analysis_id,
            "exercise_name": "RLS Test Exercise",
        },
    )
    assert res.status_code == 404

    # Try to GET with wrong club_id
    get_res = client.get(f"/api/exercises/by-analysis/{analysis_id}?club_id={OTHER_CLUB_ID}")
    assert get_res.status_code == 404


def test_weekly_summary(client: httpx.Client):
    """GET weekly-summary devuelve conteo correcto."""
    res = client.get(f"/api/exercises/weekly-summary?club_id={CLUB_ID}")
    assert res.status_code == 200
    data = res.json()
    assert "completed_count" in data
    assert "total_count" in data
    assert isinstance(data["completed_count"], int)
    assert isinstance(data["total_count"], int)


def test_mark_complete_idempotent(client: httpx.Client):
    """Marcar dos veces el mismo ejercicio no crea duplicado."""
    analysis_id = _find_done_analysis(client)
    if not analysis_id:
        import pytest
        pytest.skip("No done analysis available")

    exercise_name = "Idempotent Test Exercise"

    # Mark twice
    client.post(
        "/api/exercises/mark-complete",
        json={"club_id": CLUB_ID, "analysis_id": analysis_id, "exercise_name": exercise_name},
    )
    client.post(
        "/api/exercises/mark-complete",
        json={"club_id": CLUB_ID, "analysis_id": analysis_id, "exercise_name": exercise_name},
    )

    # Should only appear once
    get_res = client.get(f"/api/exercises/by-analysis/{analysis_id}?club_id={CLUB_ID}")
    exercises = get_res.json()["exercises"]
    count = sum(1 for e in exercises if e["exercise_name"] == exercise_name)
    assert count == 1
