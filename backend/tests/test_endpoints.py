"""Integration tests for RFAF Analytics API — run against live server.

Requires: docker-compose up -d AND JWT_SECRET env var set
Run: pytest backend/tests/test_endpoints.py -v
"""

import httpx


# --- Public endpoints ---


def test_health(client: httpx.Client):
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] in ("ok", "degraded")
    assert data["version"] == "2.0.0"
    assert "db" in data
    assert "redis" in data


# --- Auth: 401 on protected endpoints without token ---


def test_analyze_requires_auth(client: httpx.Client):
    res = client.post(
        "/api/analyze/match",
        json={
            "youtube_url": "https://www.youtube.com/watch?v=test1234567",
            "equipo_local": "A",
            "equipo_visitante": "B",
            "club_id": "00000000-0000-0000-0000-000000000001",
        },
    )
    assert res.status_code == 401


def test_reports_list_requires_auth(client: httpx.Client):
    res = client.get("/api/reports")
    assert res.status_code == 401


def test_report_detail_requires_auth(client: httpx.Client):
    res = client.get("/api/reports/00000000-0000-0000-0000-ffffffffffff")
    assert res.status_code == 401


def test_admin_dashboard_requires_auth(client: httpx.Client):
    res = client.get("/api/admin/dashboard")
    assert res.status_code == 401


def test_feedback_create_requires_auth(client: httpx.Client):
    res = client.post(
        "/api/feedback",
        json={"club_id": "00000000-0000-0000-0000-000000000001", "category": "precision", "rating": 4},
    )
    assert res.status_code == 401


def test_feedback_list_requires_auth(client: httpx.Client):
    res = client.get("/api/feedback")
    assert res.status_code == 401


def test_club_get_requires_auth(client: httpx.Client):
    res = client.get("/api/clubs/00000000-0000-0000-0000-000000000001")
    assert res.status_code == 401


# --- Authenticated endpoints ---


def test_get_club(auth_client: httpx.Client, club_id: str):
    res = auth_client.get(f"/api/clubs/{club_id}")
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == club_id
    assert data["active"] is True


def test_get_club_forbidden_other_club(auth_client: httpx.Client):
    res = auth_client.get("/api/clubs/00000000-0000-0000-0000-ffffffffffff")
    assert res.status_code in (403, 404)


def test_analyze_validates_youtube_url(auth_client: httpx.Client, club_id: str):
    res = auth_client.post(
        "/api/analyze/match",
        json={
            "youtube_url": "https://not-youtube.com/watch",
            "equipo_local": "A",
            "equipo_visitante": "B",
            "club_id": club_id,
        },
    )
    assert res.status_code == 422


def test_analyze_enqueues_successfully(auth_client: httpx.Client, club_id: str):
    res = auth_client.post(
        "/api/analyze/match",
        json={
            "youtube_url": "https://www.youtube.com/watch?v=ci_pytest_ok",
            "equipo_local": "CD Ejea",
            "equipo_visitante": "SD Tarazona",
            "competicion": "Tercera RFEF",
            "club_id": club_id,
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert "analysis_id" in data
    assert data["status"] == "pending"
    assert data["check_url"].startswith("/api/analyze/status/")

    # Verify status endpoint works
    status_res = auth_client.get(f"/api/analyze/status/{data['analysis_id']}")
    assert status_res.status_code == 200
    assert status_res.json()["analysis_id"] == data["analysis_id"]


def test_analyze_wrong_club_forbidden(auth_client: httpx.Client):
    res = auth_client.post(
        "/api/analyze/match",
        json={
            "youtube_url": "https://www.youtube.com/watch?v=test1234567",
            "equipo_local": "A",
            "equipo_visitante": "B",
            "club_id": "00000000-0000-0000-0000-ffffffffffff",
        },
    )
    assert res.status_code == 403


def test_analysis_status_not_found(auth_client: httpx.Client):
    res = auth_client.get("/api/analyze/status/00000000-0000-0000-0000-ffffffffffff")
    assert res.status_code == 404


def test_list_reports(auth_client: httpx.Client):
    res = auth_client.get("/api/reports")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)


def test_report_not_found(auth_client: httpx.Client):
    res = auth_client.get("/api/reports/00000000-0000-0000-0000-ffffffffffff")
    assert res.status_code == 404


def test_feedback_create(auth_client: httpx.Client, club_id: str):
    res = auth_client.post(
        "/api/feedback",
        json={
            "club_id": club_id,
            "category": "precision",
            "rating": 4,
            "comment": "Test desde pytest",
        },
    )
    assert res.status_code == 201
    data = res.json()
    assert data["rating"] == 4
    assert data["category"] == "precision"


def test_feedback_invalid_rating(auth_client: httpx.Client, club_id: str):
    res = auth_client.post(
        "/api/feedback",
        json={"club_id": club_id, "category": "precision", "rating": 0},
    )
    assert res.status_code == 422


def test_feedback_invalid_category(auth_client: httpx.Client, club_id: str):
    res = auth_client.post(
        "/api/feedback",
        json={"club_id": club_id, "category": "invalid", "rating": 3},
    )
    assert res.status_code == 422


def test_feedback_list(auth_client: httpx.Client):
    res = auth_client.get("/api/feedback")
    assert res.status_code == 200
    data = res.json()
    assert "feedbacks" in data
    assert "total" in data
    assert "avg_rating" in data


def test_pdf_requires_done_analysis(auth_client: httpx.Client, club_id: str):
    # Create a pending analysis
    res = auth_client.post(
        "/api/analyze/match",
        json={
            "youtube_url": "https://www.youtube.com/watch?v=pdf_test_ci1",
            "equipo_local": "PDF",
            "equipo_visitante": "Test",
            "club_id": club_id,
        },
    )
    aid = res.json()["analysis_id"]
    # PDF should fail since analysis is pending
    pdf_res = auth_client.get(f"/api/reports/{aid}/pdf")
    assert pdf_res.status_code == 400
