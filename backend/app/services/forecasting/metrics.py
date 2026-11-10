from __future__ import annotations

from typing import Iterable

import numpy as np


def _arrays(actual: Iterable[float], predicted: Iterable[float]) -> tuple[np.ndarray, np.ndarray]:
    y = np.asarray(list(actual), dtype=float)
    p = np.asarray(list(predicted), dtype=float)
    mask = np.isfinite(y) & np.isfinite(p)
    return y[mask], p[mask]


def mae(actual: Iterable[float], predicted: Iterable[float]) -> float:
    y, p = _arrays(actual, predicted)
    return float(np.mean(np.abs(y - p))) if len(y) else float("nan")


def rmse(actual: Iterable[float], predicted: Iterable[float]) -> float:
    y, p = _arrays(actual, predicted)
    return float(np.sqrt(np.mean((y - p) ** 2))) if len(y) else float("nan")


def smape(actual: Iterable[float], predicted: Iterable[float]) -> float:
    y, p = _arrays(actual, predicted)
    if not len(y):
        return float("nan")
    denom = np.maximum(np.abs(y) + np.abs(p), 1e-9)
    return float(np.mean(200.0 * np.abs(y - p) / denom))


def mase(actual: Iterable[float], predicted: Iterable[float], scale: float) -> float:
    value = mae(actual, predicted)
    return float(value / max(float(scale), 1e-9))


def directional_accuracy(origin: Iterable[float], actual: Iterable[float], predicted: Iterable[float]) -> float:
    o = np.asarray(list(origin), dtype=float)
    y = np.asarray(list(actual), dtype=float)
    p = np.asarray(list(predicted), dtype=float)
    mask = np.isfinite(o) & np.isfinite(y) & np.isfinite(p)
    if not np.any(mask):
        return float("nan")
    actual_direction = np.sign(y[mask] - o[mask])
    predicted_direction = np.sign(p[mask] - o[mask])
    return float(np.mean(actual_direction == predicted_direction) * 100.0)


def within_percent(actual: Iterable[float], predicted: Iterable[float], tolerance_percent: float) -> float:
    y, p = _arrays(actual, predicted)
    if not len(y):
        return float("nan")
    error = np.abs(y - p) / np.maximum(np.abs(y), 1.0) * 100.0
    return float(np.mean(error <= tolerance_percent) * 100.0)


def interval_coverage(actual: Iterable[float], lower: Iterable[float], upper: Iterable[float]) -> float:
    y = np.asarray(list(actual), dtype=float)
    lo = np.asarray(list(lower), dtype=float)
    hi = np.asarray(list(upper), dtype=float)
    mask = np.isfinite(y) & np.isfinite(lo) & np.isfinite(hi)
    if not np.any(mask):
        return float("nan")
    return float(np.mean((y[mask] >= lo[mask]) & (y[mask] <= hi[mask])) * 100.0)


def summarize_metrics(
    *,
    actual: Iterable[float],
    predicted: Iterable[float],
    origin: Iterable[float],
    naive_scale: float,
) -> dict[str, float]:
    return {
        "mae": mae(actual, predicted),
        "rmse": rmse(actual, predicted),
        "smape_percent": smape(actual, predicted),
        "mase": mase(actual, predicted, naive_scale),
        "directional_accuracy_percent": directional_accuracy(origin, actual, predicted),
        "within_5_percent": within_percent(actual, predicted, 5.0),
        "within_10_percent": within_percent(actual, predicted, 10.0),
    }
