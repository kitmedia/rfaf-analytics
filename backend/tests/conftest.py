"""Pytest fixtures for RFAF Analytics tests."""

import pytest
import httpx

BASE_URL = "http://localhost:8000"

TEST_EMAIL = "ci_test_user@rfaf-test.es"
TEST_PASSWORD = "CItest_Pass9!"
TEST_CLUB_NAME = "CI Test Club"
TEST_USER_NAME = "CI Tester"


@pytest.fixture(scope="session")
def auth_data():
    """Register (or re-login) a test club+user. Returns full auth payload."""
    with httpx.Client(base_url=BASE_URL, timeout=15) as c:
        reg = c.post(
            "/api/auth/register",
            json={
                "club_name": TEST_CLUB_NAME,
                "email": TEST_EMAIL,
                "password": TEST_PASSWORD,
                "name": TEST_USER_NAME,
                "plan": "BASICO",
            },
        )
        if reg.status_code == 201:
            return reg.json()
        # Already registered — just login
        login = c.post(
            "/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD},
        )
        login.raise_for_status()
        return login.json()


@pytest.fixture(scope="session")
def club_id(auth_data) -> str:
    return auth_data["club_id"]


@pytest.fixture
def client():
    """Unauthenticated HTTP client (for 401 tests and public endpoints)."""
    with httpx.Client(base_url=BASE_URL, timeout=10) as c:
        yield c


@pytest.fixture
def auth_client(auth_data):
    """Authenticated HTTP client with Bearer token."""
    token = auth_data["access_token"]
    with httpx.Client(
        base_url=BASE_URL,
        timeout=10,
        headers={"Authorization": f"Bearer {token}"},
    ) as c:
        yield c
