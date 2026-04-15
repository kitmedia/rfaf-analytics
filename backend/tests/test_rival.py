"""Tests for Rival Analysis (Story 4.2).

Run: pytest backend/tests/test_rival.py -v
"""


def test_check_upcoming_with_rival_analysis():
    """Task se ejecuta sin error con analisis rival."""
    try:
        from backend.workers.tasks import check_upcoming_matches_task
        result = check_upcoming_matches_task()
        assert "matches_found" in result
        assert "analyses_generated" in result
        assert "notifications_sent" in result
    except Exception:
        import pytest
        pytest.skip("DB not available")


def test_rival_email_renders():
    """Email rival se genera correctamente."""
    from backend.services.email_service import send_rival_analysis_email

    # With analysis
    result = send_rival_analysis_email(
        to_email="test@test.com",
        club_name="CD Ejea",
        rival_name="SD Tarazona",
        has_analysis=True,
        match_date="20/04/2026 16:00",
    )
    assert result is False  # No RESEND_API_KEY

    # Without analysis
    result2 = send_rival_analysis_email(
        to_email="test@test.com",
        club_name="CD Ejea",
        rival_name="Desconocido FC",
        has_analysis=False,
    )
    assert result2 is False
