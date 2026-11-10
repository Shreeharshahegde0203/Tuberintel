#!/usr/bin/env python3
"""Train TuberIntel's leakage-safe direct multi-horizon price forecaster."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.services.forecasting.training import (  # noqa: E402
    evaluate_gru_challenger,
    evaluate_sarimax_challenger,
    train_and_save_artifact,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=ROOT / "ml" / "artifacts" / "price_forecaster_v2.joblib")
    parser.add_argument("--folds", type=int, default=3)
    parser.add_argument("--validation-days", type=int, default=60)
    parser.add_argument("--min-train-days", type=int, default=180)
    parser.add_argument("--interval-level", type=float, default=0.80)
    parser.add_argument("--skip-xgboost", action="store_true")
    parser.add_argument("--with-weather", action="store_true")
    parser.add_argument("--run-challengers", action="store_true")
    parser.add_argument("--database-url", help="Optional DB URL used only to register the validated model version")
    args = parser.parse_args()

    frame = pd.read_csv(args.csv)
    source_text = " ".join(frame.get("source", pd.Series(dtype=str)).dropna().astype(str).unique()).lower()
    if "synthetic_test_only" not in source_text and ("demo" in source_text or "seed" in source_text):
        raise SystemExit("Refusing to train a production artifact from demo/seed market rows. Export real rows first.")

    artifact = train_and_save_artifact(
        frame,
        args.output,
        folds=args.folds,
        validation_days=args.validation_days,
        min_train_days=args.min_train_days,
        include_xgboost=not args.skip_xgboost,
        include_weather=args.with_weather,
        interval_level=args.interval_level,
    )
    report = {
        "champion": artifact["champion"],
        "model_version": artifact["model_version"],
        "selection": artifact["selection"],
        "model_metrics": artifact["model_metrics"],
    }
    if args.run_challengers:
        report["sarimax_challenger"] = evaluate_sarimax_challenger(frame)
        report["gru_challenger"] = evaluate_gru_challenger(frame)
    print(json.dumps(report, indent=2, default=str))
    print(f"Saved validated artifact: {args.output}")

    if args.database_url:
        from sqlalchemy import create_engine
        from sqlalchemy.orm import Session
        from app.services.forecasting.persistence import register_model_version

        database_url = args.database_url.replace("postgresql://", "postgresql+psycopg://", 1)
        engine = create_engine(database_url, future=True)
        with Session(engine) as db:
            register_model_version(
                db, artifact=artifact, artifact_path=args.output, training_frame=frame, activate=True
            )
        print("Registered model version in database")


if __name__ == "__main__":
    main()
