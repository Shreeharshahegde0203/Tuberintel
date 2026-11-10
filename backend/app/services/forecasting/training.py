from __future__ import annotations



from dataclasses import dataclass

from datetime import datetime, timezone

from pathlib import Path

from typing import Any, Iterable, Sequence



import joblib

import numpy as np

import pandas as pd



from app.services.forecasting.features import (

    DEFAULT_HORIZONS,

    FeatureConfig,

    build_supervised,

    feature_columns,

    parse_market_dates,

)

from app.services.forecasting.metrics import summarize_metrics



EVALUATION_HORIZONS = (1, 7, 14, 30)





@dataclass(slots=True)

class ModelSpec:

    name: str

    factory: Any | None

    eligible: bool = True





@dataclass(slots=True)

class BacktestResult:

    model_metrics: dict[str, dict[str, Any]]

    residuals: dict[str, dict[int, list[float]]]

    selection: dict[str, Any]

    category_maps: dict[str, dict[str, int]]

    feature_config: FeatureConfig

    training_points: int





def _lightgbm_factory() -> Any:

    import lightgbm as lgb



    return lgb.LGBMRegressor(

        objective="regression_l1",

        n_estimators=420,

        learning_rate=0.035,

        num_leaves=31,

        max_depth=8,

        min_child_samples=24,

        subsample=0.90,

        colsample_bytree=0.88,

        reg_alpha=0.20,

        reg_lambda=0.35,

        random_state=42,

        verbosity=-1,

        n_jobs=-1,

    )





def _xgboost_factory() -> Any:

    import xgboost as xgb



    return xgb.XGBRegressor(

        objective="reg:absoluteerror",

        n_estimators=420,

        learning_rate=0.035,

        max_depth=7,

        min_child_weight=8,

        subsample=0.90,

        colsample_bytree=0.88,

        reg_alpha=0.20,

        reg_lambda=0.60,

        random_state=42,

        n_jobs=-1,

        tree_method="hist",

    )





def default_model_specs(*, include_xgboost: bool = True) -> list[ModelSpec]:

    specs = [ModelSpec("lightgbm_direct", _lightgbm_factory)]

    if include_xgboost:

        try:

            import xgboost  # noqa: F401



            specs.append(ModelSpec("xgboost_direct", _xgboost_factory))

        except Exception:

            pass

    return specs





def _fold_windows(dates: Sequence[pd.Timestamp], *, folds: int, validation_days: int, min_train_days: int) -> list[tuple[pd.Timestamp, pd.Timestamp]]:

    if not dates:

        return []

    unique = pd.DatetimeIndex(sorted(pd.unique(pd.to_datetime(dates))))

    last = unique.max()

    windows: list[tuple[pd.Timestamp, pd.Timestamp]] = []

    for offset in reversed(range(folds)):

        validation_end = last - pd.Timedelta(days=offset * validation_days)

        validation_start = validation_end - pd.Timedelta(days=validation_days - 1)

        cutoff = validation_start - pd.Timedelta(days=1)

        if (cutoff - unique.min()).days < min_train_days:

            continue

        windows.append((cutoff, validation_end))

    return windows





def _predict_price(model: Any, rows: pd.DataFrame, columns: list[str]) -> np.ndarray:

    predicted_return = np.asarray(model.predict(rows[columns]), dtype=float)

    origin = rows["modal_price"].to_numpy(dtype=float)

    return np.maximum(origin * np.exp(predicted_return), 0.0)





def _baseline_prediction(name: str, rows: pd.DataFrame) -> np.ndarray:

    origin = rows["modal_price"].to_numpy(dtype=float)

    if name == "persistence":

        return origin

    if name == "seasonal_naive_7":

        lag_return = rows["lag_7_return"].to_numpy(dtype=float)

        lag_price = origin / np.exp(lag_return)

        return np.where(np.isfinite(lag_price), lag_price, origin)

    if name == "seasonal_naive_28":

        lag_return = rows["lag_28_return"].to_numpy(dtype=float)

        lag_price = origin / np.exp(lag_return)

        return np.where(np.isfinite(lag_price), lag_price, origin)

    raise ValueError(name)





