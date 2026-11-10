from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence

import numpy as np
import pandas as pd

IDENTITY_COLUMNS = ["state", "district", "market", "variety", "grade"]
CATEGORY_COLUMNS = ["state", "district", "market", "variety", "grade"]
OPTIONAL_WEATHER_COLUMNS = [
    "temperature_mean",
    "precipitation_mm",
    "relative_humidity_mean",
]
WEATHER_FEATURES = [
    "temperature_mean",
    "precipitation_mm",
    "relative_humidity_mean",
    "precipitation_7d",
    "precipitation_14d",
    "precipitation_lag_7",
    "temperature_7d",
    "temperature_anomaly_30d",
    "humidity_7d",
]
DEFAULT_HORIZONS = tuple(range(1, 31))

def parse_market_dates(values: pd.Series) -> pd.Series:
    """Parse ISO and Indian DD/MM/YYYY dates without swapping month/day."""
    raw = values.astype(str).str.strip()
    result = pd.Series(pd.NaT, index=values.index, dtype="datetime64[ns]")
    iso_mask = raw.str.match(r"^\d{4}-\d{2}-\d{2}(?:[ T].*)?$")
    if iso_mask.any():
        result.loc[iso_mask] = pd.to_datetime(raw.loc[iso_mask], errors="coerce", yearfirst=True)
    other = ~iso_mask
    if other.any():
        result.loc[other] = pd.to_datetime(raw.loc[other], errors="coerce", format="mixed", dayfirst=True)
    return result


NUMERIC_FEATURES = [
    "log_price",
    "spread_ratio",
    "lag_1_return",
    "lag_2_return",
    "lag_3_return",
    "lag_7_return",
    "lag_14_return",
    "lag_28_return",
    "lag_56_return",
    "rolling_mean_7_ratio",
    "rolling_mean_14_ratio",
    "rolling_mean_30_ratio",
    "rolling_median_7_ratio",
    "rolling_median_30_ratio",
    "rolling_std_7",
    "rolling_std_14",
    "rolling_std_30",
    "momentum_7",
    "momentum_14",
    "momentum_30",
    "ewm_7_ratio",
    "ewm_21_ratio",
    "days_since_observed",
    "state_price_ratio",
    "district_price_ratio",
    "dow_sin",
    "dow_cos",
    "doy_sin",
    "doy_cos",
    "month_sin",
    "month_cos",
    "horizon_days",
    "state_code",
    "district_code",
    "market_code",
    "variety_code",
    "grade_code",
]


@dataclass(frozen=True)
class FeatureConfig:
    max_ffill_days: int = 3
    include_weather: bool = False


