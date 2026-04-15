"""Integration tests for Video Upload endpoint.

Requires: docker-compose up -d (backend running on localhost:8000)
Run: pytest backend/tests/test_upload.py -v
"""

import httpx
import io

CLUB_ID = "00000000-0000-0000-0000-000000000001"


def test_upload_rejects_invalid_format(client: httpx.Client):
    """Upload rechaza formato no soportado (422)."""
    fake_file = io.BytesIO(b"fake content")
    res = client.post(
        "/api/upload/video",
        files={"file": ("test.txt", fake_file, "text/plain")},
        data={
            "club_id": CLUB_ID,
            "equipo_local": "Local",
            "equipo_visitante": "Visitante",
        },
    )
    assert res.status_code == 422


def test_upload_rejects_invalid_club(client: httpx.Client):
    """Upload rechaza club inexistente (404)."""
    fake_file = io.BytesIO(b"fake mp4 content")
    res = client.post(
        "/api/upload/video",
        files={"file": ("test.mp4", fake_file, "video/mp4")},
        data={
            "club_id": "00000000-0000-0000-0000-ffffffffffff",
            "equipo_local": "Local",
            "equipo_visitante": "Visitante",
        },
    )
    assert res.status_code == 404


def test_upload_requires_teams(client: httpx.Client):
    """Upload requiere equipo_local y equipo_visitante."""
    fake_file = io.BytesIO(b"fake mp4 content")
    res = client.post(
        "/api/upload/video",
        files={"file": ("test.mp4", fake_file, "video/mp4")},
        data={"club_id": CLUB_ID},
    )
    assert res.status_code == 422
