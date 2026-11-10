#!/usr/bin/env python3
"""End-to-end synthetic test: generate -> backtest -> train -> runtime forecast."""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "ml" / "scripts"))

from generate_dummy_market_data import generate  # noqa: E402
from app.services.forecasting.service import ForecastEngine  # noqa: E402
from app.services.forecasting.training import (  # noqa: E402
    evaluate_gru_challenger,
    evaluate_sarimax_challenger,
    train_and_save_artifact,
)


def main() -> None:
    frame = generate(days=760, seed=42)
    with tempfile.TemporaryDirectory() as directory:
        artifact_path = Path(directory) / "price_forecaster_v2.joblib"
        artifact = train_and_save_artifact(
            frame,
            artifact_path,
            folds=2,
            validation_days=45,
            min_train_days=180,
            include_xgboost=True,
        )
        sample_market = "Kolar APMC"
        market_frame = frame[frame.market.eq(sample_market)].copy()
        engine = ForecastEngine(artifact_path, min_history_days=90)
        result = engine.forecast(market_frame.to_dict("records"), 30)
        assert len(result.points) == 30
        assert all(point.predicted_price > 0 for point in result.points)
        assert all(point.lower_bound <= point.predicted_price <= point.upper_bound for point in result.points)
        assert result.points[-1].date > result.points[0].date
        report = {
            "champion": artifact["champion"],
            "champion_metrics": artifact["model_metrics"].get(artifact["champion"], {}),
            "runtime_model": result.model_name,
            "runtime_confidence": result.confidence,
            "forecast_day_1": result.points[0].as_dict(),
            "forecast_day_30": result.points[-1].as_dict(),
            "sarimax": evaluate_sarimax_challenger(frame, origins=1),
            "gru": evaluate_gru_challenger(frame, epochs=2),
        }
        print(json.dumps(report, indent=2, default=str))


if __name__ == "__main__":
    main()
