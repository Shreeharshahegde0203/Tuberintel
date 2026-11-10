#!/usr/bin/env python3
"""Generate deterministic multi-market potato prices for forecast-engine tests.

The generated data is synthetic and MUST NOT be presented as real market data.
It intentionally contains trend, weekly/annual seasonality, cross-market effects,
weather effects and a few missing reporting days so leakage/fallback behaviour can
be tested before real AGMARKNET history is used.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd


def generate(days: int = 900, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    start = pd.Timestamp("2023-01-01")
    dates = pd.date_range(start, periods=days, freq="D")
    markets = [
        ("Karnataka", "Bengaluru Urban", "Binny Mill (F&V), Bengaluru", "Local", 80.0),
        ("Karnataka", "Kolar", "Kolar APMC", "Kufri Jyoti", -60.0),
        ("Karnataka", "Chikkaballapur", "Chikkaballapur APMC", "Local", -100.0),
        ("Karnataka", "Bengaluru Rural", "Doddaballapur APMC", "Kufri Jyoti", 20.0),
    ]
    rows: list[dict] = []
    common_shock = rng.normal(0, 18, size=days).cumsum() * 0.10
    for market_index, (state, district, market, variety, premium) in enumerate(markets):
        local_noise = rng.normal(0, 35, size=days)
        temperature = 24 + 4.5 * np.sin(2 * np.pi * (np.arange(days) - 40) / 365.25) + rng.normal(0, 1.1, days)
        rain = np.maximum(0, 5 + 10 * np.sin(2 * np.pi * (np.arange(days) - 160) / 365.25) + rng.normal(0, 4.0, days))
        humidity = np.clip(62 + rain * 1.2 + rng.normal(0, 4, days), 35, 98)
        annual = 220 * np.sin(2 * np.pi * (np.arange(days) - 20) / 365.25)
        weekly = 42 * np.sin(2 * np.pi * np.arange(days) / 7.0 + market_index * 0.25)
        slow_trend = 0.55 * np.arange(days)
        # Rain has a lagged supply/handling effect to make exogenous forecasting
        # genuinely useful on this synthetic benchmark.
        rain_effect = np.roll(rain, 7) * 5.5
        rain_effect[:7] = rain_effect[7]
        price = 1550 + premium + slow_trend + annual + weekly + common_shock + rain_effect + local_noise
        price = np.maximum(price, 500)
        spread = 80 + np.abs(rng.normal(0, 35, days))
        for i, day in enumerate(dates):
            # Sparse reporting gaps, deterministic with seed. Never more than a few
            # consecutive days so forward-fill safety can be exercised.
            if rng.random() < 0.025:
                continue
            modal = float(price[i])
            rows.append({
                "state": state,
                "district": district,
                "market": market,
                "commodity": "Potato",
                "variety": variety,
                "grade": "FAQ",
                "arrival_date": day.date().isoformat(),
                "min_price": round(modal - spread[i] * 0.55, 2),
                "max_price": round(modal + spread[i] * 0.45, 2),
                "modal_price": round(modal, 2),
                "source": "SYNTHETIC_TEST_ONLY",
                "temperature_mean": round(float(temperature[i]), 3),
                "precipitation_mm": round(float(rain[i]), 3),
                "relative_humidity_mean": round(float(humidity[i]), 3),
            })
    return pd.DataFrame(rows).sort_values(["arrival_date", "market"]).reset_index(drop=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("ml/artifacts/dummy_market_history.csv"))
    parser.add_argument("--days", type=int, default=900)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    frame = generate(args.days, args.seed)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(args.output, index=False)
    print(f"Wrote {len(frame):,} SYNTHETIC rows to {args.output}")


if __name__ == "__main__":
    main()
