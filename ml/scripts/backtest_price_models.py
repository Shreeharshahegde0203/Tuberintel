#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.services.forecasting.features import FeatureConfig  # noqa: E402
from app.services.forecasting.training import (  # noqa: E402
    backtest_models,
    evaluate_gru_challenger,
    evaluate_sarimax_challenger,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=ROOT / "ml" / "artifacts" / "price_backtest.json")
    parser.add_argument("--folds", type=int, default=3)
    parser.add_argument("--validation-days", type=int, default=60)
    parser.add_argument("--min-train-days", type=int, default=180)
    parser.add_argument("--with-weather", action="store_true")
    parser.add_argument("--skip-xgboost", action="store_true")
    parser.add_argument("--neural", action="store_true")
    parser.add_argument("--sarimax", action="store_true")
    args = parser.parse_args()
    frame = pd.read_csv(args.csv)
    result = backtest_models(
        frame,
        folds=args.folds,
        validation_days=args.validation_days,
        min_train_days=args.min_train_days,
        feature_config=FeatureConfig(include_weather=args.with_weather),
        include_xgboost=not args.skip_xgboost,
    )
    payload = {
        "selection": result.selection,
        "model_metrics": result.model_metrics,
        "training_points": result.training_points,
    }
    if args.sarimax:
        payload["sarimax_challenger"] = evaluate_sarimax_challenger(frame)
    if args.neural:
        payload["gru_challenger"] = evaluate_gru_challenger(frame)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    print(json.dumps(payload, indent=2, default=str))


if __name__ == "__main__":
    main()
