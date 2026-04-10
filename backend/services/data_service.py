"""StatsBomb data loading + xG model training."""

import os
import pickle
from pathlib import Path

import numpy as np
import pandas as pd
import structlog
from sklearn.metrics import brier_score_loss, roc_auc_score
from sklearn.model_selection import train_test_split
from xgboost import XGBClassifier

logger = structlog.get_logger()

DATA_DIR = Path(__file__).parent.parent / "data"
BENCHMARKS_DIR = DATA_DIR / "benchmarks"
ML_MODELS_DIR = Path(__file__).parent.parent / "ml_models"
XG_MODEL_PATH = ML_MODELS_DIR / "rfaf_xg_model.pkl"


def load_statsbomb_shots_for_xg_training() -> pd.DataFrame:
    """Load La Liga 2015/16 shots from StatsBomb Open Data for xG training."""
    from statsbombpy import sb

    BENCHMARKS_DIR.mkdir(parents=True, exist_ok=True)
    parquet_path = BENCHMARKS_DIR / "shots_xg_comp11_s4.parquet"

    if parquet_path.exists():
        logger.info("statsbomb_shots_cached", path=str(parquet_path))
        return pd.read_parquet(parquet_path)

    logger.info("statsbomb_loading_shots", competition_id=11, season_id=4)

    # La Liga 2015/16 = competition_id=11, season_id=4
    matches = sb.matches(competition_id=11, season_id=4)

    all_shots = []
    for _, match_row in matches.iterrows():
        try:
            events = sb.events(match_id=match_row["match_id"])
            shots = events[events["type"] == "Shot"].copy()
            if not shots.empty:
                all_shots.append(shots)
        except Exception:
            continue

    if not all_shots:
        raise RuntimeError("No se pudieron cargar tiros de StatsBomb")

    df = pd.concat(all_shots, ignore_index=True)

    # Extract features from shot location
    df["x"] = df["location"].apply(lambda loc: loc[0] if isinstance(loc, list) and len(loc) >= 2 else np.nan)
    df["y"] = df["location"].apply(lambda loc: loc[1] if isinstance(loc, list) and len(loc) >= 2 else np.nan)
    df["is_goal"] = (df["shot_outcome"] == "Goal").astype(int)

    # Distance and angle to goal (goal center at x=120, y=40)
    df["distance"] = np.sqrt((120 - df["x"]) ** 2 + (40 - df["y"]) ** 2)
    df["angle"] = np.abs(np.arctan2(40 - df["y"], 120 - df["x"]))

    # Shot body part encoding
    df["is_head"] = (df["shot_body_part"] == "Head").astype(int)
    df["is_right_foot"] = (df["shot_body_part"] == "Right Foot").astype(int)

    # Keep relevant columns
    cols = ["x", "y", "distance", "angle", "is_head", "is_right_foot", "is_goal"]
    df_clean = df[cols].dropna()

    df_clean.to_parquet(parquet_path, index=False)
    logger.info(
        "statsbomb_shots_saved",
        path=str(parquet_path),
        total_shots=len(df_clean),
        goals=int(df_clean["is_goal"].sum()),
    )
    return df_clean


def train_rfaf_xg_model() -> dict:
    """Train xG model with XGBoost on StatsBomb data.

    Returns dict with metrics: brier_score, auc.
    """
    ML_MODELS_DIR.mkdir(parents=True, exist_ok=True)

    df = load_statsbomb_shots_for_xg_training()

    features = ["x", "y", "distance", "angle", "is_head", "is_right_foot"]
    X = df[features]
    y = df["is_goal"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    model = XGBClassifier(
        n_estimators=200,
        max_depth=4,
        learning_rate=0.05,
        objective="binary:logistic",
        eval_metric="logloss",
        random_state=42,
        use_label_encoder=False,
    )
    model.fit(X_train, y_train)

    y_prob = model.predict_proba(X_test)[:, 1]
    brier = brier_score_loss(y_test, y_prob)
    auc = roc_auc_score(y_test, y_prob)

    with open(XG_MODEL_PATH, "wb") as f:
        pickle.dump(model, f)

    metrics = {"brier_score": round(brier, 4), "auc": round(auc, 4)}
    logger.info("xg_model_trained", **metrics, model_path=str(XG_MODEL_PATH))
    return metrics


def predict_xg(shots: list[dict]) -> list[dict]:
    """Predict xG for a list of shots from Gemini tactical data.

    Each shot dict should have: x, y, tipo (pie_derecho/pie_izquierdo/cabeza/otro).
    Returns the same list with 'xg_model' field added.
    """
    if not XG_MODEL_PATH.exists():
        logger.warn("xg_model_not_found", msg="Usando xG estimado de Gemini")
        return shots

    with open(XG_MODEL_PATH, "rb") as f:
        model = pickle.load(f)

    for shot in shots:
        x = shot.get("x")
        y = shot.get("y")
        if x is None or y is None:
            continue

        # Normalize from 0-100 to StatsBomb pitch (0-120, 0-80)
        sb_x = x * 120 / 100
        sb_y = y * 80 / 100

        distance = np.sqrt((120 - sb_x) ** 2 + (40 - sb_y) ** 2)
        angle = abs(np.arctan2(40 - sb_y, 120 - sb_x))
        is_head = 1 if shot.get("tipo") == "cabeza" else 0
        is_right_foot = 1 if shot.get("tipo") == "pie_derecho" else 0

        features = pd.DataFrame(
            [[sb_x, sb_y, distance, angle, is_head, is_right_foot]],
            columns=["x", "y", "distance", "angle", "is_head", "is_right_foot"],
        )
        shot["xg_model"] = round(float(model.predict_proba(features)[0][1]), 4)

    return shots
