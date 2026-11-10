from __future__ import annotations

from collections.abc import Mapping

import numpy as np


def interpolate_error_quantile(calibration: Mapping[int | str, float], horizon: int, default: float) -> float:
    if not calibration:
        return default
    parsed = sorted((int(key), float(value)) for key, value in calibration.items() if float(value) >= 0)
    if not parsed:
        return default
    horizons = np.asarray([item[0] for item in parsed], dtype=float)
    values = np.asarray([item[1] for item in parsed], dtype=float)
    return float(np.interp(float(horizon), horizons, values, left=values[0], right=values[-1]))


def symmetric_bounds(
    predicted_price: float,
    *,
    horizon_days: int,
    base_error: float,
    calibration: Mapping[int | str, float] | None = None,
) -> tuple[float, float]:
    calibrated = interpolate_error_quantile(calibration or {}, horizon_days, base_error)
    # Beyond calibration anchors, uncertainty may not shrink. The sqrt term is
    # deliberately mild because the empirical quantile already captures most of it.
    width = max(20.0, calibrated) * max(1.0, np.sqrt(horizon_days / 7.0) * 0.72)
    return float(max(0.0, predicted_price - width)), float(max(0.0, predicted_price + width))
