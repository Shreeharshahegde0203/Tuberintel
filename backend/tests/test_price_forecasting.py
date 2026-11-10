from __future__ import annotations

from pathlib import Path
import sys

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ml" / "scripts"))

from generate_dummy_market_data import generate  # noqa: E402
from app.services.forecasting.features import engineer_origin_features, feature_columns  # noqa: E402
from app.services.forecasting.service import ForecastEngine  # noqa: E402
from app.services.forecasting.training import train_and_save_artifact  # noqa: E402


def test_feature_engineering_does_not_read_future_prices() -> None:
    frame = generate(days=300, seed=7)
    market = "Kolar APMC"
    frame = frame[frame.market.eq(market)].copy()
    cutoff = pd.Timestamp("2023-08-15")

    base, _ = engineer_origin_features(frame)
    changed = frame.copy()
    dates = pd.to_datetime(changed["arrival_date"])
    changed.loc[dates > cutoff, ["modal_price", "min_price", "max_price"]] *= 4.0
    changed_features, _ = engineer_origin_features(changed)

    base_row = base[pd.to_datetime(base.arrival_date).eq(cutoff)].iloc[-1]
    changed_row = changed_features[pd.to_datetime(changed_features.arrival_date).eq(cutoff)].iloc[-1]
    comparable = [column for column in feature_columns(False) if column != "horizon_days"]
    assert np.allclose(
        base_row[comparable].to_numpy(dtype=float),
        changed_row[comparable].to_numpy(dtype=float),
        equal_nan=True,
    )


def test_validated_artifact_beats_naive_and_serves_30_days(tmp_path: Path) -> None:
    frame = generate(days=520, seed=42)
    artifact_path = tmp_path / "price_forecaster_v2.joblib"
    artifact = train_and_save_artifact(
        frame,
        artifact_path,
        folds=2,
        validation_days=35,
        min_train_days=180,
        include_xgboost=False,
    )
    champion = artifact["champion"]
    assert champion in {"lightgbm_direct", "persistence", "seasonal_naive_7", "seasonal_naive_28"}
    assert float(artifact["model_metrics"][champion]["weighted_mase"]) <= 1.0

    market_frame = frame[frame.market.eq("Kolar APMC")]
    result = ForecastEngine(artifact_path, min_history_days=90).forecast(market_frame.to_dict("records"), 30)
    assert len(result.points) == 30
    assert all(point.predicted_price > 0 for point in result.points)
    assert all(point.lower_bound <= point.predicted_price <= point.upper_bound for point in result.points)
    assert result.points[0].horizon_days == 1
    assert result.points[-1].horizon_days == 30
    assert result.points[-1].date > result.points[0].date


def test_runtime_uses_safe_fallback_without_artifact() -> None:
    frame = generate(days=140, seed=9)
    market_frame = frame[frame.market.eq("Kolar APMC")]
    result = ForecastEngine(None, min_history_days=90).forecast(market_frame.to_dict("records"), 14)
    assert result.fallback_used is True
    assert result.model_name == "robust_seasonal_trend"
    assert len(result.points) == 14
    assert all(point.predicted_price > 0 for point in result.points)
    first_width = result.points[0].upper_bound - result.points[0].lower_bound
    last_width = result.points[-1].upper_bound - result.points[-1].lower_bound
    assert last_width >= first_width


def test_numeric_horizon_is_capped_at_30_days() -> None:
    frame = generate(days=140, seed=11)
    engine = ForecastEngine(None, max_horizon_days=30)
    result = engine.forecast(frame[frame.market.eq("Kolar APMC")].to_dict("records"), 90)
    assert len(result.points) == 30
