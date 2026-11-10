from __future__ import annotations

from datetime import timedelta
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd

from app.services.forecasting.artifact import load_artifact
from app.services.forecasting.baselines import future_dates, robust_seasonal_trend, seasonal_naive
from app.services.forecasting.contracts import ForecastPointResult, ForecastResult
from app.services.forecasting.features import FeatureConfig, feature_columns, latest_origin_rows
from app.services.forecasting.intervals import symmetric_bounds


class ForecastEngine:
    """Runtime forecasting engine with a validated-artifact path and safe fallback."""

    def __init__(
        self,
        artifact_path: str | Path | None = None,
        *,
        max_horizon_days: int = 30,
        min_history_days: int = 90,
        interval_level: float = 0.80,
    ) -> None:
        self.artifact_path = Path(artifact_path) if artifact_path else None
        self.max_horizon_days = min(max(int(max_horizon_days), 1), 30)
        self.min_history_days = max(int(min_history_days), 30)
        self.interval_level = float(np.clip(interval_level, 0.5, 0.99))

    @staticmethod
    def records_to_frame(records: Iterable[Any]) -> pd.DataFrame:
        rows: list[dict[str, Any]] = []
        for item in records:
            if isinstance(item, dict):
                getter = item.get
            else:
                getter = lambda key, default=None, obj=item: getattr(obj, key, default)
            rows.append(
                {
                    "state": getter("state", "Unknown"),
                    "district": getter("district", "Unknown"),
                    "market": getter("market", "Unknown"),
                    "commodity": getter("commodity", "Potato"),
                    "variety": getter("variety", "Local"),
                    "grade": getter("grade", "FAQ"),
                    "arrival_date": getter("arrival_date"),
                    "min_price": getter("min_price"),
                    "max_price": getter("max_price"),
                    "modal_price": getter("modal_price"),
                    "source": getter("source", "unknown"),
                }
            )
        return pd.DataFrame(rows)

    @staticmethod
    def _confidence(history_points: int, model_name: str, metrics: dict[str, Any] | None = None) -> str:
        if history_points < 60:
            return "low"
        mase_value = None
        if metrics:
            try:
                mase_value = float(metrics.get("weighted_mase"))
            except (TypeError, ValueError):
                mase_value = None
        if history_points >= 365 and model_name not in {"robust_seasonal_trend", "persistence"} and (mase_value is None or mase_value < 0.95):
            return "high"
        if history_points >= 120:
            return "medium"
        return "low"

    def _artifact_forecast(self, frame: pd.DataFrame, horizon_days: int, artifact: dict[str, Any]) -> ForecastResult | None:
        champion = str(artifact.get("champion", ""))
        if champion in {"persistence", "seasonal_naive_7", "seasonal_naive_28", "robust_seasonal_trend"}:
            return None
        model = (artifact.get("models") or {}).get(champion)
        if model is None:
            return None
        include_weather = bool(artifact.get("feature_config", {}).get("include_weather", False))
        if include_weather:
            # Runtime historical DB rows currently do not carry point-in-time weather
            # forecasts. Do not silently substitute future actual weather.
            return None
        maps = artifact.get("category_maps") or {}
        config = FeatureConfig(
            max_ffill_days=int(artifact.get("feature_config", {}).get("max_ffill_days", 3)),
            include_weather=False,
        )
        horizons = list(range(1, horizon_days + 1))
        latest = latest_origin_rows(frame, horizons=horizons, category_maps=maps, config=config)
        if latest.empty:
            return None
        columns = artifact.get("feature_columns") or feature_columns(False)
        if any(column not in latest.columns for column in columns):
            return None

        # A market-specific forecast should resolve to one current identity. If
        # multiple identities remain (state-level overview), the trained market
        # model is not used; the caller gets an auditable aggregate fallback.
        identity_count = latest[["state", "district", "market", "variety", "grade"]].drop_duplicates().shape[0]
        if identity_count != 1:
            return None

        prediction_return = np.asarray(model.predict(latest[columns]), dtype=float)
        current_price = latest["modal_price"].to_numpy(dtype=float)
        prices = np.maximum(current_price * np.exp(prediction_return), 0.0)
        last_date = pd.to_datetime(latest["arrival_date"].iloc[0]).date()
        calibration = artifact.get("calibration", {}).get(champion, {})
        base_error = float(artifact.get("fallback_error", max(float(current_price[0]) * 0.05, 50.0)))
        confidence = self._confidence(
            int(artifact.get("training_points", len(frame))),
            champion,
            (artifact.get("model_metrics") or {}).get(champion),
        )
        points: list[ForecastPointResult] = []
        for horizon, predicted in zip(horizons, prices, strict=False):
            lower, upper = symmetric_bounds(
                float(predicted),
                horizon_days=horizon,
                base_error=base_error,
                calibration=calibration,
            )
            points.append(
                ForecastPointResult(
                    date=last_date + timedelta(days=horizon),
                    predicted_price=round(float(predicted), 2),
                    lower_bound=round(lower, 2),
                    upper_bound=round(upper, 2),
                    horizon_days=horizon,
                    model_name=champion,
                    confidence=confidence,
                    interval_level=self.interval_level,
                )
            )
        normalized_dates = pd.to_datetime(frame["arrival_date"], errors="coerce").dropna()
        return ForecastResult(
            points=points,
            model_name=champion,
            model_version=str(artifact.get("model_version", "v2")),
            confidence=confidence,
            training_points=int(artifact.get("training_points", len(frame))),
            fallback_used=False,
            data_start=normalized_dates.min().date() if len(normalized_dates) else None,
            data_end=normalized_dates.max().date() if len(normalized_dates) else None,
            methodology=[
                "Direct multi-horizon forecast: each future horizon is estimated from information available at the forecast origin.",
                "Champion model was selected by chronological expanding-window backtesting against naive baselines.",
                f"{int(self.interval_level * 100)}% uncertainty bounds are calibrated from out-of-sample residuals.",
            ],
            diagnostics={
                "artifact_path": str(self.artifact_path) if self.artifact_path else None,
                "selection": artifact.get("selection", {}),
                "champion_metrics": (artifact.get("model_metrics") or {}).get(champion, {}),
            },
        )

    def _fallback_forecast(self, frame: pd.DataFrame, horizon_days: int) -> ForecastResult:
        baseline = robust_seasonal_trend(frame, horizon_days)
        dates = future_dates(frame, horizon_days)
        if not len(baseline.prices) or not dates:
            return ForecastResult([], "unavailable", "v2", "low", 0, True)
        history_points = int(frame["arrival_date"].nunique())
        confidence = self._confidence(history_points, baseline.name)
        points: list[ForecastPointResult] = []
        for horizon, (target_date, predicted) in enumerate(zip(dates, baseline.prices, strict=False), start=1):
            lower, upper = symmetric_bounds(
                float(predicted),
                horizon_days=horizon,
                base_error=baseline.residual_scale,
            )
            points.append(
                ForecastPointResult(
                    date=target_date,
                    predicted_price=round(float(predicted), 2),
                    lower_bound=round(lower, 2),
                    upper_bound=round(upper, 2),
                    horizon_days=horizon,
                    model_name=baseline.name,
                    confidence=confidence,
                    interval_level=self.interval_level,
                )
            )
        normalized_dates = pd.to_datetime(frame["arrival_date"], errors="coerce").dropna()
        return ForecastResult(
            points=points,
            model_name=baseline.name,
            model_version="fallback-v2",
            confidence=confidence,
            training_points=history_points,
            fallback_used=True,
            data_start=normalized_dates.min().date() if len(normalized_dates) else None,
            data_end=normalized_dates.max().date() if len(normalized_dates) else None,
            methodology=[
                "No validated champion artifact was available for this exact forecast context.",
                "Fallback combines robust recent trend, 7-day seasonality, 28-day seasonality and persistence without using future observations.",
                f"{int(self.interval_level * 100)}% bounds widen with horizon using empirical historical forecast errors.",
            ],
            diagnostics={"residual_scale": round(float(baseline.residual_scale), 2)},
        )

    def forecast(self, records: Iterable[Any], horizon_days: int = 30) -> ForecastResult:
        horizon_days = min(max(int(horizon_days), 1), self.max_horizon_days)
        frame = self.records_to_frame(records)
        if frame.empty:
            return ForecastResult([], "unavailable", "v2", "low", 0, True)
        history_points = frame["arrival_date"].nunique()
        artifact = None
        if self.artifact_path and history_points >= self.min_history_days:
            try:
                artifact = load_artifact(str(self.artifact_path.resolve()))
            except Exception:
                artifact = None
        if artifact:
            try:
                result = self._artifact_forecast(frame, horizon_days, artifact)
                if result and result.points:
                    return result
            except Exception:
                # Prediction failure must never take down the market dashboard;
                # transparent fallback remains available.
                pass
        # TUBERINTEL WEB FORECAST DATES V1
        from datetime import datetime, timezone
        today = datetime.now(timezone(timedelta(hours=5, minutes=30))).date()
        normalized = pd.to_datetime(frame["arrival_date"], errors="coerce").dropna()
        end = normalized.max().date() if len(normalized) else today
        gap = max(0, (today - end).days)
        if gap > 14:
            return ForecastResult([], "unavailable_stale_history", "web-v1", "low", int(history_points), True,
                data_end=end, methodology=["Latest observation is over 14 days old; refresh prices before forecasting."])
        result = self._fallback_forecast(frame, horizon_days + gap)
        result.points = result.points[gap:gap + horizon_days]
        for index, point in enumerate(result.points, 1):
            point.horizon_days = index
        result.diagnostics["reporting_gap_days"] = gap
        result.methodology.append(f"Reporting gap: {gap} days; projections advance through that gap before tomorrow's forecast.")
        if history_points < 60:
            result.methodology = [item for item in result.methodology if "bounds widen" not in item]
            result.methodology.append("Short history: fallback only, low confidence. Bounds are heuristic and are not validated coverage intervals.")
        return result
