from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date
from typing import Any


@dataclass(slots=True)
class ForecastPointResult:
    date: date
    predicted_price: float
    lower_bound: float
    upper_bound: float
    horizon_days: int
    model_name: str
    confidence: str
    interval_level: float = 0.80

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ForecastResult:
    points: list[ForecastPointResult]
    model_name: str
    model_version: str
    confidence: str
    training_points: int
    fallback_used: bool
    data_start: date | None = None
    data_end: date | None = None
    methodology: list[str] = field(default_factory=list)
    diagnostics: dict[str, Any] = field(default_factory=dict)

    def points_as_dicts(self) -> list[dict[str, Any]]:
        return [item.as_dict() for item in self.points]

    def as_dict(self) -> dict[str, Any]:
        return {
            "points": self.points_as_dicts(),
            "model_name": self.model_name,
            "model_version": self.model_version,
            "confidence": self.confidence,
            "training_points": self.training_points,
            "fallback_used": self.fallback_used,
            "data_start": self.data_start,
            "data_end": self.data_end,
            "methodology": self.methodology,
            "diagnostics": self.diagnostics,
        }