def _metric_summary(rows: pd.DataFrame, prediction: np.ndarray, persistence_prediction: np.ndarray) -> dict[str, Any]:

    actual = rows["target_price"].to_numpy(dtype=float)

    origin = rows["modal_price"].to_numpy(dtype=float)

    naive_mae = float(np.mean(np.abs(actual - persistence_prediction)))

    overall = summarize_metrics(actual=actual, predicted=prediction, origin=origin, naive_scale=max(naive_mae, 1e-6))

    per_horizon: dict[str, dict[str, float]] = {}

    for horizon in EVALUATION_HORIZONS:

        mask = rows["horizon_days"].eq(horizon).to_numpy()

        if not np.any(mask):

            continue

        actual_h = actual[mask]

        predicted_h = prediction[mask]

        origin_h = origin[mask]

        persistence_h = persistence_prediction[mask]

        scale_h = float(np.mean(np.abs(actual_h - persistence_h)))

        per_horizon[str(horizon)] = summarize_metrics(

            actual=actual_h,

            predicted=predicted_h,

            origin=origin_h,

            naive_scale=max(scale_h, 1e-6),

        )

    overall["per_horizon"] = per_horizon

    if per_horizon:

        weights = {"1": 0.15, "7": 0.30, "14": 0.30, "30": 0.25}

        available = [(weights[key], value["mase"]) for key, value in per_horizon.items() if key in weights and np.isfinite(value["mase"])]

        weight_sum = sum(item[0] for item in available)

        overall["weighted_mase"] = float(sum(weight * value for weight, value in available) / max(weight_sum, 1e-9))

    else:

        overall["weighted_mase"] = float(overall["mase"])

    return overall





def backtest_models(

    frame: pd.DataFrame,

    *,

    folds: int = 3,

    validation_days: int = 60,

    min_train_days: int = 180,

    horizons: Sequence[int] = DEFAULT_HORIZONS,

    feature_config: FeatureConfig | None = None,

    include_xgboost: bool = True,

) -> BacktestResult:

    config = feature_config or FeatureConfig()

    supervised, category_maps = build_supervised(frame, horizons=horizons, config=config, require_observed_target=True)

    if supervised.empty:

        raise ValueError("No leakage-safe supervised rows could be built from the market history")



    windows = _fold_windows(

        supervised["arrival_date"].tolist(),

        folds=folds,

        validation_days=validation_days,

        min_train_days=min_train_days,

    )

    if not windows:

        raise ValueError("Not enough chronological history for expanding-window backtesting")



    columns = feature_columns(config.include_weather)

    baseline_names = ["persistence", "seasonal_naive_7", "seasonal_naive_28"]

    specs = default_model_specs(include_xgboost=include_xgboost)

    fold_predictions: dict[str, list[pd.DataFrame]] = {name: [] for name in baseline_names + [spec.name for spec in specs]}

    residuals: dict[str, dict[int, list[float]]] = {name: {} for name in fold_predictions}



    for fold_index, (cutoff, validation_end) in enumerate(windows, start=1):

        # A training example is legal only if its TARGET was already known by cutoff.

        train = supervised[pd.to_datetime(supervised["target_date"]) <= cutoff].copy()

        validation = supervised[

            (pd.to_datetime(supervised["arrival_date"]) > cutoff)

            & (pd.to_datetime(supervised["target_date"]) <= validation_end)

        ].copy()

        if len(train) < 300 or len(validation) < 20:

            continue

        persistence_prediction = _baseline_prediction("persistence", validation)



        for name in baseline_names:

            prediction = _baseline_prediction(name, validation)

            result = validation[["arrival_date", "target_date", "horizon_days", "modal_price", "target_price"]].copy()

            result["prediction"] = prediction

            result["fold"] = fold_index

            fold_predictions[name].append(result)

            errors = np.abs(result["target_price"].to_numpy(dtype=float) - prediction)

            for horizon, error in zip(result["horizon_days"], errors, strict=False):

                residuals[name].setdefault(int(horizon), []).append(float(error))



        for spec in specs:

            try:

                model = spec.factory()

                model.fit(train[columns], train["target_return"])

                prediction = _predict_price(model, validation, columns)

            except Exception:

                continue

            result = validation[["arrival_date", "target_date", "horizon_days", "modal_price", "target_price"]].copy()

            result["prediction"] = prediction

            result["fold"] = fold_index

            fold_predictions[spec.name].append(result)

            errors = np.abs(result["target_price"].to_numpy(dtype=float) - prediction)

            for horizon, error in zip(result["horizon_days"], errors, strict=False):

                residuals[spec.name].setdefault(int(horizon), []).append(float(error))



    metrics: dict[str, dict[str, Any]] = {}

    for name, pieces in fold_predictions.items():

        if not pieces:

            continue

        rows = pd.concat(pieces, ignore_index=True)

        prediction = rows["prediction"].to_numpy(dtype=float)

        persistence_prediction = _baseline_prediction("persistence", rows)

        metrics[name] = _metric_summary(rows, prediction, persistence_prediction)

        metrics[name]["validation_rows"] = int(len(rows))

        metrics[name]["folds"] = int(rows["fold"].nunique())



    if "persistence" not in metrics:

        raise ValueError("Backtest did not produce a persistence baseline")



    eligible = {name: data for name, data in metrics.items() if np.isfinite(float(data.get("weighted_mase", np.inf)))}

    if not eligible:

        champion = "persistence"

    else:

        champion = min(eligible, key=lambda name: (float(eligible[name]["weighted_mase"]), float(eligible[name]["mae"])))



    # A learned model is not promoted unless it genuinely beats persistence on

    # the weighted horizon score. This prevents 'ML theatre'.

    if champion not in baseline_names and float(metrics[champion]["weighted_mase"]) >= 0.99:

        baseline_eligible = {name: metrics[name] for name in baseline_names if name in metrics}

        champion = min(baseline_eligible, key=lambda name: (float(baseline_eligible[name]["weighted_mase"]), float(baseline_eligible[name]["mae"])))



    selection = {

        "champion": champion,

        "criterion": "lowest weighted MASE across D+1/D+7/D+14/D+30; learned models must beat persistence",

        "folds_requested": folds,

        "fold_windows": [{"train_cutoff": cutoff.isoformat(), "validation_end": end.isoformat()} for cutoff, end in windows],

    }

    return BacktestResult(

        model_metrics=metrics,

        residuals=residuals,

        selection=selection,

        category_maps=category_maps,

        feature_config=config,

        training_points=int(frame["arrival_date"].nunique()),

    )





