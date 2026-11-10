from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

import numpy as np
import pandas as pd
from sklearn.linear_model import HuberRegressor

from app.services.forecasting.features import parse_market_dates


@dataclass(slots=True)
class BaselinePrediction:
    prices: np.ndarray
    residual_scale: float
    name: str


def _series(frame: pd.DataFrame) -> pd.Series:
    data = frame[["arrival_date", "modal_price"]].copy()
    data["arrival_date"] = parse_market_dates(data["arrival_date"])
    data["modal_price"] = pd.to_numeric(data["modal_price"], errors="coerce")
    data = data.dropna().groupby("arrival_date")["modal_price"].median().sort_index()
    if data.empty:
        return data
    full = pd.date_range(data.index.min(), data.index.max(), freq="D")
    return data.reindex(full).ffill(limit=3).dropna()


def persistence(frame: pd.DataFrame, horizon_days: int) -> BaselinePrediction:
    series = _series(frame)
    if series.empty:
        return BaselinePrediction(np.array([]), 0.0, "persistence")
    last = float(series.iloc[-1])
    residuals = (series - series.shift(1)).dropna().to_numpy(dtype=float)
    scale = float(np.quantile(np.abs(residuals), 0.80)) if len(residuals) else max(last * 0.05, 50.0)
    return BaselinePrediction(np.repeat(last, horizon_days), max(scale, 20.0), "persistence")


def seasonal_naive(frame: pd.DataFrame, horizon_days: int, period: int = 7) -> BaselinePrediction:
    series = _series(frame)
    if series.empty:
        return BaselinePrediction(np.array([]), 0.0, f"seasonal_naive_{period}")
    values = series.to_numpy(dtype=float)
    predicted = []
    for step in range(1, horizon_days + 1):
        index = len(values) - period + ((step - 1) % period)
        predicted.append(float(values[index]) if index >= 0 else float(values[-1]))
    residuals = (series - series.shift(period)).dropna().to_numpy(dtype=float)
    scale = float(np.quantile(np.abs(residuals), 0.80)) if len(residuals) else max(float(series.iloc[-1]) * 0.06, 60.0)
    return BaselinePrediction(np.asarray(predicted), max(scale, 20.0), f"seasonal_naive_{period}")


def robust_seasonal_trend(frame: pd.DataFrame, horizon_days: int) -> BaselinePrediction:
    """Auditable fallback used when no trained champion artifact is available.

    It combines robust recent trend, 7-day seasonality, 28-day seasonality and
    persistence.  Every component only uses observations at or before the
    forecast origin.
    """
    series = _series(frame)
    if series.empty:
        return BaselinePrediction(np.array([]), 0.0, "robust_seasonal_trend")
    values = series.to_numpy(dtype=float)
    last = float(values[-1])
    window = min(len(values), 90)
    recent = values[-window:]
    x = np.arange(window, dtype=float).reshape(-1, 1)
    if window >= 14:
        model = HuberRegressor(epsilon=1.35, alpha=0.1, max_iter=500)
        model.fit(x, recent)
        slope = float(model.coef_[0])
    else:
        slope = 0.0
    # Prevent a short shock from being extrapolated into an absurd month-long move.
    max_daily_slope = max(last * 0.015, 10.0)
    slope = float(np.clip(slope, -max_daily_slope, max_daily_slope))

    p7 = seasonal_naive(frame, horizon_days, 7).prices
    p28 = seasonal_naive(frame, horizon_days, 28).prices
    trend = np.asarray([last + slope * step for step in range(1, horizon_days + 1)], dtype=float)
    persist = np.repeat(last, horizon_days)

    if len(values) >= 56:
        weights = np.array([0.28, 0.30, 0.22, 0.20])
    elif len(values) >= 21:
        weights = np.array([0.30, 0.38, 0.08, 0.24])
    else:
        weights = np.array([0.15, 0.25, 0.00, 0.60])
    stacked = np.vstack([trend, p7, p28, persist])
    predicted = np.average(stacked, axis=0, weights=weights)

    # Empirical one-step fallback residuals for uncertainty calibration.
    residuals: list[float] = []
    min_history = 35
    for end in range(min_history, len(series)):
        hist = pd.DataFrame({"arrival_date": series.index[:end], "modal_price": series.iloc[:end].to_numpy()})
        one = seasonal_naive(hist, 1, 7).prices
        if len(one):
            residuals.append(float(series.iloc[end] - one[0]))
    scale = float(np.quantile(np.abs(residuals), 0.80)) if residuals else max(last * 0.05, 50.0)
    return BaselinePrediction(np.maximum(predicted, 0.0), max(scale, 20.0), "robust_seasonal_trend")


def future_dates(frame: pd.DataFrame, horizon_days: int) -> list[date]:
    series = _series(frame)
    if series.empty:
        return []
    last_date = series.index[-1].date()
    return [last_date + timedelta(days=step) for step in range(1, horizon_days + 1)]
