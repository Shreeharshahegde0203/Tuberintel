#!/usr/bin/env python3
"""Measure whether point-in-time weather features improve the forecast.

This script never auto-promotes a weather model into runtime. It produces an
objective comparison so weather is only adopted after it demonstrably helps.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.services.forecasting.features import FeatureConfig  # noqa: E402
from app.services.forecasting.training import backtest_models  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=ROOT / "ml" / "artifacts" / "weather_feature_comparison.json")
    parser.add_argument("--folds", type=int, default=3)
    parser.add_argument("--validation-days", type=int, default=60)
    parser.add_argument("--min-train-days", type=int, default=180)
    args = parser.parse_args()
    frame = pd.read_csv(args.csv)
    needed = {"temperature_mean", "precipitation_mm", "relative_humidity_mean"}
    missing = needed - set(frame.columns)
    if missing:
        raise SystemExit(f"Weather comparison requires columns: {sorted(missing)}")

    base = backtest_models(
        frame,
        folds=args.folds,
        validation_days=args.validation_days,
        min_train_days=args.min_train_days,
        feature_config=FeatureConfig(include_weather=False),
        include_xgboost=False,
    )
    weather = backtest_models(
        frame,
        folds=args.folds,
        validation_days=args.validation_days,
        min_train_days=args.min_train_days,
        feature_config=FeatureConfig(include_weather=True),
        include_xgboost=False,
    )
    base_name = base.selection["champion"]
    weather_name = weather.selection["champion"]
    base_score = float(base.model_metrics[base_name]["weighted_mase"])
    weather_score = float(weather.model_metrics[weather_name]["weighted_mase"])
    improvement = (base_score - weather_score) / max(base_score, 1e-9) * 100
    payload = {
        "base": {"champion": base_name, "weighted_mase": base_score},
        "with_weather": {"champion": weather_name, "weighted_mase": weather_score},
        "relative_mase_improvement_percent": improvement,
        "recommendation": "retain_weather" if improvement >= 2.0 else "do_not_add_weather_complexity",
        "note": "Production promotion also requires point-in-time historical forecasts and future forecast availability for the serving path.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