def calibration_quantiles(residuals: dict[int, list[float]], level: float = 0.80) -> dict[int, float]:

    result: dict[int, float] = {}

    for horizon, values in residuals.items():

        clean = np.asarray([value for value in values if np.isfinite(value) and value >= 0], dtype=float)

        if len(clean):

            result[int(horizon)] = float(np.quantile(clean, level))

    return result





def fit_final_model(

    frame: pd.DataFrame,

    *,

    champion: str,

    category_maps: dict[str, dict[str, int]],

    feature_config: FeatureConfig,

    horizons: Sequence[int] = DEFAULT_HORIZONS,

) -> Any | None:

    if champion in {"persistence", "seasonal_naive_7", "seasonal_naive_28", "robust_seasonal_trend"}:

        return None

    supervised, _ = build_supervised(

        frame,

        horizons=horizons,

        category_maps=category_maps,

        config=feature_config,

        require_observed_target=True,

    )

    columns = feature_columns(feature_config.include_weather)

    if champion == "lightgbm_direct":

        model = _lightgbm_factory()

    elif champion == "xgboost_direct":

        model = _xgboost_factory()

    else:

        raise ValueError(f"Unsupported final champion: {champion}")

    model.fit(supervised[columns], supervised["target_return"])

    return model





def train_and_save_artifact(

    frame: pd.DataFrame,

    output: Path,

    *,

    folds: int = 3,

    validation_days: int = 60,

    min_train_days: int = 180,

    include_xgboost: bool = True,

    include_weather: bool = False,

    interval_level: float = 0.80,

    model_version: str | None = None,

) -> dict[str, Any]:

    config = FeatureConfig(include_weather=include_weather)

    result = backtest_models(

        frame,

        folds=folds,

        validation_days=validation_days,

        min_train_days=min_train_days,

        feature_config=config,

        include_xgboost=include_xgboost,

    )

    champion = str(result.selection["champion"])

    final_model = fit_final_model(

        frame,

        champion=champion,

        category_maps=result.category_maps,

        feature_config=config,

    )

    version = model_version or datetime.now(timezone.utc).strftime("price-v2-%Y%m%dT%H%M%SZ")

    calibration = {

        name: calibration_quantiles(values, interval_level)

        for name, values in result.residuals.items()

    }

    persistence_errors = [value for values in result.residuals.get("persistence", {}).values() for value in values]

    fallback_error = float(np.quantile(persistence_errors, interval_level)) if persistence_errors else 75.0

    artifact = {

        "artifact_version": 2,

        "model_version": version,

        "champion": champion,

        "models": {champion: final_model} if final_model is not None else {},

        "category_maps": result.category_maps,

        "feature_columns": feature_columns(config.include_weather),

        "feature_config": {

            "max_ffill_days": config.max_ffill_days,

            "include_weather": config.include_weather,

        },

        "horizons": list(DEFAULT_HORIZONS),

        "operational_horizon_days": 30,

        "model_metrics": result.model_metrics,

        "selection": result.selection,

        "calibration": calibration,

        "interval_level": interval_level,

        "fallback_error": fallback_error,

        "training_points": result.training_points,

        "created_at": datetime.now(timezone.utc).isoformat(),

    }

    output.parent.mkdir(parents=True, exist_ok=True)

    joblib.dump(artifact, output)

    metrics_path = output.with_suffix(".metrics.json")

    serializable = {key: value for key, value in artifact.items() if key != "models"}

    import json



    metrics_path.write_text(json.dumps(serializable, indent=2, default=str), encoding="utf-8")

    return artifact





