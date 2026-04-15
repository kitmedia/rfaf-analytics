"""Integration tests for degraded report and retry-section.

Run: pytest backend/tests/test_degraded.py -v
"""

import httpx

CLUB_ID = "00000000-0000-0000-0000-000000000001"


def test_retry_section_rejects_missing_analysis(client: httpx.Client):
    """POST retry-section con analysis inexistente devuelve 404."""
    res = client.post(
        "/api/reports/00000000-0000-0000-0000-ffffffffffff/retry-section",
        json={"club_id": CLUB_ID, "section": "narrative"},
    )
    assert res.status_code == 404


def test_retry_section_rejects_invalid_section(client: httpx.Client):
    """POST retry-section con seccion invalida devuelve 422."""
    res = client.post(
        "/api/reports/00000000-0000-0000-0000-ffffffffffff/retry-section",
        json={"club_id": CLUB_ID, "section": "invalid_section"},
    )
    assert res.status_code == 422


def test_retry_section_rls(client: httpx.Client):
    """RLS: otro club no puede retry secciones."""
    OTHER_CLUB = "00000000-0000-0000-0000-000000000002"
    # Create analysis for CLUB_ID
    res = client.post(
        "/api/analyze/match",
        json={
            "youtube_url": "https://www.youtube.com/watch?v=retry_rls01",
            "equipo_local": "Retry",
            "equipo_visitante": "RLS",
            "club_id": CLUB_ID,
        },
    )
    if res.status_code != 200:
        return
    analysis_id = res.json()["analysis_id"]

    retry_res = client.post(
        f"/api/reports/{analysis_id}/retry-section",
        json={"club_id": OTHER_CLUB, "section": "narrative"},
    )
    assert retry_res.status_code == 404
