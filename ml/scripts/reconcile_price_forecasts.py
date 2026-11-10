#!/usr/bin/env python3
"""Attach realized mandi prices to stored forecast snapshots for monitoring."""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.core.config import get_settings  # noqa: E402
from app.services.forecasting.persistence import reconcile_realized_prices  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database-url", default=os.getenv("DATABASE_URL") or get_settings().database_url)
    parser.add_argument("--limit", type=int, default=5000)
    args = parser.parse_args()
    if not args.database_url:
        raise SystemExit("Provide --database-url or DATABASE_URL")
    url = args.database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    engine = create_engine(url, future=True)
    with Session(engine) as db:
        result = reconcile_realized_prices(db, limit=args.limit)
    print(result)


if __name__ == "__main__":
    main()