def evaluate_sarimax_challenger(frame: pd.DataFrame, *, horizon_days: int = 30, origins: int = 3) -> dict[str, Any]:

    """Small statistical challenger benchmark; intentionally not used in runtime.



    Fits only the longest exact market series because full panel SARIMAX is too

    expensive for routine retraining. It exists to keep a classical statistical

    benchmark in model-development reports.

    """

    try:

        from statsmodels.tsa.statespace.sarimax import SARIMAX

    except Exception as exc:

        return {"status": "unavailable", "reason": str(exc)}



    data = frame.copy()

    data["arrival_date"] = parse_market_dates(data["arrival_date"])

    data["modal_price"] = pd.to_numeric(data["modal_price"], errors="coerce")

    group_cols = [column for column in ("state", "district", "market", "variety", "grade") if column in data.columns]

    if group_cols:

        groups = list(data.dropna(subset=["arrival_date", "modal_price"]).groupby(group_cols, dropna=False))

        if not groups:

            return {"status": "insufficient_data"}

        _, data = max(groups, key=lambda item: len(item[1]))

    series = data.groupby("arrival_date")["modal_price"].median().sort_index()

    if len(series) < 240:

        return {"status": "insufficient_data", "points": int(len(series))}

    errors: dict[int, list[float]] = {h: [] for h in EVALUATION_HORIZONS if h <= horizon_days}

    step = max(30, horizon_days)

    cutoffs = [len(series) - step * k - horizon_days for k in range(origins, 0, -1)]

    for cutoff in cutoffs:

        if cutoff < 180:

            continue

        train = series.iloc[:cutoff]

        actual = series.iloc[cutoff : cutoff + horizon_days]

        # Statsmodels cannot reliably extend an irregular DatetimeIndex.
        # AGMARKNET/mandi observations may have missing reporting dates, so
        # fit SARIMAX on the numeric sequence and manage target dates outside
        # the statistical model. This avoids inventing artificial daily rows.
        train_values = train.to_numpy(dtype=float)
        actual_values = actual.to_numpy(dtype=float)

        try:

            fitted = SARIMAX(

                train_values,

                order=(1, 1, 1),

                seasonal_order=(1, 0, 0, 7),

                enforce_stationarity=False,

                enforce_invertibility=False,

            ).fit(disp=False, maxiter=80)

            pred = np.asarray(
                fitted.forecast(steps=horizon_days),
                dtype=float,
            )

        except Exception:

            continue

        for h in errors:

            if h <= len(actual_values):

                errors[h].append(float(abs(actual_values[h - 1] - pred[h - 1])))

    if not any(errors.values()):

        return {"status": "failed"}

    return {

        "status": "ok",

        "market_points": int(len(series)),

        "mae_by_horizon": {str(h): float(np.mean(values)) for h, values in errors.items() if values},

    }





