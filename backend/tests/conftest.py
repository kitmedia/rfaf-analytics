"""Pytest fixtures for RFAF Analytics tests."""

import os

import pytest
import httpx

BASE_URL = "http://localhost:8000"
CLUB_ID = "00000000-0000-0000-0000-000000000001"

# Admin credentials for testing (set via env or defaults for local dev)
ADMIN_EMAIL = os.getenv("TEST_ADMIN_EMAIL", "admin@rfaf.es")
ADMIN_PASSWORD = os.getenv("TEST_ADMIN_PASSWORD", "admin1234")


@pytest.fixture
def client():
    """Sync HTTP client testing against the running backend."""
    with httpx.Client(base_url=BASE_URL, timeout=10) as c:
        yield c


@pytest.fixture
def admin_token(client: httpx.Client) -> str:
    """Obtener JWT token de admin para tests protegidos."""
    res = client.post(
        "/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
    )
    if res.status_code != 200:
        pytest.skip(f"No se pudo obtener token admin (status {res.status_code}). Configura TEST_ADMIN_EMAIL/TEST_ADMIN_PASSWORD.")
    return res.json()["access_token"]


@pytest.fixture
def admin_client(client: httpx.Client, admin_token: str) -> httpx.Client:
    """HTTP client con JWT admin header inyectado."""
    client.headers["Authorization"] = f"Bearer {admin_token}"
    return client
