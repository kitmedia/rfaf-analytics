"""Tests for pipeline fallback logic.

Run: pytest backend/tests/test_fallback.py -v
"""


def test_run_with_fallback_primary_success():
    """Primary succeeds — no fallback called."""
    from backend.workers.tasks import _run_with_fallback

    result, model = _run_with_fallback(
        "extraction",
        lambda: {"data": "ok"},
        lambda: {"data": "fallback"},
        {},
    )
    assert result == {"data": "ok"}
    assert model == "gemini-2.5-flash"


def test_run_with_fallback_primary_fails():
    """Primary fails — fallback called."""
    from backend.workers.tasks import _run_with_fallback

    def failing_primary():
        raise ConnectionError("API down")

    result, model = _run_with_fallback(
        "narrative",
        failing_primary,
        lambda: ("fallback content", 0.05),
        {},
    )
    assert result == ("fallback content", 0.05)
    assert model == "claude-haiku-4-5-20251001"


def test_run_with_fallback_both_fail():
    """Both primary and fallback fail — returns None."""
    from backend.workers.tasks import _run_with_fallback

    def failing():
        raise ConnectionError("down")

    result, model = _run_with_fallback(
        "extraction",
        failing,
        failing,
        {},
    )
    assert result is None
    assert model is None


def test_run_with_fallback_no_fallback_fn():
    """No fallback function provided — returns None on primary failure."""
    from backend.workers.tasks import _run_with_fallback

    result, model = _run_with_fallback(
        "extraction",
        lambda: (_ for _ in ()).throw(ConnectionError("down")),
        None,
        {},
    )
    assert result is None
    assert model is None
