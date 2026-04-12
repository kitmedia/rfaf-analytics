"""Pytest fixtures for RFAF Analytics tests."""

import pytest
import httpx

BASE_URL = "http://localhost:8000"
CLUB_ID = "00000000-0000-0000-0000-000000000001"


@pytest.fixture
def client():
    """Sync HTTP client testing against the running backend."""
    with httpx.Client(base_url=BASE_URL, timeout=10) as c:
        yield c
