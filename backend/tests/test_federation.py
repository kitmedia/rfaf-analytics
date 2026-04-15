"""Tests for Federation dashboard.
Run: pytest backend/tests/test_federation.py -v
"""
import httpx

def test_federation_dashboard(client: httpx.Client):
    res = client.get("/api/federation/dashboard")
    assert res.status_code == 200
    data = res.json()
    assert "total_clubs" in data
    assert "analyses_total" in data
    assert isinstance(data["total_clubs"], int)
