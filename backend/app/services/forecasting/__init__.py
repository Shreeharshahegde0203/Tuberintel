"""Leakage-safe potato price forecasting for TuberIntel.

Runtime code deliberately has a deterministic statistical fallback so the API
continues to work when no trained artifact is present.  Offline training and
back-testing live in :mod:`ml.scripts` and can promote a validated challenger
artifact without changing the public API contract.
"""

from app.services.forecasting.service import ForecastEngine, ForecastResult

__all__ = ["ForecastEngine", "ForecastResult"]