def normalize_frame(frame: pd.DataFrame) -> pd.DataFrame:
    required = {"arrival_date", "modal_price"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Missing required market columns: {sorted(missing)}")

    data = frame.copy()
    data["arrival_date"] = parse_market_dates(data["arrival_date"])
    for column in ("modal_price", "min_price", "max_price"):
        if column not in data:
            data[column] = np.nan
        data[column] = pd.to_numeric(data[column], errors="coerce")
    data = data.dropna(subset=["arrival_date", "modal_price"])
    data = data[data["modal_price"] > 0].copy()

    defaults = {
        "state": "Unknown",
        "district": "Unknown",
        "market": "Unknown",
        "variety": "Local",
        "grade": "FAQ",
        "commodity": "Potato",
        "source": "unknown",
    }
    for column, default in defaults.items():
        if column not in data:
            data[column] = default
        data[column] = data[column].fillna(default).astype(str).str.strip().replace("", default)

    for column in OPTIONAL_WEATHER_COLUMNS:
        if column in data:
            data[column] = pd.to_numeric(data[column], errors="coerce")

    # One observation per exact market identity/date. Median is robust to accidental
    # duplicate fetches while database uniqueness normally prevents them.
    aggregations: dict[str, str] = {
        "modal_price": "median",
        "min_price": "median",
        "max_price": "median",
        "commodity": "last",
        "source": "last",
    }
    for column in OPTIONAL_WEATHER_COLUMNS:
        if column in data:
            aggregations[column] = "mean"
    data = (
        data.groupby(IDENTITY_COLUMNS + ["arrival_date"], as_index=False)
        .agg(aggregations)
        .sort_values(IDENTITY_COLUMNS + ["arrival_date"])
        .reset_index(drop=True)
    )
    return data


def _regularize_group(group: pd.DataFrame, config: FeatureConfig) -> pd.DataFrame:
    group = group.sort_values("arrival_date").copy()
    identity = {column: str(group.iloc[-1][column]) for column in IDENTITY_COLUMNS}
    full_index = pd.date_range(group["arrival_date"].min(), group["arrival_date"].max(), freq="D")
    indexed = group.set_index("arrival_date").reindex(full_index)
    indexed.index.name = "arrival_date"
    for column, value in identity.items():
        indexed[column] = value

    observed = indexed["modal_price"].notna()
    indexed["is_observed"] = observed.astype(int)
    indexed["observed_modal_price"] = indexed["modal_price"]

    # Forward fill only: future observations are never pulled backwards in time.
    for column in ("modal_price", "min_price", "max_price"):
        indexed[column] = indexed[column].ffill(limit=config.max_ffill_days)

    for column in OPTIONAL_WEATHER_COLUMNS:
        if column in indexed:
            # Historical weather should already be point-in-time valid. Only a tiny
            # forward fill is allowed for sparse provider rows; no back-fill.
            indexed[column] = indexed[column].ffill(limit=1)

    positions = np.arange(len(indexed), dtype=float)
    last_observed = np.where(observed.to_numpy(), positions, np.nan)
    last_observed = pd.Series(last_observed, index=indexed.index).ffill().to_numpy()
    indexed["days_since_observed"] = positions - last_observed
    indexed.loc[np.isnan(last_observed), "days_since_observed"] = np.nan
    return indexed.reset_index()


def regularize_panel(frame: pd.DataFrame, config: FeatureConfig | None = None) -> pd.DataFrame:
    config = config or FeatureConfig()
    data = normalize_frame(frame)
    pieces: list[pd.DataFrame] = []
    for _, group in data.groupby(IDENTITY_COLUMNS, sort=False, dropna=False):
        pieces.append(_regularize_group(group, config))
    if not pieces:
        return pd.DataFrame()
    panel = pd.concat(pieces, ignore_index=True)
    panel = panel.dropna(subset=["modal_price"]).copy()
    panel["modal_price"] = panel["modal_price"].astype(float)
    return panel.sort_values(IDENTITY_COLUMNS + ["arrival_date"]).reset_index(drop=True)


def build_category_maps(frame: pd.DataFrame) -> dict[str, dict[str, int]]:
    result: dict[str, dict[str, int]] = {}
    for column in CATEGORY_COLUMNS:
        values = sorted({str(value) for value in frame[column].dropna().unique()})
        result[column] = {value: index for index, value in enumerate(values)}
    return result


def _apply_category_maps(frame: pd.DataFrame, maps: Mapping[str, Mapping[str, int]]) -> pd.DataFrame:
    output = frame.copy()
    for column in CATEGORY_COLUMNS:
        mapping = maps.get(column, {})
        output[f"{column}_code"] = output[column].map(lambda value: int(mapping.get(str(value), -1)))
    return output


def engineer_origin_features(
    frame: pd.DataFrame,
    *,
    category_maps: Mapping[str, Mapping[str, int]] | None = None,
    config: FeatureConfig | None = None,
) -> tuple[pd.DataFrame, dict[str, dict[str, int]]]:
    config = config or FeatureConfig()
    panel = regularize_panel(frame, config)
    if panel.empty:
        return panel, dict(category_maps or {})

    maps = dict(category_maps or build_category_maps(panel))
    keys = IDENTITY_COLUMNS
    grouped = panel.groupby(keys, sort=False, group_keys=False)
    price = panel["modal_price"].clip(lower=1.0)
    panel["log_price"] = np.log(price)
    min_price = panel["min_price"].where(panel["min_price"] > 0, panel["modal_price"])
    max_price = panel["max_price"].where(panel["max_price"] > 0, panel["modal_price"])
    panel["spread_ratio"] = ((max_price - min_price).clip(lower=0) / price).clip(0, 2)

    for lag in (1, 2, 3, 7, 14, 28, 56):
        lag_price = grouped["modal_price"].shift(lag)
        panel[f"lag_{lag}_return"] = np.log(price / lag_price.clip(lower=1.0))

    def rolling(column: str, window: int, fn: str) -> pd.Series:
        roller = grouped[column].rolling(window, min_periods=max(2, window // 3))
        if fn == "mean":
            values = roller.mean()
        elif fn == "median":
            values = roller.median()
        else:
            values = roller.std()
        return values.reset_index(level=keys, drop=True).sort_index()

    for window in (7, 14, 30):
        mean_value = rolling("modal_price", window, "mean")
        panel[f"rolling_mean_{window}_ratio"] = mean_value / price
    for window in (7, 30):
        median_value = rolling("modal_price", window, "median")
        panel[f"rolling_median_{window}_ratio"] = median_value / price
    for window in (7, 14, 30):
        # Standard deviation of log price is scale-free across markets.
        std_value = grouped["log_price"].rolling(window, min_periods=max(3, window // 3)).std()
        panel[f"rolling_std_{window}"] = std_value.reset_index(level=keys, drop=True).sort_index()

    for window in (7, 14, 30):
        lag_price = grouped["modal_price"].shift(window)
        panel[f"momentum_{window}"] = np.log(price / lag_price.clip(lower=1.0))

    for span in (7, 21):
        ewm = grouped["modal_price"].transform(lambda series: series.ewm(span=span, adjust=False).mean())
        panel[f"ewm_{span}_ratio"] = ewm / price

    # Cross-market context is calculated at the forecast origin date only.  It
    # therefore never uses a future market observation for an earlier origin.
    state_median = panel.groupby(["state", "arrival_date"])["modal_price"].transform("median")
    district_median = panel.groupby(["state", "district", "arrival_date"])["modal_price"].transform("median")
    panel["state_price_ratio"] = price / state_median.clip(lower=1.0)
    panel["district_price_ratio"] = price / district_median.clip(lower=1.0)

    dates = pd.to_datetime(panel["arrival_date"])
    dow = dates.dt.dayofweek.astype(float)
    doy = dates.dt.dayofyear.astype(float)
    month = dates.dt.month.astype(float)
    panel["dow_sin"] = np.sin(2 * np.pi * dow / 7.0)
    panel["dow_cos"] = np.cos(2 * np.pi * dow / 7.0)
    panel["doy_sin"] = np.sin(2 * np.pi * doy / 365.25)
    panel["doy_cos"] = np.cos(2 * np.pi * doy / 365.25)
    panel["month_sin"] = np.sin(2 * np.pi * (month - 1) / 12.0)
    panel["month_cos"] = np.cos(2 * np.pi * (month - 1) / 12.0)

    if config.include_weather:
        for column in OPTIONAL_WEATHER_COLUMNS:
            if column not in panel:
                panel[column] = np.nan
        # Weather features are origin-time values only. Future weather must be
        # provided separately by a point-in-time forecast source, never actuals.
        panel["temperature_mean"] = pd.to_numeric(panel["temperature_mean"], errors="coerce")
        panel["precipitation_mm"] = pd.to_numeric(panel["precipitation_mm"], errors="coerce")
        panel["relative_humidity_mean"] = pd.to_numeric(panel["relative_humidity_mean"], errors="coerce")
        weather_group = panel.groupby(keys, sort=False, group_keys=False)
        panel["precipitation_7d"] = weather_group["precipitation_mm"].transform(lambda series: series.rolling(7, min_periods=2).sum())
        panel["precipitation_14d"] = weather_group["precipitation_mm"].transform(lambda series: series.rolling(14, min_periods=4).sum())
        panel["precipitation_lag_7"] = weather_group["precipitation_mm"].shift(7)
        panel["temperature_7d"] = weather_group["temperature_mean"].transform(lambda series: series.rolling(7, min_periods=2).mean())
        temperature_30d = weather_group["temperature_mean"].transform(lambda series: series.rolling(30, min_periods=7).mean())
        panel["temperature_anomaly_30d"] = panel["temperature_mean"] - temperature_30d
        panel["humidity_7d"] = weather_group["relative_humidity_mean"].transform(lambda series: series.rolling(7, min_periods=2).mean())

    panel = _apply_category_maps(panel, maps)
    return panel, maps


def feature_columns(include_weather: bool = False) -> list[str]:
    columns = list(NUMERIC_FEATURES)
    if include_weather:
        columns.extend(WEATHER_FEATURES)
    return columns


def build_supervised(
    frame: pd.DataFrame,
    *,
    horizons: Sequence[int] = DEFAULT_HORIZONS,
    category_maps: Mapping[str, Mapping[str, int]] | None = None,
    config: FeatureConfig | None = None,
    require_observed_target: bool = True,
) -> tuple[pd.DataFrame, dict[str, dict[str, int]]]:
    origins, maps = engineer_origin_features(frame, category_maps=category_maps, config=config)
    if origins.empty:
        return origins, maps
    keys = IDENTITY_COLUMNS
    grouped = origins.groupby(keys, sort=False, group_keys=False)
    parts: list[pd.DataFrame] = []
    for horizon in horizons:
        if horizon < 1 or horizon > 90:
            raise ValueError("Forecast horizons must be between 1 and 90 days")
        part = origins.copy()
        part["horizon_days"] = int(horizon)
        part["target_price"] = grouped["modal_price"].shift(-horizon)
        part["target_is_observed"] = grouped["is_observed"].shift(-horizon)
        part["target_date"] = pd.to_datetime(part["arrival_date"]) + pd.to_timedelta(horizon, unit="D")
        part["target_return"] = np.log(part["target_price"].clip(lower=1.0) / part["modal_price"].clip(lower=1.0))
        mask = part["target_price"].notna()
        if require_observed_target:
            mask &= part["target_is_observed"].fillna(0).eq(1)
        parts.append(part.loc[mask])
    data = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()
    columns = feature_columns((config or FeatureConfig()).include_weather)
    if not data.empty:
        # When weather is enabled it is treated as a real model input, so origins
        # without the required point-in-time weather history are excluded rather
        # than silently imputed from future values.
        data = data.dropna(subset=columns)
    return data.reset_index(drop=True), maps


def latest_origin_rows(
    frame: pd.DataFrame,
    *,
    horizons: Iterable[int],
    category_maps: Mapping[str, Mapping[str, int]],
    config: FeatureConfig | None = None,
) -> pd.DataFrame:
    origins, _ = engineer_origin_features(frame, category_maps=category_maps, config=config)
    if origins.empty:
        return origins
    latest = (
        origins.sort_values("arrival_date")
        .groupby(IDENTITY_COLUMNS, as_index=False, sort=False)
        .tail(1)
    )
    parts: list[pd.DataFrame] = []
    for horizon in horizons:
        part = latest.copy()
        part["horizon_days"] = int(horizon)
        parts.append(part)
    return pd.concat(parts, ignore_index=True)