def evaluate_gru_challenger(

    frame: pd.DataFrame,

    *,

    lookback: int = 60,

    horizon_days: int = 30,

    epochs: int = 8,

    hidden_size: int = 32,

) -> dict[str, Any]:

    """Optional neural challenger on the longest market series.



    It is deliberately isolated from the champion runtime until it wins a

    leakage-safe benchmark and a dedicated runtime adapter is enabled.

    """

    try:

        import torch

        from torch import nn

    except Exception as exc:

        return {"status": "unavailable", "reason": str(exc)}



    data = frame.copy()

    data["arrival_date"] = parse_market_dates(data["arrival_date"])

    data["modal_price"] = pd.to_numeric(data["modal_price"], errors="coerce")

    group_cols = [column for column in ("state", "district", "market", "variety", "grade") if column in data.columns]

    if group_cols:

        groups = list(data.dropna(subset=["arrival_date", "modal_price"]).groupby(group_cols, dropna=False))

        if not groups:

            return {"status": "insufficient_data"}

        _, data = max(groups, key=lambda item: len(item[1]))

    series = data.groupby("arrival_date")["modal_price"].median().sort_index()

    full = pd.date_range(series.index.min(), series.index.max(), freq="D")

    series = series.reindex(full).ffill(limit=3).dropna()

    values = series.to_numpy(dtype=np.float32)

    if len(values) < lookback + horizon_days + 120:

        return {"status": "insufficient_data", "points": int(len(values))}



    # Train on old data and reserve the newest 90+ days. Normalization is fit on

    # training values only, preventing future scale leakage.

    validation_days = max(90, horizon_days * 2)

    split = len(values) - validation_days

    mean = float(np.mean(values[:split]))

    std = float(np.std(values[:split])) or 1.0

    normalized = (values - mean) / std



    def windows(end: int) -> tuple[np.ndarray, np.ndarray]:

        xs, ys = [], []

        for index in range(lookback, end - horizon_days + 1):

            xs.append(normalized[index - lookback : index])

            ys.append(normalized[index : index + horizon_days])

        return np.asarray(xs, dtype=np.float32), np.asarray(ys, dtype=np.float32)



    train_x, train_y = windows(split)

    if len(train_x) < 80:

        return {"status": "insufficient_data"}



    class GRUModel(nn.Module):

        def __init__(self) -> None:

            super().__init__()

            self.gru = nn.GRU(1, hidden_size, batch_first=True)

            self.head = nn.Linear(hidden_size, horizon_days)



        def forward(self, x: Any) -> Any:

            output, _ = self.gru(x)

            return self.head(output[:, -1, :])



    torch.manual_seed(42)

    model = GRUModel()

    optimizer = torch.optim.Adam(model.parameters(), lr=0.005, weight_decay=1e-4)

    loss_fn = nn.SmoothL1Loss()

    x_tensor = torch.from_numpy(train_x[:, :, None])

    y_tensor = torch.from_numpy(train_y)

    batch = 64

    model.train()

    for _ in range(max(1, epochs)):

        order = torch.randperm(len(x_tensor))

        for start in range(0, len(order), batch):

            idx = order[start : start + batch]

            optimizer.zero_grad()

            prediction = model(x_tensor[idx])

            loss = loss_fn(prediction, y_tensor[idx])

            loss.backward()

            optimizer.step()



    origins = []

    for index in range(split, len(values) - horizon_days + 1, 7):

        origins.append(index)

    if not origins:

        return {"status": "insufficient_validation"}

    predictions = []

    actuals = []

    model.eval()

    with torch.no_grad():

        for index in origins:

            x = torch.from_numpy(normalized[index - lookback : index][None, :, None].astype(np.float32))

            pred = model(x).numpy()[0] * std + mean

            predictions.append(pred)

            actuals.append(values[index : index + horizon_days])

    prediction_array = np.asarray(predictions)

    actual_array = np.asarray(actuals)

    result: dict[str, Any] = {"status": "ok", "validation_origins": len(origins), "mae_by_horizon": {}}

    for h in EVALUATION_HORIZONS:

        if h <= horizon_days:

            result["mae_by_horizon"][str(h)] = float(np.mean(np.abs(actual_array[:, h - 1] - prediction_array[:, h - 1])))

    return result
