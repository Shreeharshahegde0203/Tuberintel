from __future__ import annotations

import logging
import math
import time
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlparse

import httpx
import numpy as np
from sqlalchemy import Select, and_, desc, func, or_, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import Market, MarketDistrict, MarketPrice, MarketState, MarketSyncRun


logger = logging.getLogger(__name__)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def normalize_name(value: str | None) -> str:
    normalized = unicodedata.normalize("NFKC", value or "")
    return " ".join(normalized.strip().lower().split())


def title_name(value: str | None, fallback: str = "Unknown") -> str:
    cleaned = " ".join((value or "").split())
    return cleaned or fallback


@dataclass
class UpstreamRecord:
    state: str
    district: str
    market: str
    commodity: str
    variety: str
    grade: str
    arrival_date: date
    min_price: float
    max_price: float
    modal_price: float
    source: str
    source_record_id: str | None


class MarketService:
    DATA_GOV_BASE = "https://api.data.gov.in/resource"
    UPSTREAM_SOURCE = "data.gov.in / AGMARKNET"

    def __init__(self) -> None:
        self.settings = get_settings()
        parsed = urlparse(self.DATA_GOV_BASE)
        self.allowed_upstream_host = parsed.hostname

    def list_states(self, db: Session) -> list[dict[str, Any]]:
        rows = db.execute(
            select(
                MarketState,
                func.count(func.distinct(MarketDistrict.id)).label("district_count"),
                func.count(func.distinct(Market.id)).label("market_count"),
            )
            .outerjoin(MarketDistrict, MarketDistrict.state_id == MarketState.id)
            .outerjoin(Market, Market.state_id == MarketState.id)
            .where(MarketState.active.is_(True))
            .group_by(MarketState.id)
            .order_by(MarketState.name.asc())
        ).all()
        return [
            {
                "id": state.id,
                "name": state.name,
                "code": state.code,
                "active": state.active,
                "district_count": district_count,
                "market_count": market_count,
            }
            for state, district_count, market_count in rows
        ]

    def list_districts(self, db: Session, state: str) -> list[dict[str, Any]]:
        state_row = self._require_state(db, state)
        rows = db.execute(
            select(
                MarketDistrict,
                func.count(Market.id).label("market_count"),
            )
            .outerjoin(Market, Market.district_id == MarketDistrict.id)
            .where(MarketDistrict.state_id == state_row.id, MarketDistrict.active.is_(True))
            .group_by(MarketDistrict.id)
            .order_by(MarketDistrict.name.asc())
        ).all()
        return [
            {
                "id": district.id,
                "name": district.name,
                "state": state_row.name,
                "active": district.active,
                "market_count": market_count,
            }
            for district, market_count in rows
        ]

    def list_markets(
        self,
        db: Session,
        *,
        state: str | None = None,
        district: str | None = None,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        limit = max(1, min(limit, 100))
        offset = max(0, min(offset, 10_000))
        query = (
            select(Market, MarketState.name.label("state_name"), MarketDistrict.name.label("district_name"))
            .join(MarketState, MarketState.id == Market.state_id)
            .join(MarketDistrict, MarketDistrict.id == Market.district_id)
            .where(Market.active.is_(True))
        )
        count_query = select(func.count(Market.id)).join(MarketState, MarketState.id == Market.state_id).join(
            MarketDistrict, MarketDistrict.id == Market.district_id
        ).where(Market.active.is_(True))
        if state:
            normalized_state = normalize_name(state)
            query = query.where(MarketState.normalized_name == normalized_state)
            count_query = count_query.where(MarketState.normalized_name == normalized_state)
        if district:
            normalized_district = normalize_name(district)
            query = query.where(MarketDistrict.normalized_name == normalized_district)
            count_query = count_query.where(MarketDistrict.normalized_name == normalized_district)
        if search:
            normalized_search = f"%{normalize_name(search)}%"
            query = query.where(
                or_(
                    Market.normalized_name.like(normalized_search),
                    MarketDistrict.normalized_name.like(normalized_search),
                )
            )
            count_query = count_query.where(
                or_(
                    Market.normalized_name.like(normalized_search),
                    MarketDistrict.normalized_name.like(normalized_search),
                )
            )

        total = db.scalar(count_query) or 0
        rows = db.execute(query.order_by(Market.name.asc()).limit(limit).offset(offset)).all()
        return {
            "state": state,
            "district": district,
            "total": total,
            "limit": limit,
            "offset": offset,
            "items": [
                {
                    "id": market.id,
                    "name": market.name,
                    "state": state_name,
                    "district": district_name,
                    "source": market.source,
                    "active": market.active,
                    "latitude": market.latitude,
                    "longitude": market.longitude,
                    "external_market_name": market.external_market_name,
                    "external_id": market.external_id,
                    "updated_at": market.updated_at,
                }
                for market, state_name, district_name in rows
            ],
            "source": self.UPSTREAM_SOURCE,
            "live_data": self._has_live_prices(db, state),
            "note": None if total else "No matching markets were found in the current directory.",
        }

    def get_filters(self, db: Session, state: str | None = None, district: str | None = None) -> dict[str, Any]:
        states = [row[0] for row in db.execute(select(MarketState.name).where(MarketState.active.is_(True)).order_by(MarketState.name)).all()]

        district_query = select(func.distinct(MarketDistrict.name)).join(MarketState, MarketState.id == MarketDistrict.state_id)
        if state:
            district_query = district_query.where(MarketState.normalized_name == normalize_name(state))
        districts = [row[0] for row in db.execute(district_query.order_by(MarketDistrict.name)).all()]

        market_query = (
            select(func.distinct(Market.name))
            .join(MarketState, MarketState.id == Market.state_id)
            .join(MarketDistrict, MarketDistrict.id == Market.district_id)
        )
        price_query = select(MarketPrice)
        if state:
            normalized_state = normalize_name(state)
            market_query = market_query.where(MarketState.normalized_name == normalized_state)
            price_query = price_query.where(func.lower(MarketPrice.state) == normalized_state)
        if district:
            normalized_district = normalize_name(district)
            market_query = market_query.where(MarketDistrict.normalized_name == normalized_district)
            price_query = price_query.where(func.lower(MarketPrice.district) == normalized_district)

        markets = [row[0] for row in db.execute(market_query.order_by(Market.name)).all()]
        prices = list(db.scalars(price_query.order_by(MarketPrice.arrival_date.desc()).limit(1000)))
        latest_date = max((item.arrival_date for item in prices), default=None)
        return {
            "states": states,
            "districts": districts,
            "markets": sorted({item.market for item in prices}) if prices else markets,
            "commodities": sorted({item.commodity for item in prices}) or ["Potato"],
            "varieties": sorted({item.variety for item in prices}),
            "grades": sorted({item.grade for item in prices}),
            "selected_state": state,
            "selected_district": district,
            "source": self.UPSTREAM_SOURCE,
            "freshness": latest_date.isoformat() if latest_date else "unavailable",
        }

    def list_prices(self, db: Session, filters: dict[str, Any]) -> list[MarketPrice]:
        query = select(MarketPrice)
        query = self._apply_price_filters(query, filters)
        if filters.get("latest_only"):
            latest_date_query = select(func.max(MarketPrice.arrival_date))
            latest_date_query = self._apply_price_filters(latest_date_query, filters, include_latest=False)
            latest_date = db.scalar(latest_date_query)
            if latest_date is not None:
                query = query.where(MarketPrice.arrival_date == latest_date)
        limit = max(1, min(int(filters.get("limit", 50)), 200))
        offset = max(0, min(int(filters.get("offset", 0)), 10_000))
        return list(
            db.scalars(
                query.order_by(MarketPrice.arrival_date.desc(), MarketPrice.modal_price.desc()).limit(limit).offset(offset)
            )
        )

    def analytics(self, db: Session, filters: dict[str, Any]) -> dict[str, Any]:
        window_days = max(1, min(int(filters.get("window_days", 30)), 365))
        query = select(MarketPrice).where(MarketPrice.arrival_date >= date.today() - timedelta(days=window_days))
        query = self._apply_price_filters(query, filters)
        rows = list(db.scalars(query.order_by(MarketPrice.arrival_date.asc())))
        if not rows:
            return {
                "state": filters.get("state"),
                "district": filters.get("district"),
                "market": filters.get("market"),
                "commodity": filters.get("commodity") or "Potato",
                "variety": filters.get("variety"),
                "window_days": window_days,
                "summary": {
                    "record_count": 0,
                    "average_modal_price": None,
                    "minimum_price": None,
                    "maximum_price": None,
                    "latest_price": None,
                    "previous_price": None,
                    "change_amount": None,
                    "change_percent": 0.0,
                    "direction": "stable",
                },
                "trend": [],
                "source": self.UPSTREAM_SOURCE,
                "freshness": "unavailable",
                "note": "No historical market prices are available for the selected filters.",
            }

        grouped: dict[date, list[MarketPrice]] = {}
        for row in rows:
            grouped.setdefault(row.arrival_date, []).append(row)
        trend = []
        average_modal = sum(row.modal_price for row in rows) / len(rows)
        for arrival_date, items in sorted(grouped.items()):
            modal_values = [item.modal_price for item in items]
            min_values = [item.min_price for item in items]
            max_values = [item.max_price for item in items]
            trend.append(
                {
                    "date": arrival_date,
                    "min_price": round(min(min_values), 2),
                    "max_price": round(max(max_values), 2),
                    "modal_price": round(sum(modal_values) / len(modal_values), 2),
                    "average_price": round(sum(modal_values) / len(modal_values), 2),
                }
            )
        latest_price = trend[-1]["modal_price"]
        previous_price = trend[-2]["modal_price"] if len(trend) > 1 else None
        change_amount = latest_price - previous_price if previous_price is not None else None
        change_percent = round((change_amount / previous_price) * 100, 2) if previous_price else 0.0
        return {
            "state": filters.get("state"),
            "district": filters.get("district"),
            "market": filters.get("market"),
            "commodity": filters.get("commodity") or "Potato",
            "variety": filters.get("variety"),
            "window_days": window_days,
            "summary": {
                "record_count": len(rows),
                "average_modal_price": round(average_modal, 2),
                "minimum_price": round(min(row.min_price for row in rows), 2),
                "maximum_price": round(max(row.max_price for row in rows), 2),
                "latest_price": latest_price,
                "previous_price": previous_price,
                "change_amount": round(change_amount, 2) if change_amount is not None else None,
                "change_percent": change_percent,
                "direction": self._direction(change_percent),
            },
            "trend": trend,
            "source": self._source_note(rows),
            "freshness": max(row.arrival_date for row in rows).isoformat(),
            "note": None,
        }

    def forecast(self, db: Session, state: str = "Karnataka", horizon_days: int = 30) -> list[dict[str, Any]]:
        rows = self.historical_prices(db, state=state, days=120)
        if not rows:
            return []

        by_date: dict[date, list[float]] = {}
        for row in rows:
            by_date.setdefault(row.arrival_date, []).append(row.modal_price)
        dates = sorted(by_date)
        values = np.array([np.mean(by_date[d]) for d in dates], dtype=float)
        x = np.arange(len(values), dtype=float)

        if len(values) >= 8:
            coeff = np.polyfit(x, values, deg=1)
            trend = np.polyval(coeff, x)
            residual = values - trend
            weekday_effects = {
                idx: float(np.mean(residual[np.arange(len(values)) % 7 == idx]))
                for idx in range(7)
                if np.any(np.arange(len(values)) % 7 == idx)
            }
            sigma = max(35.0, float(np.std(residual)))
        else:
            coeff = np.array([0.0, float(np.mean(values))])
            weekday_effects = {}
            sigma = max(45.0, float(np.std(values)) if len(values) > 1 else 60.0)

        last_date = dates[-1]
        result: list[dict[str, Any]] = []
        for step in range(1, horizon_days + 1):
            xi = len(values) - 1 + step
            predicted = float(np.polyval(coeff, xi) + weekday_effects.get(xi % 7, 0.0))
            uncertainty = sigma * (1.0 + step / max(horizon_days, 1) * 0.35)
            result.append(
                {
                    "date": last_date + timedelta(days=step),
                    "predicted_price": round(max(0.0, predicted), 2),
                    "lower_bound": round(max(0.0, predicted - 1.28 * uncertainty), 2),
                    "upper_bound": round(predicted + 1.28 * uncertainty, 2),
                }
            )
        return result

    def latest_prices(self, db: Session, state: str = "Karnataka", limit: int = 12) -> list[MarketPrice]:
        latest_date = db.scalar(
            select(func.max(MarketPrice.arrival_date)).where(
                func.lower(MarketPrice.state) == normalize_name(state),
                MarketPrice.commodity == "Potato",
            )
        )
        if latest_date is None:
            return []
        return list(
            db.scalars(
                select(MarketPrice)
                .where(
                    func.lower(MarketPrice.state) == normalize_name(state),
                    MarketPrice.commodity == "Potato",
                    MarketPrice.arrival_date == latest_date,
                )
                .order_by(desc(MarketPrice.modal_price))
                .limit(limit)
            )
        )

    def historical_prices(self, db: Session, state: str = "Karnataka", days: int = 90) -> list[MarketPrice]:
        start = date.today() - timedelta(days=days)
        return list(
            db.scalars(
                select(MarketPrice)
                .where(
                    func.lower(MarketPrice.state) == normalize_name(state),
                    MarketPrice.commodity == "Potato",
                    MarketPrice.arrival_date >= start,
                )
                .order_by(MarketPrice.arrival_date)
            )
        )

    def overview(self, db: Session, state: str = "Karnataka") -> dict[str, Any]:
        prices = self.latest_prices(db, state=state)
        forecast = self.forecast(db, state=state, horizon_days=30)
        history = self.historical_prices(db, state=state, days=14)
        all_states = [item["name"] for item in self.list_states(db)]

        by_date: dict[date, list[float]] = {}
        for row in history:
            by_date.setdefault(row.arrival_date, []).append(row.modal_price)
        date_values = [(d, float(np.mean(v))) for d, v in sorted(by_date.items())]
        if len(date_values) >= 2 and date_values[0][1]:
            change = round((date_values[-1][1] - date_values[0][1]) / date_values[0][1] * 100, 2)
        else:
            change = 0.0

        latest_date = max((p.arrival_date for p in prices), default=None)
        top_markets = self._top_markets(prices, history)
        consolidated = {
            "date": latest_date,
            "active_mandis": len({item.market for item in prices}),
            "records": len(prices),
            "average_modal_price": round(sum(item.modal_price for item in prices) / len(prices), 2) if prices else None,
            "minimum_price": round(min((item.min_price for item in prices), default=0.0), 2) if prices else None,
            "maximum_price": round(max((item.max_price for item in prices), default=0.0), 2) if prices else None,
            "commodity": "Potato",
            "data_source": self._source_note(prices),
            "arrival_volume": None,
            "arrival_volume_note": "Arrival volume is unavailable from the current AGMARKNET response.",
            "change_percent_7d": change,
            "direction": self._direction(change),
        }
        return {
            "latest_prices": prices,
            "forecast": forecast,
            "price_direction": self._direction(change),
            "change_percent": change,
            "best_market": prices[0].market if prices else "No market data",
            "source_note": self._source_note(prices),
            "freshness": latest_date.isoformat() if latest_date else "unavailable",
            "consolidated": consolidated,
            "top_markets": top_markets,
            "live_data": any("data.gov.in" in item.source.lower() for item in prices),
            "states": all_states,
        }

    def sync_directory(self, db: Session, state: str | None = None) -> dict[str, Any]:
        received = self._sync_directory_from_prices(db, state=state)
        return {
            "state": state,
            "received": received,
            "inserted": received,
            "updated": 0,
            "mandi_count": self._count_markets(db, state),
            "live_data": self._has_live_prices(db, state),
            "source": self.UPSTREAM_SOURCE,
            "note": "Directory synchronized from stored market price records.",
        }

    def refresh_from_data_gov(self, db: Session, state: str | None = None, max_pages: int = 3, triggered_by: str | None = None) -> dict[str, Any]:
        sync_run = MarketSyncRun(source=self.UPSTREAM_SOURCE, state=state, status="running", triggered_by=triggered_by)
        db.add(sync_run)
        db.flush()
        try:
            records = self._fetch_upstream_records(state=state, max_pages=max_pages)
            inserted, updated = self._upsert_records(db, records)
            self._sync_directory_from_prices(db, state=state)
            sync_run.status = "completed"
            sync_run.records_received = len(records)
            sync_run.records_inserted = inserted
            sync_run.records_updated = updated
            sync_run.completed_at = utc_now()
            db.commit()
            return {
                "state": state,
                "received": len(records),
                "inserted": inserted,
                "updated": updated,
                "mandi_count": self._count_markets(db, state),
                "live_data": True,
                "source": self.UPSTREAM_SOURCE,
                "note": "Official market data refresh completed.",
            }
        except Exception as exc:
            db.rollback()
            with db.begin():
                sync_run.status = "failed"
                sync_run.completed_at = utc_now()
                sync_run.error_message = str(exc)
                db.add(sync_run)
            logger.exception("market_refresh_failed", extra={"state": state})
            raise

    def _fetch_upstream_records(self, state: str | None, max_pages: int) -> list[UpstreamRecord]:
        if not self.settings.data_gov_api_key:
            raise ValueError("DATA_GOV_API_KEY is not configured.")

        max_pages = max(1, min(max_pages, self.settings.market_max_pages))
        url = f"{self.DATA_GOV_BASE}/{self.settings.data_gov_resource_id}"
        parsed = urlparse(url)
        if parsed.hostname != self.allowed_upstream_host:
            raise ValueError("Unexpected upstream host.")

        records: list[UpstreamRecord] = []
        offset = 0
        for _ in range(max_pages):
            params: dict[str, Any] = {
                "api-key": self.settings.data_gov_api_key,
                "format": "json",
                "limit": self.settings.market_page_size,
                "offset": offset,
                "filters[commodity]": "Potato",
            }
            if state:
                params["filters[state]"] = state
            payload = self._request_with_retry(url, params=params)
            page_records = payload.get("records", [])
            if not isinstance(page_records, list):
                raise ValueError("Malformed upstream response: 'records' is not a list.")
            parsed_page = [self._parse_upstream_record(item) for item in page_records]
            parsed_page = [item for item in parsed_page if item is not None]
            records.extend(parsed_page)
            if len(page_records) < self.settings.market_page_size:
                break
            offset += self.settings.market_page_size
        return records

    def _request_with_retry(self, url: str, *, params: dict[str, Any]) -> dict[str, Any]:
        last_error: Exception | None = None
        for attempt in range(self.settings.market_retry_attempts):
            try:
                with httpx.Client(
                    timeout=httpx.Timeout(connect=self.settings.market_connect_timeout, read=self.settings.market_read_timeout),
                    follow_redirects=False,
                ) as client:
                    response = client.get(url, params=params, headers={"Accept": "application/json"})
                    response.raise_for_status()
                    payload = response.json()
                    if not isinstance(payload, dict):
                        raise ValueError("Malformed upstream response body.")
                    return payload
            except Exception as exc:
                last_error = exc
                if attempt == self.settings.market_retry_attempts - 1:
                    break
                time.sleep(min(2**attempt, 8))
        assert last_error is not None
        raise last_error

    def _parse_upstream_record(self, item: Any) -> UpstreamRecord | None:
        if not isinstance(item, dict):
            return None
        try:
            arrival = datetime.strptime(str(item["arrival_date"]), "%d/%m/%Y").date()
            min_price = float(item.get("min_price", 0) or 0)
            max_price = float(item.get("max_price", 0) or 0)
            modal_price = float(item.get("modal_price", 0) or 0)
        except (KeyError, TypeError, ValueError):
            return None
        if min_price < 0 or max_price < 0 or modal_price < 0:
            return None
        return UpstreamRecord(
            state=title_name(item.get("state")),
            district=title_name(item.get("district")),
            market=title_name(item.get("market")),
            commodity=title_name(item.get("commodity"), "Potato"),
            variety=title_name(item.get("variety"), "Local"),
            grade=title_name(item.get("grade"), "FAQ"),
            arrival_date=arrival,
            min_price=min_price,
            max_price=max_price,
            modal_price=modal_price,
            source=self.UPSTREAM_SOURCE,
            source_record_id=str(item.get("_id")) if item.get("_id") is not None else None,
        )

    def _upsert_records(self, db: Session, records: Iterable[UpstreamRecord]) -> tuple[int, int]:
        inserted = 0
        updated = 0
        for record in records:
            market = self._upsert_market_directory_entry(db, state_name=record.state, district_name=record.district, market_name=record.market)
            existing = db.scalar(
                select(MarketPrice).where(
                    MarketPrice.market_id == market.id,
                    MarketPrice.commodity == record.commodity,
                    MarketPrice.variety == record.variety,
                    MarketPrice.grade == record.grade,
                    MarketPrice.arrival_date == record.arrival_date,
                    MarketPrice.source == record.source,
                )
            )
            if existing:
                existing.min_price = record.min_price
                existing.max_price = record.max_price
                existing.modal_price = record.modal_price
                existing.fetched_at = utc_now()
                existing.source_record_id = record.source_record_id
                updated += 1
                continue
            db.add(
                MarketPrice(
                    market_id=market.id,
                    state=record.state,
                    district=record.district,
                    market=record.market,
                    commodity=record.commodity,
                    variety=record.variety,
                    grade=record.grade,
                    arrival_date=record.arrival_date,
                    min_price=record.min_price,
                    max_price=record.max_price,
                    modal_price=record.modal_price,
                    source=record.source,
                    source_record_id=record.source_record_id,
                )
            )
            inserted += 1
        db.flush()
        return inserted, updated

    def _upsert_market_directory_entry(self, db: Session, *, state_name: str, district_name: str, market_name: str) -> Market:
        state = self._get_or_create_state(db, state_name)
        district = self._get_or_create_district(db, state, district_name)
        market = db.scalar(
            select(Market).where(
                Market.state_id == state.id,
                Market.district_id == district.id,
                Market.normalized_name == normalize_name(market_name),
            )
        )
        if market:
            return market
        market = Market(
            state_id=state.id,
            district_id=district.id,
            name=title_name(market_name),
            normalized_name=normalize_name(market_name),
            external_market_name=title_name(market_name),
            source=self.UPSTREAM_SOURCE,
            active=True,
        )
        db.add(market)
        db.flush()
        return market

    def _get_or_create_state(self, db: Session, state_name: str) -> MarketState:
        normalized = normalize_name(state_name)
        state = db.scalar(select(MarketState).where(MarketState.normalized_name == normalized))
        if state:
            return state
        state = MarketState(name=title_name(state_name), normalized_name=normalized, active=True)
        db.add(state)
        db.flush()
        return state

    def _get_or_create_district(self, db: Session, state: MarketState, district_name: str) -> MarketDistrict:
        normalized = normalize_name(district_name)
        district = db.scalar(
            select(MarketDistrict).where(MarketDistrict.state_id == state.id, MarketDistrict.normalized_name == normalized)
        )
        if district:
            return district
        district = MarketDistrict(state_id=state.id, name=title_name(district_name), normalized_name=normalized, active=True)
        db.add(district)
        db.flush()
        return district

    def _sync_directory_from_prices(self, db: Session, state: str | None = None) -> int:
        query = select(MarketPrice.state, MarketPrice.district, MarketPrice.market).distinct()
        if state:
            query = query.where(func.lower(MarketPrice.state) == normalize_name(state))
        received = 0
        for state_name, district_name, market_name in db.execute(query).all():
            self._upsert_market_directory_entry(
                db,
                state_name=title_name(state_name),
                district_name=title_name(district_name),
                market_name=title_name(market_name),
            )
            received += 1
        db.commit()
        return received

    def _apply_price_filters(self, query: Select[Any], filters: dict[str, Any], *, include_latest: bool = True) -> Select[Any]:
        state = filters.get("state")
        district = filters.get("district")
        market = filters.get("market")
        commodity = filters.get("commodity")
        variety = filters.get("variety")
        grade = filters.get("grade")
        date_from = filters.get("date_from")
        date_to = filters.get("date_to")
        clauses = []
        if state:
            clauses.append(func.lower(MarketPrice.state) == normalize_name(state))
        if district:
            clauses.append(func.lower(MarketPrice.district) == normalize_name(district))
        if market:
            clauses.append(func.lower(MarketPrice.market) == normalize_name(market))
        if commodity:
            clauses.append(func.lower(MarketPrice.commodity) == normalize_name(commodity))
        if variety:
            clauses.append(func.lower(MarketPrice.variety) == normalize_name(variety))
        if grade:
            clauses.append(func.lower(MarketPrice.grade) == normalize_name(grade))
        if date_from:
            clauses.append(MarketPrice.arrival_date >= date_from)
        if date_to:
            clauses.append(MarketPrice.arrival_date <= date_to)
        if clauses:
            query = query.where(and_(*clauses))
        return query

    def _require_state(self, db: Session, state: str) -> MarketState:
        state_row = db.scalar(select(MarketState).where(MarketState.normalized_name == normalize_name(state)))
        if not state_row:
            raise ValueError(f"Unknown state: {state}")
        return state_row

    def _source_note(self, prices: Iterable[MarketPrice]) -> str:
        values = sorted({item.source for item in prices})
        return ", ".join(values) if values else "No source"

    def _top_markets(self, latest_prices: list[MarketPrice], history: list[MarketPrice]) -> list[dict[str, Any]]:
        prior_by_market: dict[tuple[str, str, str], float] = {}
        if history:
            historical_groups: dict[tuple[str, str, str], list[MarketPrice]] = {}
            for item in history:
                historical_groups.setdefault((item.state, item.district, item.market), []).append(item)
            for key, items in historical_groups.items():
                items = sorted(items, key=lambda row: row.arrival_date)
                if len(items) > 1:
                    prior_by_market[key] = items[-2].modal_price
        results = []
        for index, item in enumerate(latest_prices[:10], start=1):
            previous = prior_by_market.get((item.state, item.district, item.market))
            change_percent = round(((item.modal_price - previous) / previous) * 100, 2) if previous else None
            results.append(
                {
                    "market_id": item.market_id,
                    "state": item.state,
                    "district": item.district,
                    "market": item.market,
                    "modal_price": item.modal_price,
                    "arrival_date": item.arrival_date,
                    "variety": item.variety,
                    "source": item.source,
                    "rank": index,
                    "change_percent": change_percent,
                }
            )
        return results

    def _count_markets(self, db: Session, state: str | None) -> int:
        query = select(func.count(Market.id))
        if state:
            query = query.join(MarketState, MarketState.id == Market.state_id).where(
                MarketState.normalized_name == normalize_name(state)
            )
        return int(db.scalar(query) or 0)

    def _has_live_prices(self, db: Session, state: str | None) -> bool:
        query = select(MarketPrice.id).where(func.lower(MarketPrice.source).like("%data.gov.in%"))
        if state:
            query = query.where(func.lower(MarketPrice.state) == normalize_name(state))
        return db.scalar(query.limit(1)) is not None

    @staticmethod
    def _direction(change_percent: float) -> str:
        if change_percent > 1:
            return "rising"
        if change_percent < -1:
            return "falling"
        return "stable"
