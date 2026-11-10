#!/usr/bin/env python3
"""Export potato market history from TuberIntel DB into a training CSV.

By default demonstration/seed rows are excluded. This guard is intentional: a
trained artifact should never silently learn from seeded demo market prices.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.core.config import get_settings  # noqa: E402

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database-url", default=os.getenv("DATABASE_URL") or get_settings().database_url)
    parser.add_argument("--output", type=Path, default=ROOT / "ml" / "artifacts" / "market_history.csv")
    parser.add_argument("--state")
    parser.add_argument("--market")
    parser.add_argument("--variety")
    parser.add_argument("--include-demo", action="store_true")
    args = parser.parse_args()
    if not args.database_url:
        raise SystemExit("Provide --database-url or DATABASE_URL")
    url = args.database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    engine = create_engine(url, future=True)
    conditions = ["commodity = 'Potato'", "modal_price > 0"]
    params: dict[str, str] = {}
    if not args.include_demo:
        conditions.append("lower(source) NOT LIKE '%demo%'")
        conditions.append("lower(source) NOT LIKE '%seed%'")
    for column in ("state", "market", "variety"):
        value = getattr(args, column)
        if value:
            conditions.append(f"{column} = :{column}")
            params[column] = value
    query = text(
        "SELECT state,district,market,commodity,variety,grade,arrival_date,min_price,max_price,modal_price,source,fetched_at "
        "FROM market_prices WHERE " + " AND ".join(conditions) + " ORDER BY arrival_date, state, district, market, variety, grade"
    )
    with engine.connect() as connection:
        frame = pd.read_sql(query, connection, params=params)
    if frame.empty:
        raise SystemExit("No eligible real market-price rows found. Demo rows are excluded by default.")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(args.output, index=False)
    print(f"Exported {len(frame):,} rows -> {args.output}")
    print(f"Date range: {frame.arrival_date.min()} .. {frame.arrival_date.max()}")
    print(f"Markets: {frame.market.nunique()} | varieties: {frame.variety.nunique()}")


if __name__ == "__main__":
    main()
