"""Integration tests for RFAF Analytics API — run against live server.

Requires: docker-compose up -d (backend running on localhost:8000)
Run: pytest backend/tests/test_endpoints.py -v
"""

import httpx

CLUB_ID = "00000000-0000-0000-0000-000000000001"


def test_health(client: httpx.Client):
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] in ("ok", "degraded")
    assert data["version"] == "2.0.0"
    assert "db" in data
    assert "redis" in data


def test_get_club(client: httpx.Client):
    res = client.get(f"/api/clubs/{CLUB_ID}")
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == CLUB_ID
    assert data["active"] is True


def test_get_club_not_found(client: httpx.Client):
    res = client.get("/api/clubs/00000000-0000-0000-0000-ffffffffffff")
    assert res.status_code == 404


def test_create_club_duplicate(client: httpx.Client):
    res = client.post(
        "/api/clubs",
        json={"name": "Duplicate", "email": "contacto@cdejea.es", "plan": "basico"},
    )
    assert res.status_code == 409  # email already exists


def test_analyze_validates_youtube_url(client: httpx.Client):
    res = client.post(
        "/api/analyze/match",
        json={
            "youtube_url": "https://not-youtube.com/watch",
            "equipo_local": "A",
            "equipo_visitante": "B",
            "club_id": CLUB_ID,
        },
    )
    assert res.status_code == 422


def test_analyze_rejects_invalid_club(client: httpx.Client):
    res = client.post(
        "/api/analyze/match",
        json={
            "youtube_url": "https://www.youtube.com/watch?v=test1234567",
            "equipo_local": "A",
            "equipo_visitante": "B",
            "club_id": "00000000-0000-0000-0000-ffffffffffff",
        },
    )
    assert res.status_code == 404


def test_analyze_enqueues_successfully(client: httpx.Client):
    res = client.post(
        "/api/analyze/match",
        json={
            "youtube_url": "https://www.youtube.com/watch?v=ci_pytest_ok",
            "equipo_local": "CD Ejea",
            "equipo_visitante": "SD Tarazona",
            "competicion": "Tercera RFEF",
            "club_id": CLUB_ID,
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert "analysis_id" in data
    assert data["status"] == "pending"
    assert data["check_url"].startswith("/api/analyze/status/")

    # Verify status endpoint works
    status_res = client.get(f"/api/analyze/status/{data['analysis_id']}")
    assert status_res.status_code == 200
    assert status_res.json()["analysis_id"] == data["analysis_id"]


def test_analysis_status_not_found(client: httpx.Client):
    res = client.get("/api/analyze/status/00000000-0000-0000-0000-ffffffffffff")
    assert res.status_code == 404


def test_list_reports(client: httpx.Client):
    res = client.get(f"/api/reports?club_id={CLUB_ID}")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)


def test_report_not_found(client: httpx.Client):
    res = client.get("/api/reports/00000000-0000-0000-0000-ffffffffffff")
    assert res.status_code == 404


def test_feedback_create(client: httpx.Client):
    res = client.post(
        "/api/feedback",
        json={
            "club_id": CLUB_ID,
            "category": "precision",
            "rating": 4,
            "comment": "Test desde pytest",
        },
    )
    assert res.status_code == 201
    data = res.json()
    assert data["rating"] == 4
    assert data["category"] == "precision"


def test_feedback_invalid_rating(client: httpx.Client):
    res = client.post(
        "/api/feedback",
        json={"club_id": CLUB_ID, "category": "precision", "rating": 0},
    )
    assert res.status_code == 422


def test_feedback_invalid_category(client: httpx.Client):
    res = client.post(
        "/api/feedback",
        json={"club_id": CLUB_ID, "category": "invalid", "rating": 3},
    )
    assert res.status_code == 422


def test_feedback_list(client: httpx.Client):
    res = client.get("/api/feedback")
    assert res.status_code == 200
    data = res.json()
    assert "feedbacks" in data
    assert "total" in data
    assert "avg_rating" in data
    assert data["total"] >= 1


def test_admin_dashboard(client: httpx.Client):
    res = client.get("/api/admin/dashboard")
    assert res.status_code == 200
    data = res.json()
    assert "mrr_eur" in data
    assert "total_clubs" in data
    assert "active_clubs" in data
    assert "clubs_by_plan" in data
    assert data["total_clubs"] >= 1


def test_pdf_requires_done_analysis(client: httpx.Client):
    # Create a pending analysis
    res = client.post(
        "/api/analyze/match",
        json={
            "youtube_url": "https://www.youtube.com/watch?v=pdf_test_ci1",
            "equipo_local": "PDF",
            "equipo_visitante": "Test",
            "club_id": CLUB_ID,
        },
    )
    aid = res.json()["analysis_id"]
    # PDF should fail since analysis is pending
    pdf_res = client.get(f"/api/reports/{aid}/pdf")
    assert pdf_res.status_code == 400
