#!/usr/bin/env python3
"""Train the xG model from StatsBomb open data.

Usage:
    python -m backend.scripts.train_xg_model

Run this once before first deploy, or whenever you want to retrain.
The model is saved to backend/ml_models/rfaf_xg_model.pkl.
"""

import sys
from pathlib import Path

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.services.data_service import train_rfaf_xg_model, XG_MODEL_PATH


def main():
    if XG_MODEL_PATH.exists():
        print(f"Model already exists at {XG_MODEL_PATH}")
        resp = input("Retrain? [y/N] ").strip().lower()
        if resp != "y":
            print("Skipped.")
            return

    print("Training xG model from StatsBomb La Liga 2015/16 data...")
    print("This may take 1-2 minutes on first run (downloading data).")
    metrics = train_rfaf_xg_model()
    print(f"Done! Brier score: {metrics['brier_score']}, AUC: {metrics['auc']}")
    print(f"Model saved to: {XG_MODEL_PATH}")


if __name__ == "__main__":
    main()
