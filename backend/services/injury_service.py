"""ACWR (Acute:Chronic Workload Ratio) injury risk model.

Calculates injury risk based on player physical data across matches.
Used by the PlayerPhysical model to set injury_risk_0_100 and status.
"""

import structlog

logger = structlog.get_logger()


def calculate_acwr(
    acute_load: float,
    chronic_load: float,
) -> float:
    """Calculate Acute:Chronic Workload Ratio.

    Args:
        acute_load: Last 7 days average workload (distance_m, sprint events, etc.)
        chronic_load: Last 28 days average workload

    Returns:
        ACWR ratio (ideal range: 0.8-1.3)
    """
    if chronic_load <= 0:
        return 0.0
    return round(acute_load / chronic_load, 2)


def injury_risk_from_acwr(acwr: float) -> int:
    """Convert ACWR to injury risk percentage (0-100).

    Based on sports science research:
    - ACWR 0.8-1.3: low risk (sweet spot)
    - ACWR < 0.8: moderate risk (undertraining → vulnerability)
    - ACWR 1.3-1.5: high risk (spike in load)
    - ACWR > 1.5: very high risk (dangerous spike)
    """
    if 0.8 <= acwr <= 1.3:
        # Sweet spot — low risk
        return max(5, int((abs(acwr - 1.05) / 0.25) * 20))
    elif acwr < 0.8:
        # Undertrained — moderate risk
        return int(30 + (0.8 - acwr) * 60)
    elif acwr <= 1.5:
        # High load spike — high risk
        return int(50 + (acwr - 1.3) * 150)
    else:
        # Dangerous spike
        return min(100, int(80 + (acwr - 1.5) * 40))


def classify_physical_status(injury_risk: int) -> str:
    """Classify player physical status from injury risk score.

    Returns one of: 'healthy', 'fatigue', 'risk', 'injured'.
    """
    if injury_risk <= 20:
        return "healthy"
    elif injury_risk <= 45:
        return "fatigue"
    elif injury_risk <= 75:
        return "risk"
    else:
        return "injured"


def assess_player_risk(
    recent_distances: list[float],
    window_acute: int = 7,
    window_chronic: int = 28,
) -> dict:
    """Full injury risk assessment for a player.

    Args:
        recent_distances: List of daily distances (meters), most recent first.
            Must have at least `window_chronic` entries for reliable results.
        window_acute: Days for acute window (default 7).
        window_chronic: Days for chronic window (default 28).

    Returns:
        Dict with keys: acwr, injury_risk_0_100, status.
    """
    if len(recent_distances) < window_acute:
        logger.warning(
            "injury_insufficient_data",
            data_points=len(recent_distances),
            required=window_acute,
        )
        return {"acwr": 0.0, "injury_risk_0_100": 0, "status": "healthy"}

    acute_load = sum(recent_distances[:window_acute]) / window_acute

    if len(recent_distances) >= window_chronic:
        chronic_load = sum(recent_distances[:window_chronic]) / window_chronic
    else:
        chronic_load = sum(recent_distances) / len(recent_distances)

    acwr = calculate_acwr(acute_load, chronic_load)
    risk = injury_risk_from_acwr(acwr)
    status = classify_physical_status(risk)

    logger.info(
        "injury_risk_assessed",
        acwr=acwr,
        risk=risk,
        status=status,
        acute_avg=round(acute_load, 0),
        chronic_avg=round(chronic_load, 0),
    )

    return {
        "acwr": acwr,
        "injury_risk_0_100": min(100, max(0, risk)),
        "status": status,
    }
