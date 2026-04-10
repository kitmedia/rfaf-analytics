"""Load test with Locust — 20 concurrent users.

Run:
    locust -f backend/tests/locustfile.py --headless -u 20 -r 5 --run-time 5m \
        --host http://localhost:8000

Target:
    - < 5% error rate
    - P95 < 30s for cached analysis
    - Health endpoint P95 < 200ms
"""

import random
import uuid

from locust import HttpUser, between, task

CLUB_ID = "00000000-0000-0000-0000-000000000001"

# Pool of YouTube URLs for testing (vary to test caching)
YOUTUBE_URLS = [
    "https://www.youtube.com/watch?v=bnVZdRzVqIc",
    "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "https://www.youtube.com/watch?v=test1234567",
    "https://www.youtube.com/watch?v=test2345678",
    "https://www.youtube.com/watch?v=test3456789",
]

EQUIPOS_LOCAL = ["CD Ejea", "SD Huesca B", "CF Utebo", "UD Barbastro", "CD Cuarte"]
EQUIPOS_VISIT = ["SD Tarazona", "Deportivo Aragón", "CF Borja", "Cariñena CF", "Épila CF"]


class RFAFUser(HttpUser):
    """Simulates a club user interacting with the platform."""

    wait_time = between(2, 8)

    @task(10)
    def health_check(self):
        """Lightweight health check — most frequent."""
        self.client.get("/api/health")

    @task(5)
    def list_reports(self):
        """List reports for the club."""
        self.client.get(f"/api/reports?club_id={CLUB_ID}")

    @task(3)
    def get_club(self):
        """Get club info."""
        self.client.get(f"/api/clubs/{CLUB_ID}")

    @task(2)
    def analyze_match(self):
        """Submit a new analysis — triggers Celery pipeline."""
        url = random.choice(YOUTUBE_URLS)
        local = random.choice(EQUIPOS_LOCAL)
        visit = random.choice(EQUIPOS_VISIT)

        with self.client.post(
            "/api/analyze/match",
            json={
                "youtube_url": url,
                "equipo_local": local,
                "equipo_visitante": visit,
                "competicion": "Tercera RFEF Grupo XVII",
                "club_id": CLUB_ID,
            },
            catch_response=True,
        ) as response:
            if response.status_code == 429:
                # Plan limit reached — expected behavior, not an error
                response.success()
            elif response.status_code == 200:
                data = response.json()
                # Poll status once
                self.client.get(f"/api/analyze/status/{data['analysis_id']}")

    @task(1)
    def submit_feedback(self):
        """Submit feedback."""
        categories = ["usabilidad", "precision", "velocidad", "funcionalidad", "otro"]
        self.client.post(
            "/api/feedback",
            json={
                "club_id": CLUB_ID,
                "category": random.choice(categories),
                "rating": random.randint(3, 5),
                "comment": "Test feedback from load test",
            },
        )

    @task(1)
    def admin_dashboard(self):
        """Check admin dashboard."""
        self.client.get("/api/admin/dashboard")
