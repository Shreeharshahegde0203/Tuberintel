#!/usr/bin/env python3
"""Train an auditable mandi-price forecaster using lag and calendar features.

Input CSV requires arrival_date and modal_price. Optional market/state filters are
handled before running this script. Dates may be ISO or DD/MM/YYYY.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error

FEATURES = [
    "lag_1", "lag_2", "lag_3", "lag_7", "lag_14", "lag_28",
    "rolling_mean_3", "rolling_mean_7", "rolling_mean_14", "rolling_std_7",
    "day_of_week", "day_of_month", "month", "week_of_year", "trend_index",
]


def prepare(frame: pd.DataFrame) -> pd.DataFrame:
    if not {"arrival_date", "modal_price"}.issubset(frame.columns):
        raise ValueError("CSV must include arrival_date and modal_price columns.")
    frame = frame.copy()
    frame["arrival_date"] = pd.to_datetime(frame["arrival_date"], dayfirst=True, errors="coerce")
    frame["modal_price"] = pd.to_numeric(frame["modal_price"], errors="coerce")
    frame = frame.dropna(subset=["arrival_date", "modal_price"])
    frame = frame.groupby("arrival_date", as_index=False)["modal_price"].median().sort_values("arrival_date")
    full_index = pd.date_range(frame.arrival_date.min(), frame.arrival_date.max(), freq="D")
    frame = frame.set_index("arrival_date").reindex(full_index)
    frame.index.name = "arrival_date"
    frame["modal_price"] = frame["modal_price"].interpolate(limit_direction="both")
    for lag in [1, 2, 3, 7, 14, 28]:
        frame[f"lag_{lag}"] = frame["modal_price"].shift(lag)
    for window in [3, 7, 14]:
        frame[f"rolling_mean_{window}"] = frame["modal_price"].shift(1).rolling(window).mean()
    frame["rolling_std_7"] = frame["modal_price"].shift(1).rolling(7).std()
    frame["day_of_week"] = frame.index.dayofweek
    frame["day_of_month"] = frame.index.day
    frame["month"] = frame.index.month
    frame["week_of_year"] = frame.index.isocalendar().week.astype(int)
    frame["trend_index"] = np.arange(len(frame))
    return frame.dropna().reset_index()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("ml/artifacts/price_forecaster.joblib"))
    parser.add_argument("--test-days", type=int, default=30)
    args = parser.parse_args()

    data = prepare(pd.read_csv(args.csv))
    if len(data) < max(90, args.test_days * 2):
        raise ValueError("At least 90 daily observations are recommended after cleaning.")
    split = len(data) - args.test_days
    train, test = data.iloc[:split], data.iloc[split:]

    model = lgb.LGBMRegressor(
        objective="regression_l1",
        n_estimators=700,
        learning_rate=0.025,
        num_leaves=24,
        max_depth=7,
        min_child_samples=18,
        subsample=0.85,
        colsample_bytree=0.85,
        reg_alpha=0.15,
        reg_lambda=0.25,
        random_state=42,
        verbosity=-1,
    )
    model.fit(train[FEATURES], train["modal_price"])
    prediction = model.predict(test[FEATURES])
    mae = float(mean_absolute_error(test["modal_price"], prediction))
    rmse = float(np.sqrt(mean_squared_error(test["modal_price"], prediction)))
    mape = float(np.mean(np.abs((test["modal_price"].to_numpy() - prediction) / np.maximum(test["modal_price"].to_numpy(), 1))) * 100)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"model": model, "features": FEATURES, "last_frame": data.tail(35)}, args.output)
    args.output.with_suffix(".metrics.json").write_text(json.dumps({
        "mae": mae,
        "rmse": rmse,
        "mape_percent": mape,
        "train_rows": len(train),
        "test_rows": len(test),
        "test_start": test.arrival_date.min().isoformat(),
        "test_end": test.arrival_date.max().isoformat(),
        "feature_importance": dict(sorted(zip(FEATURES, model.feature_importances_.tolist()), key=lambda x: x[1], reverse=True)),
    }, indent=2), encoding="utf-8")
    print(f"MAE={mae:.2f} RMSE={rmse:.2f} MAPE={mape:.2f}%")
    print(f"Saved: {args.output}")


if __name__ == "__main__":
    main()
