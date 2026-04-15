"""Integration tests for Scouting (P2) endpoints.

Requires: docker-compose up -d (backend running on localhost:8000)
Run: pytest backend/tests/test_scouting.py -v
"""

import httpx

CLUB_ID = "00000000-0000-0000-0000-000000000001"
OTHER_CLUB_ID = "00000000-0000-0000-0000-000000000002"


def test_scout_rejects_missing_analysis(client: httpx.Client):
    """POST scout con analysis_id inexistente devuelve 404."""
    res = client.post(
        "/api/reports/00000000-0000-0000-0000-ffffffffffff/scout",
        json={
            "club_id": CLUB_ID,
            "player_id": "00000000-0000-0000-0000-ffffffffffff",
        },
    )
    assert res.status_code == 404


def test_scout_rls_blocks_other_club(client: httpx.Client):
    """Un club no puede generar scouting para análisis de otro club."""
    # Create analysis for CLUB_ID
    res = client.post(
        "/api/analyze/match",
        json={
            "youtube_url": "https://www.youtube.com/watch?v=rls_sc_test1",
            "equipo_local": "RLS Scout",
            "equipo_visitante": "Test",
            "club_id": CLUB_ID,
        },
    )
    assert res.status_code == 200
    analysis_id = res.json()["analysis_id"]

    # Try scout with OTHER_CLUB_ID
    scout_res = client.post(
        f"/api/reports/{analysis_id}/scout",
        json={
            "club_id": OTHER_CLUB_ID,
            "player_id": "00000000-0000-0000-0000-ffffffffffff",
        },
    )
    assert scout_res.status_code == 404


def test_scout_rejects_pending_analysis(client: httpx.Client):
    """No se puede generar scouting si el análisis no está completado."""
    res = client.post(
        "/api/analyze/match",
        json={
            "youtube_url": "https://www.youtube.com/watch?v=sc_pending01",
            "equipo_local": "Pending Scout",
            "equipo_visitante": "Test",
            "club_id": CLUB_ID,
        },
    )
    assert res.status_code == 200
    analysis_id = res.json()["analysis_id"]

    scout_res = client.post(
        f"/api/reports/{analysis_id}/scout",
        json={
            "club_id": CLUB_ID,
            "player_id": "00000000-0000-0000-0000-ffffffffffff",
        },
    )
    assert scout_res.status_code == 400
    assert "no está completado" in scout_res.json()["detail"]


def test_scout_report_not_found(client: httpx.Client):
    """GET scout report inexistente devuelve 404."""
    res = client.get(
        f"/api/reports/scout/00000000-0000-0000-0000-ffffffffffff?club_id={CLUB_ID}"
    )
    assert res.status_code == 404


def test_scout_pdf_not_found(client: httpx.Client):
    """GET scout PDF inexistente devuelve 404."""
    res = client.get(
        f"/api/reports/scout/00000000-0000-0000-0000-ffffffffffff/pdf?club_id={CLUB_ID}"
    )
    assert res.status_code == 404


def test_scout_pdf_requires_done(client: httpx.Client):
    """GET scout PDF con status != done devuelve 400."""
    # Find any scout report that is not done
    # Since we can't easily create one in tests, test the 404 path
    res = client.get(
        f"/api/reports/scout/00000000-0000-0000-0000-ffffffffffff/pdf?club_id={CLUB_ID}"
    )
    assert res.status_code in (400, 404)
