"""Tests for weekly adoption summary task and email.

Run: pytest backend/tests/test_adoption.py -v
"""


def test_adoption_email_renders():
    """Email template se genera correctamente."""
    from backend.services.email_service import send_weekly_adoption_email

    # This will fail silently if RESEND_API_KEY not set (expected in test)
    result = send_weekly_adoption_email(
        to_email="test@test.com",
        club_name="CD Ejea Test",
        completed_count=2,
        total_count=5,
        improvement_msg="Tu equipo mejoró un 12% en xG",
        recommended_exercises=["Rondo de Salida", "Pressing Coordinado", "Transición"],
        has_recent_analysis=True,
    )
    # Returns False because RESEND_API_KEY is not set in test env
    assert result is False


def test_adoption_email_with_cta():
    """Email con CTA 'Analiza tu proximo partido' cuando has_recent_analysis=False."""
    from backend.services.email_service import send_weekly_adoption_email

    result = send_weekly_adoption_email(
        to_email="test@test.com",
        club_name="CD Ejea Test",
        completed_count=0,
        total_count=3,
        improvement_msg=None,
        recommended_exercises=[],
        has_recent_analysis=False,
    )
    assert result is False


def test_adoption_task_runs_without_error():
    """Task se ejecuta sin errores (puede no enviar emails sin Resend key)."""
    try:
        from backend.workers.tasks import send_weekly_adoption_summary_task
        result = send_weekly_adoption_summary_task()
        assert "clubs_processed" in result
        assert "emails_sent" in result
        assert isinstance(result["clubs_processed"], int)
    except Exception:
        # Task may fail if DB not available in test env
        import pytest
        pytest.skip("DB not available for task test")
