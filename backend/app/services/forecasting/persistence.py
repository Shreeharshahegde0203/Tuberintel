from __future__ import annotations

from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import MarketPrice, PriceForecast, PriceModelVersion
from app.services.forecasting.contracts import ForecastResult


def register_model_version(
    db: Session,
    *,
    artifact: dict[str, Any],
    artifact_path: str | Path,
    training_frame: Any | None = None,
    activate: bool = True,
) -> PriceModelVersion:
    version = str(artifact["model_version"])
    row = db.scalar(select(PriceModelVersion).where(PriceModelVersion.model_version == version))
    if row is None:
        training_start = None
        training_end = None
        markets = 0
        training_rows = int(artifact.get("training_points", 0))
        if training_frame is not None and len(training_frame):
            import pandas as pd

            dates = pd.to_datetime(training_frame["arrival_date"], errors="coerce").dropna()
            training_start = dates.min().date() if len(dates) else None
            training_end = dates.max().date() if len(dates) else None
            markets = int(training_frame["market"].nunique()) if "market" in training_frame else 0
            training_rows = int(len(training_frame))
        row = PriceModelVersion(
            model_name=str(artifact.get("champion", "unknown")),
            model_version=version,
            feature_version="forecast-v2",
            training_start=training_start,
            training_end=training_end,
            training_rows=training_rows,
            markets=markets,
            metrics_json=artifact.get("model_metrics", {}),
            artifact_path=str(artifact_path),
            active=bool(activate),
        )
        db.add(row)
    else:
        row.model_name = str(artifact.get("champion", row.model_name))
        row.metrics_json = artifact.get("model_metrics", row.metrics_json)
        row.artifact_path = str(artifact_path)
        row.active = bool(activate)
    if activate:
        db.query(PriceModelVersion).filter(PriceModelVersion.model_version != version).update({"active": False})
    db.commit()
    db.refresh(row)
    return row


def persist_forecast_snapshot(
    db: Session,
    *,
    result: ForecastResult,
    state: str,
    district: str | None,
    market: str | None,
    variety: str | None,
    grade: str | None = None,
) -> int:
    if not result.points or not result.data_end:
        return 0
    changed = 0
    for point in result.points:
        conditions = [
            PriceForecast.state == state,
            PriceForecast.forecast_origin == result.data_end,
            PriceForecast.target_date == point.date,
            PriceForecast.model_version == result.model_version,
        ]
        for column, value in ((PriceForecast.district, district), (PriceForecast.market, market), (PriceForecast.variety, variety), (PriceForecast.grade, grade)):
            conditions.append(column.is_(None) if value is None else column == value)
        row = db.scalar(select(PriceForecast).where(*conditions))
        values = {
            "horizon_days": point.horizon_days,
            "predicted_price": point.predicted_price,
            "lower_bound": point.lower_bound,
            "upper_bound": point.upper_bound,
            "confidence": point.confidence,
            "model_name": result.model_name,
        }
        if row:
            for key, value in values.items():
                setattr(row, key, value)
        else:
            db.add(
                PriceForecast(
                    state=state,
                    district=district,
                    market=market,
                    variety=variety,
                    grade=grade,
                    forecast_origin=result.data_end,
                    target_date=point.date,
                    model_version=result.model_version,
                    **values,
                )
            )
        changed += 1
    db.commit()
    return changed


def reconcile_realized_prices(db: Session, *, limit: int = 5000) -> dict[str, float | int]:
    rows = list(
        db.scalars(
            select(PriceForecast)
            .where(PriceForecast.actual_price.is_(None))
            .order_by(PriceForecast.target_date)
            .limit(limit)
        )
    )
    updated = 0
    errors: list[float] = []
    for forecast in rows:
        conditions = [
            MarketPrice.state == forecast.state,
            MarketPrice.arrival_date == forecast.target_date,
            MarketPrice.commodity == "Potato",
        ]
        if forecast.district:
            conditions.append(MarketPrice.district == forecast.district)
        if forecast.market:
            conditions.append(MarketPrice.market == forecast.market)
        if forecast.variety:
            conditions.append(MarketPrice.variety == forecast.variety)
        if forecast.grade:
            conditions.append(MarketPrice.grade == forecast.grade)
        values = list(db.scalars(select(MarketPrice.modal_price).where(*conditions)))
        actual = None
        if values:
            import numpy as np

            actual = float(np.median(values))
        if actual is None:
            continue
        forecast.actual_price = float(actual)
        forecast.absolute_error = abs(float(actual) - forecast.predicted_price)
        errors.append(forecast.absolute_error)
        updated += 1
    db.commit()
    return {
        "updated": updated,
        "mae": float(sum(errors) / len(errors)) if errors else 0.0,
    }
