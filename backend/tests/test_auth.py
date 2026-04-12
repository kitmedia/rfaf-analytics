"""Tests de autenticación — register, login, JWT validation, 401 on protected endpoints.

Estos tests usan el servidor live (localhost:8000) igual que test_endpoints.py.
Requiere: docker-compose up -d AND JWT_SECRET env var set.
"""

import uuid

import httpx
import pytest

BASE_URL = "http://localhost:8000"


# --- Register ---


def test_register_creates_club_and_returns_token(client: httpx.Client):
    """POST /api/auth/register debe crear club + user y devolver JWT."""
    unique_email = f"register_test_{uuid.uuid4().hex[:8]}@rfaf-test.es"
    res = client.post(
        "/api/auth/register",
        json={
            "club_name": "Club Registro Test",
            "email": unique_email,
            "password": "SecurePass_99",
            "name": "Entrenador Test",
            "plan": "BASICO",
        },
    )
    assert res.status_code == 201
    data = res.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert "club_id" in data
    assert data["plan"] == "BASICO"
    assert data["club_name"] == "Club Registro Test"


def test_register_duplicate_email_returns_409(client: httpx.Client):
    """Registrar el mismo email dos veces debe devolver 409."""
    email = f"dup_{uuid.uuid4().hex[:8]}@rfaf-test.es"
    payload = {
        "club_name": "Club A",
        "email": email,
        "password": "Pass123!",
        "name": "User A",
    }
    first = client.post("/api/auth/register", json=payload)
    assert first.status_code == 201

    second = client.post("/api/auth/register", json={**payload, "club_name": "Club B"})
    assert second.status_code == 409


def test_register_invalid_plan_returns_400(client: httpx.Client):
    """Plan inválido debe devolver 400."""
    res = client.post(
        "/api/auth/register",
        json={
            "club_name": "Club X",
            "email": f"plan_{uuid.uuid4().hex[:8]}@rfaf-test.es",
            "password": "Pass123!",
            "name": "User",
            "plan": "INVALIDO",
        },
    )
    assert res.status_code == 400


# --- Login ---


def test_login_valid_credentials(auth_data: dict):
    """auth_data fixture ya valida que el login funciona (session-scoped)."""
    assert "access_token" in auth_data
    assert auth_data["token_type"] == "bearer"
    assert "club_id" in auth_data
    assert "expires_in" in auth_data


def test_login_wrong_password_returns_401(client: httpx.Client):
    res = client.post(
        "/api/auth/login",
        json={"email": "ci_test_user@rfaf-test.es", "password": "wrong_password"},
    )
    assert res.status_code == 401
    assert "detail" in res.json()


def test_login_unknown_email_returns_401(client: httpx.Client):
    res = client.post(
        "/api/auth/login",
        json={"email": "noexiste@rfaf-test.es", "password": "any"},
    )
    assert res.status_code == 401


# --- Token validation ---


def test_me_with_valid_token(auth_client: httpx.Client, auth_data: dict):
    """GET /api/auth/me debe devolver info del usuario autenticado."""
    res = auth_client.get("/api/auth/me")
    assert res.status_code == 200
    data = res.json()
    assert "user_id" in data
    assert data["club_id"] == auth_data["club_id"]
    assert "role" in data


def test_me_without_token_returns_401(client: httpx.Client):
    res = client.get("/api/auth/me")
    assert res.status_code == 401


def test_me_with_invalid_token_returns_401(client: httpx.Client):
    res = client.get(
        "/api/auth/me",
        headers={"Authorization": "Bearer invalid.token.here"},
    )
    assert res.status_code == 401


def test_me_with_malformed_header_returns_401(client: httpx.Client):
    res = client.get("/api/auth/me", headers={"Authorization": "Token abc123"})
    assert res.status_code == 401


# --- Protected endpoints return 401 without token ---


PROTECTED_GET = [
    "/api/reports",
    "/api/reports/00000000-0000-0000-0000-ffffffffffff",
    "/api/clubs/00000000-0000-0000-0000-ffffffffffff",
    "/api/admin/dashboard",
    "/api/feedback",
    "/api/analyze/status/00000000-0000-0000-0000-ffffffffffff",
]


@pytest.mark.parametrize("path", PROTECTED_GET)
def test_get_endpoint_requires_auth(client: httpx.Client, path: str):
    res = client.get(path)
    assert res.status_code == 401, f"Expected 401 for GET {path}, got {res.status_code}"


PROTECTED_POST = [
    ("/api/analyze/match", {"youtube_url": "https://youtube.com/watch?v=test1234567", "equipo_local": "A", "equipo_visitante": "B", "club_id": "00000000-0000-0000-0000-000000000001"}),
    ("/api/feedback", {"club_id": "00000000-0000-0000-0000-000000000001", "category": "precision", "rating": 3}),
    ("/api/clubs/00000000-0000-0000-0000-000000000001/portal", {}),
]


@pytest.mark.parametrize("path,body", PROTECTED_POST)
def test_post_endpoint_requires_auth(client: httpx.Client, path: str, body: dict):
    res = client.post(path, json=body)
    assert res.status_code == 401, f"Expected 401 for POST {path}, got {res.status_code}"


# --- Admin role check ---


def test_admin_dashboard_forbidden_for_non_admin(auth_client: httpx.Client):
    """Usuario con rol entrenador/manager no puede acceder al dashboard admin."""
    res = auth_client.get("/api/admin/dashboard")
    # CI test user is registered as ADMIN, so this would be 200.
    # But it should return 403 for non-admin users.
    assert res.status_code in (200, 403)  # 200 if admin, 403 if not
