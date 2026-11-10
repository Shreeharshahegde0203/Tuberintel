#!/usr/bin/env python3
"""Backfill/upsert official potato mandi rows through TuberIntel's data.gov adapter.

This reuses the production ingestion service, so training data and application
market data follow the same parsing, uniqueness and provenance rules.
"""
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
from app.services.market_service import MarketService  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database-url", default=os.getenv("DATABASE_URL") or get_settings().database_url)
    parser.add_argument("--state", default="Karnataka")
    parser.add_argument("--district")
    parser.add_argument("--max-pages", type=int, default=80)
    args = parser.parse_args()
    if not args.database_url:
        raise SystemExit("Provide --database-url or DATABASE_URL")
    url = args.database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    engine = create_engine(url, future=True)
    service = MarketService()
    if not service.settings.data_gov_api_key:
        raise SystemExit("DATA_GOV_API_KEY must be configured in backend/.env or the environment")
    with Session(engine) as db:
        result = service.refresh_from_data_gov(
            db, state=args.state, district=args.district, max_pages=max(args.max_pages, 1)
        )
    print(result)


if __name__ == "__main__":
    main()
