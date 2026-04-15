"""Integration tests for Training Plan (P3) endpoint.

Requires: docker-compose up -d (backend running on localhost:8000)
Run: pytest backend/tests/test_training_plan.py -v
"""

import httpx

CLUB_ID = "00000000-0000-0000-0000-000000000001"
OTHER_CLUB_ID = "00000000-0000-0000-0000-000000000002"


def test_training_plan_enqueues_for_done_analysis(client: httpx.Client):
    """POST training-plan con analisis DONE encola correctamente (200)."""
    # Find a done analysis without training plan
    reports_res = client.get(f"/api/reports?club_id={CLUB_ID}")
    if reports_res.status_code != 200:
        import pytest
        pytest.skip("No reports available")

    reports = reports_res.json()
    done_reports = [r for r in reports if r["status"] == "done"]

    for report in done_reports:
        detail_res = client.get(f"/api/reports/{report['analysis_id']}")
        if detail_res.status_code == 200:
            detail = detail_res.json()
            if detail.get("training_plan_json") is None:
                tp_res = client.post(
                    f"/api/reports/{report['analysis_id']}/training-plan",
                    json={"club_id": CLUB_ID},
                )
                assert tp_res.status_code == 200
                data = tp_res.json()
                assert data["status"] == "pending"
                assert data["analysis_id"] == report["analysis_id"]
                return

    import pytest
    pytest.skip("No done analysis without training plan found for happy path test")


def test_training_plan_rejects_missing_analysis(client: httpx.Client):
    """POST training-plan con analysis_id inexistente devuelve 404."""
    res = client.post(
        "/api/reports/00000000-0000-0000-0000-ffffffffffff/training-plan",
        json={"club_id": CLUB_ID},
    )
    assert res.status_code == 404


def test_training_plan_rls_blocks_other_club(client: httpx.Client):
    """Un club no puede generar plan para análisis de otro club."""
    # First create an analysis for CLUB_ID
    res = client.post(
        "/api/analyze/match",
        json={
            "youtube_url": "https://www.youtube.com/watch?v=rls_tp_test1",
            "equipo_local": "RLS Local",
            "equipo_visitante": "RLS Visit",
            "club_id": CLUB_ID,
        },
    )
    assert res.status_code == 200
    analysis_id = res.json()["analysis_id"]

    # Try to generate training plan with OTHER_CLUB_ID
    tp_res = client.post(
        f"/api/reports/{analysis_id}/training-plan",
        json={"club_id": OTHER_CLUB_ID},
    )
    assert tp_res.status_code == 404


def test_training_plan_rejects_pending_analysis(client: httpx.Client):
    """No se puede generar plan si el análisis no está completado."""
    # Create a pending analysis
    res = client.post(
        "/api/analyze/match",
        json={
            "youtube_url": "https://www.youtube.com/watch?v=tp_pending01",
            "equipo_local": "Pending",
            "equipo_visitante": "Test",
            "club_id": CLUB_ID,
        },
    )
    assert res.status_code == 200
    analysis_id = res.json()["analysis_id"]

    # Try to generate training plan for pending analysis
    tp_res = client.post(
        f"/api/reports/{analysis_id}/training-plan",
        json={"club_id": CLUB_ID},
    )
    assert tp_res.status_code == 400
    assert "no está completado" in tp_res.json()["detail"]


def test_training_plan_idempotency(client: httpx.Client, admin_client: httpx.Client):
    """Si P3 ya existe, no se regenera (devuelve 409)."""
    # Find a done analysis with training_plan_json already set
    reports_res = client.get(f"/api/reports?club_id={CLUB_ID}")
    if reports_res.status_code != 200:
        import pytest
        pytest.skip("No reports available to test idempotency")

    reports = reports_res.json()
    done_reports = [r for r in reports if r["status"] == "done"]

    for report in done_reports:
        detail_res = client.get(f"/api/reports/{report['analysis_id']}")
        if detail_res.status_code == 200:
            detail = detail_res.json()
            if detail.get("training_plan_json") is not None:
                # This analysis already has a training plan — POST should return 409
                tp_res = client.post(
                    f"/api/reports/{report['analysis_id']}/training-plan",
                    json={"club_id": CLUB_ID},
                )
                assert tp_res.status_code == 409
                assert "ya fue generado" in tp_res.json()["detail"]
                return

    import pytest
    pytest.skip("No done analysis with existing training plan found to test idempotency")
