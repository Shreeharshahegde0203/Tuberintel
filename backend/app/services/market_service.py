from __future__ import annotations

from collections import defaultdict
import json
from pathlib import Path
from datetime import date, datetime, timedelta, timezone
from statistics import median
from zoneinfo import ZoneInfo
from typing import Any, Iterable

import httpx
import numpy as np
from sqlalchemy import and_, desc, func, or_, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import MandiDirectory, MarketPrice, MarketState, MarketSyncRun
from app.schemas.market import StoragePlanRequest, TransportPlanRequest
from app.services.forecasting import ForecastEngine
from app.services.forecasting.persistence import persist_forecast_snapshot


class MarketService:
    """Official mandi-price ingestion plus transparent, auditable analytics.

    The public AGMARKNET resource supplies state, district, market, commodity,
    variety, grade, date, and minimum/maximum/modal prices. It does not expose
    physical arrival volume in the same resource, so the service never invents
    an arrivals number.
    """

    DATA_GOV_BASE = "https://api.data.gov.in/resource"

    def __init__(self) -> None:
        self.settings = get_settings()
        self.forecast_engine = ForecastEngine(
            self.settings.price_forecast_model_path,
            max_horizon_days=self.settings.price_forecast_max_horizon_days,
            min_history_days=self.settings.price_forecast_min_history_days,
            interval_level=self.settings.price_forecast_interval_level,
        )

    @staticmethod
    def _clean(value: Any, default: str) -> str:
        text = str(value or "").strip()
        return text or default

    @staticmethod
    def _parse_date(value: Any) -> date | None:
        if not value:
            return None
        text = str(value).strip()
        for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
            try:
                return datetime.strptime(text, fmt).date()
            except ValueError:
                continue
        return None

    @staticmethod
    def _price(value: Any) -> float:
        try:
            parsed = float(str(value).replace(",", "").strip())
        except (TypeError, ValueError):
            return 0.0
        return parsed if parsed >= 0 else 0.0

    STATE_ALIASES = {
        "orissa": "Odisha",
        "uttaranchal": "Uttarakhand",
        "pondicherry": "Puducherry",
        "nct of delhi": "Delhi",
        "national capital territory of delhi": "Delhi",
        "jammu & kashmir": "Jammu and Kashmir",
        "andaman & nicobar islands": "Andaman and Nicobar Islands",
        "dadra and nagar haveli": "Dadra and Nagar Haveli and Daman and Diu",
        "daman and diu": "Dadra and Nagar Haveli and Daman and Diu",
    }

    @classmethod
    def _state_catalog(cls) -> list[dict[str, str]]:
        path = Path(__file__).resolve().parents[1] / "data" / "india_states.json"
        return json.loads(path.read_text(encoding="utf-8"))

    @classmethod
    def canonical_state_name(cls, value: Any) -> str:
        raw = cls._clean(value, "Unknown")
        alias = cls.STATE_ALIASES.get(raw.casefold())
        if alias:
            return alias
        catalog = cls._state_catalog()
        for item in catalog:
            if item["name"].casefold() == raw.casefold():
                return item["name"]
        return raw

    def seed_state_directory(self, db: Session) -> int:
        # TUBERINTEL LEGACY STATE SEED FIX V1
        from app.services.state_seed_compat import seed_state_directory
        return seed_state_directory(db, MarketState, self._state_catalog())

    def _ensure_state(self, db: Session, state_name: str) -> MarketState:
        canonical = self.canonical_state_name(state_name)
        row = db.scalar(select(MarketState).where(func.lower(MarketState.name) == canonical.lower()))
        if row:
            return row
        code = "X" + str(abs(hash(canonical)) % 1000).zfill(3)
        row = MarketState(code=code, name=canonical, state_type="Other", source="AGMARKNET response")
        db.add(row)
        db.flush()
        return row

    def _upsert_mandi(
        self,
        db: Session,
        *,
        state: str,
        district: str,
        market: str,
        source: str,
        seen_at: datetime | None = None,
    ) -> tuple[MandiDirectory, bool]:
        state_row = self._ensure_state(db, state)
        district_value = self._clean(district, "Unspecified district")
        market_value = self._clean(market, "Unknown market")
        row = db.scalar(
            select(MandiDirectory).where(
                MandiDirectory.state_id == state_row.id,
                func.lower(MandiDirectory.district) == district_value.lower(),
                func.lower(MandiDirectory.market) == market_value.lower(),
            )
        )
        now = seen_at or datetime.now(timezone.utc)
        if row:
            row.district = district_value
            row.market = market_value
            row.source = source
            row.active = True
            row.last_seen_at = now
            return row, False
        row = MandiDirectory(
            state_id=state_row.id,
            district=district_value,
            market=market_value,
            source=source,
            active=True,
            last_seen_at=now,
        )
        db.add(row)
        return row, True

    def bootstrap_directory_from_prices(self, db: Session) -> int:
        self.seed_state_directory(db)
        inserted = 0
        locations = db.execute(
            select(MarketPrice.state, MarketPrice.district, MarketPrice.market, func.max(MarketPrice.fetched_at))
            .group_by(MarketPrice.state, MarketPrice.district, MarketPrice.market)
        ).all()
        for state, district, market, fetched_at in locations:
            _, created = self._upsert_mandi(
                db,
                state=state,
                district=district,
                market=market,
                source="market price history",
                seen_at=fetched_at,
            )
            inserted += int(created)
        db.commit()
        return inserted

    def directory_states(self, db: Session) -> list[dict[str, Any]]:
        self.seed_state_directory(db)
        db.commit()
        counts = {
            state_id: count
            for state_id, count in db.execute(
                select(MandiDirectory.state_id, func.count(MandiDirectory.id))
                .where(MandiDirectory.active.is_(True))
                .group_by(MandiDirectory.state_id)
            ).all()
        }
        rows = list(db.scalars(select(MarketState).where(MarketState.active.is_(True)).order_by(MarketState.name)))
        return [
            {
                "code": row.code,
                "name": row.name,
                "type": row.state_type,
                "mandi_count": int(counts.get(row.id, 0)),
            }
            for row in rows
        ]

    def mandi_directory(
        self,
        db: Session,
        *,
        state: str,
        district: str | None = None,
        search: str | None = None,
        limit: int = 2500,
    ) -> dict[str, Any]:
        canonical = self.canonical_state_name(state)
        state_row = db.scalar(select(MarketState).where(func.lower(MarketState.name) == canonical.lower()))
        if not state_row:
            self.seed_state_directory(db)
            db.commit()
            state_row = db.scalar(select(MarketState).where(func.lower(MarketState.name) == canonical.lower()))
        conditions: list[Any] = [MandiDirectory.active.is_(True)]
        if state_row:
            conditions.append(MandiDirectory.state_id == state_row.id)
        else:
            return {
                "state": canonical, "districts": [], "mandis": [], "count": 0,
                "source": "database", "last_synced_at": None,
                "api_configured": bool(self.settings.data_gov_api_key),
            }
        if district:
            conditions.append(func.lower(MandiDirectory.district) == district.lower())
        if search:
            term = f"%{search.strip().lower()}%"
            conditions.append(or_(func.lower(MandiDirectory.market).like(term), func.lower(MandiDirectory.district).like(term)))
        rows = list(
            db.scalars(
                select(MandiDirectory)
                .where(*conditions)
                .order_by(MandiDirectory.district, MandiDirectory.market)
                .limit(min(max(limit, 1), 5000))
            )
        )
        districts = list(
            db.scalars(
                select(MandiDirectory.district)
                .where(MandiDirectory.state_id == state_row.id, MandiDirectory.active.is_(True))
                .distinct()
                .order_by(MandiDirectory.district)
            )
        )
        last_synced = db.scalar(
            select(func.max(MandiDirectory.last_seen_at)).where(MandiDirectory.state_id == state_row.id)
        )
        real_locations = set(db.execute(select(MarketPrice.district, MarketPrice.market)
            .where(*self._conditions(state=canonical))).all())
        rows = [row for row in rows if (row.district, row.market) in real_locations
                or ("data.gov.in" in row.source.lower() and "seed" not in row.source.lower())]
        districts = sorted({row.district for row in rows})
        sources = sorted({row.source for row in rows})
        return {
            "state": state_row.name,
            "districts": [str(item) for item in districts if item],
            "mandis": [
                {
                    "id": row.id,
                    "state": state_row.name,
                    "district": row.district,
                    "market": row.market,
                    "source": row.source,
                    "is_enam": row.is_enam,
                    "last_seen_at": row.last_seen_at,
                }
                for row in rows
            ],
            "count": len(rows),
            "source": ", ".join(sources) if sources else "database",
            "last_synced_at": last_synced,
            "api_configured": bool(self.settings.data_gov_api_key),
        }

    def sync_mandi_directory(
        self,
        db: Session,
        *,
        state: str,
        max_pages: int | None = None,
    ) -> dict[str, Any]:
        """Synchronise a state's reporting mandis into the database.

        The source resource is the official current-daily AGMARKNET feed. The
        sync deliberately omits a commodity filter so every market reporting
        any commodity for the selected state can be discovered. Repeated runs
        accumulate the directory instead of replacing it, which protects
        markets that do not report on a particular day.
        """
        canonical = self.canonical_state_name(state)
        self.seed_state_directory(db)
        state_row = db.scalar(select(MarketState).where(func.lower(MarketState.name) == canonical.lower()))
        if state_row is None:
            state_row = self._ensure_state(db, canonical)
        db.commit()

        if not self.settings.data_gov_api_key:
            return {
                "state": canonical,
                "received": 0,
                "inserted": 0,
                "updated": 0,
                "mandi_count": self.mandi_directory(db, state=canonical)["count"],
                "live_data": False,
                "source": "database",
                "note": "DATA_GOV_API_KEY is not configured. The complete state list is available, but the official reporting-mandi directory has not been synchronized.",
            }

        run = MarketSyncRun(
            source="data.gov.in / AGMARKNET mandi directory",
            resource_id=self.settings.data_gov_resource_id,
            state=canonical,
            status="running",
        )
        db.add(run)
        db.commit()
        db.refresh(run)

        # Load the state's current directory once. This avoids one database
        # query per source record during large state synchronisations.
        existing_rows = list(
            db.scalars(select(MandiDirectory).where(MandiDirectory.state_id == state_row.id))
        )
        existing: dict[tuple[str, str], MandiDirectory] = {
            (row.district.casefold(), row.market.casefold()): row for row in existing_rows
        }

        page_size = min(max(1, self.settings.market_page_size), 1000)
        page_limit = max_pages or self.settings.market_directory_max_pages
        params_base: dict[str, Any] = {
            "api-key": self.settings.data_gov_api_key,
            "format": "json",
            "limit": page_size,
            "filters[state]": canonical,
        }
        url = f"{self.DATA_GOV_BASE}/{self.settings.data_gov_resource_id}"
        received = inserted = updated = 0
        seen: set[tuple[str, str]] = set()
        try:
            with httpx.Client(timeout=35.0, follow_redirects=True) as client:
                for page in range(page_limit):
                    response = client.get(url, params={**params_base, "offset": page * page_size})
                    response.raise_for_status()
                    records = response.json().get("records") or []
                    if not isinstance(records, list):
                        raise ValueError("Unexpected data.gov.in response: records is not a list")
                    received += len(records)
                    now = datetime.now(timezone.utc)
                    for record in records:
                        district_value = self._clean(record.get("district"), "Unspecified district")
                        market_value = self._clean(record.get("market"), "Unknown market")
                        identity = (district_value.casefold(), market_value.casefold())
                        if identity in seen:
                            continue
                        seen.add(identity)
                        row = existing.get(identity)
                        if row is None:
                            row = MandiDirectory(
                                state_id=state_row.id,
                                district=district_value,
                                market=market_value,
                                source="data.gov.in / AGMARKNET reporting mandi directory",
                                active=True,
                                last_seen_at=now,
                            )
                            db.add(row)
                            existing[identity] = row
                            inserted += 1
                        else:
                            row.district = district_value
                            row.market = market_value
                            row.source = "data.gov.in / AGMARKNET reporting mandi directory"
                            row.active = True
                            row.last_seen_at = now
                            updated += 1
                    db.commit()
                    if len(records) < page_size:
                        break

            run.status = "completed"
            run.records_received = received
            run.records_inserted = inserted
            run.records_updated = updated
            run.finished_at = datetime.now(timezone.utc)
            db.commit()
            directory = self.mandi_directory(db, state=canonical)
            return {
                "state": canonical,
                "received": received,
                "inserted": inserted,
                "updated": updated,
                "mandi_count": directory["count"],
                "live_data": True,
                "source": "data.gov.in / AGMARKNET",
                "note": "Official reporting mandis were synchronized and stored in the database. The directory is accumulated across syncs and is not a fabricated frontend list.",
                "sync_run_id": run.id,
            }
        except Exception as exc:
            run.status = "failed"
            run.error = str(exc)[:3000]
            run.records_received = received
            run.records_inserted = inserted
            run.records_updated = updated
            run.finished_at = datetime.now(timezone.utc)
            db.commit()
            raise

    def refresh_from_data_gov(
        self,
        db: Session,
        state: str | None = None,
        district: str | None = None,
        max_pages: int | None = None,
    ) -> dict[str, Any]:
        if not self.settings.data_gov_api_key:
            return {
                "updated": 0,
                "inserted": 0,
                "received": 0,
                "source": "database",
                "live_data": False,
                "note": "DATA_GOV_API_KEY is not configured. Existing database records remain available.",
            }

        run = MarketSyncRun(
            source="data.gov.in / AGMARKNET",
            resource_id=self.settings.data_gov_resource_id,
            state=state,
            status="running",
        )
        db.add(run)
        db.commit()
        db.refresh(run)

        page_size = min(max(1, self.settings.market_page_size), 1000)
        page_limit = max_pages or self.settings.market_max_pages
        base_params: dict[str, Any] = {
            "api-key": self.settings.data_gov_api_key,
            "format": "json",
            "limit": page_size,
            "filters[commodity]": "Potato",
        }
        if state:
            base_params["filters[state]"] = state
        if district:
            base_params["filters[district]"] = district

        url = f"{self.DATA_GOV_BASE}/{self.settings.data_gov_resource_id}"
        received = inserted = updated = 0
        try:
            with httpx.Client(timeout=35.0, follow_redirects=True) as client:
                for page in range(page_limit):
                    params = {**base_params, "offset": page * page_size}
                    response = client.get(url, params=params)
                    response.raise_for_status()
                    payload = response.json()
                    records = payload.get("records") or []
                    if not isinstance(records, list):
                        raise ValueError("Unexpected data.gov.in response: records is not a list")
                    received += len(records)

                    for record in records:
                        arrival = self._parse_date(record.get("arrival_date"))
                        if not arrival:
                            continue
                        state_value = self._clean(record.get("state"), state or "Unknown")
                        district_value = self._clean(record.get("district"), district or "Unknown")
                        market_value = self._clean(record.get("market"), "Unknown")
                        self._upsert_mandi(
                            db,
                            state=state_value,
                            district=district_value,
                            market=market_value,
                            source="data.gov.in / AGMARKNET reporting mandi directory",
                        )
                        commodity_value = self._clean(record.get("commodity"), "Potato")
                        variety_value = self._clean(record.get("variety"), "Local")
                        grade_value = self._clean(record.get("grade"), "FAQ")
                        key_filter = and_(
                            MarketPrice.state == state_value,
                            MarketPrice.district == district_value,
                            MarketPrice.market == market_value,
                            MarketPrice.commodity == commodity_value,
                            MarketPrice.variety == variety_value,
                            MarketPrice.grade == grade_value,
                            MarketPrice.arrival_date == arrival,
                        )
                        row = db.scalar(select(MarketPrice).where(key_filter))
                        values = {
                            "min_price": self._price(record.get("min_price")),
                            "max_price": self._price(record.get("max_price")),
                            "modal_price": self._price(record.get("modal_price")),
                            "source": "data.gov.in / AGMARKNET",
                            "fetched_at": datetime.now(timezone.utc),
                        }
                        if row:
                            changed = any(abs(float(getattr(row, key)) - float(value)) > 0.001 for key, value in values.items() if key.endswith("price"))
                            for key, value in values.items():
                                setattr(row, key, value)
                            updated += 1 if changed else 0
                        else:
                            db.add(
                                MarketPrice(
                                    state=state_value,
                                    district=district_value,
                                    market=market_value,
                                    commodity=commodity_value,
                                    variety=variety_value,
                                    grade=grade_value,
                                    arrival_date=arrival,
                                    **values,
                                )
                            )
                            inserted += 1
                    db.commit()
                    if len(records) < page_size:
                        break

            run.status = "completed"
            run.records_received = received
            run.records_inserted = inserted
            run.records_updated = updated
            run.finished_at = datetime.now(timezone.utc)
            db.commit()
            return {
                "updated": updated,
                "inserted": inserted,
                "received": received,
                "source": "data.gov.in / AGMARKNET",
                "live_data": True,
                "note": "Official potato mandi prices refreshed and persisted for historical analytics.",
                "sync_run_id": run.id,
            }
        except Exception as exc:
            run.status = "failed"
            run.error = str(exc)[:3000]
            run.records_received = received
            run.records_inserted = inserted
            run.records_updated = updated
            run.finished_at = datetime.now(timezone.utc)
            db.commit()
            raise

    @staticmethod
    def _conditions(
        *,
        state: str | None = None,
        district: str | None = None,
        market: str | None = None,
        variety: str | None = None,
        grade: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> list[Any]:
        conditions: list[Any] = [
            MarketPrice.commodity == "Potato",
            ~func.lower(func.coalesce(MarketPrice.source, "")).like("%seeded%"),
            ~func.lower(func.coalesce(MarketPrice.source, "")).like("%demo%"),
            ~func.lower(MarketPrice.market).like("%binny%"),
        ]
        if state:
            conditions.append(MarketPrice.state == state)
        if district:
            conditions.append(MarketPrice.district == district)
        if market:
            conditions.append(MarketPrice.market == market)
        if variety:
            conditions.append(MarketPrice.variety == variety)
        if grade:
            conditions.append(MarketPrice.grade == grade)
        if date_from:
            conditions.append(MarketPrice.arrival_date >= date_from)
        if date_to:
            conditions.append(MarketPrice.arrival_date <= date_to)
        return conditions

    def list_prices(
        self,
        db: Session,
        *,
        state: str | None = None,
        district: str | None = None,
        market: str | None = None,
        variety: str | None = None,
        grade: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        latest_only: bool = False,
        limit: int = 250,
        offset: int = 0,
    ) -> list[MarketPrice]:
        conditions = self._conditions(
            state=state,
            district=district,
            market=market,
            variety=variety,
            grade=grade,
            date_from=date_from,
            date_to=date_to,
        )
        if latest_only:
            latest_date = db.scalar(select(func.max(MarketPrice.arrival_date)).where(*conditions))
            if latest_date:
                conditions.append(MarketPrice.arrival_date == latest_date)
        query = (
            select(MarketPrice)
            .where(*conditions)
            .order_by(MarketPrice.arrival_date.desc(), MarketPrice.modal_price.desc(), MarketPrice.market)
            .offset(offset)
            .limit(min(max(limit, 1), 1000))
        )
        return list(db.scalars(query))

    def filters(self, db: Session, state: str | None = None) -> dict[str, Any]:
        self.seed_state_directory(db)
        canonical = self.canonical_state_name(state) if state else None
        price_conditions = self._conditions()
        if canonical:
            price_conditions.append(MarketPrice.state == canonical)

        def price_values(column: Any) -> list[str]:
            return [str(v) for v in db.scalars(select(column).where(*price_conditions).distinct().order_by(column)) if v]

        states = [item["name"] for item in self.directory_states(db)]
        directory = self.mandi_directory(db, state=canonical) if canonical else None
        return {
            "states": states,
            "districts": price_values(MarketPrice.district),
            "markets": price_values(MarketPrice.market),
            "varieties": price_values(MarketPrice.variety),
            "grades": price_values(MarketPrice.grade),
            "latest_date": db.scalar(select(func.max(MarketPrice.arrival_date)).where(*price_conditions)),
        }

    def analysis_market_inputs(self, db: Session, batch: Any) -> tuple[list[MarketPrice], list[dict], dict]:
        """Build a dated market snapshot for this inspection's selected market."""
        today = datetime.now(ZoneInfo("Asia/Kolkata")).date()
        earliest = today - timedelta(days=self.settings.analysis_market_max_age_days)
        variety = batch.variety
        if (variety or "").strip().casefold() in {"", "unspecified", "not specified", "local"}:
            variety = None
        scope = {
            "state": batch.state,
            "market": batch.intended_market,
            "district": None if batch.intended_market else batch.district,
            "variety": variety,
        }
        prices = self.list_prices(db, **scope, date_to=today, latest_only=True)
        prices = [row for row in prices if row.modal_price > 0]
        latest_date = prices[0].arrival_date if prices else None
        current = latest_date is not None and latest_date >= earliest
        forecast = []
        if current:
            forecast = self.forecast_detailed(
                db, **scope, horizon_days=self.settings.price_forecast_max_horizon_days,
                persist=True, as_of=today,
            )["points"]
            forecast = [
                {**point, "horizon_days": (point["date"] - today).days}
                for point in forecast if point["date"] > today
            ]
        snapshot = {
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
            "reporting_date": latest_date.isoformat() if latest_date else None,
            "status": "recent" if current else "stale" if latest_date else "unavailable",
            "max_age_days": self.settings.analysis_market_max_age_days,
        }
        return prices if current else [], forecast, snapshot

    def latest_prices(self, db: Session, state: str = "Karnataka", limit: int = 12) -> list[MarketPrice]:
        return self.list_prices(db, state=state, latest_only=True, limit=limit)

    def historical_prices(
        self,
        db: Session,
        state: str = "Karnataka",
        days: int = 90,
        district: str | None = None,
        market: str | None = None,
        variety: str | None = None,
    ) -> list[MarketPrice]:
        latest_date = db.scalar(
            select(func.max(MarketPrice.arrival_date)).where(
                *self._conditions(state=state, district=district, market=market, variety=variety)
            )
        )
        if not latest_date:
            return []
        start = latest_date - timedelta(days=max(days - 1, 0))
        conditions = self._conditions(
            state=state, district=district, market=market, variety=variety, date_from=start, date_to=latest_date
        )
        query = (
            select(MarketPrice)
            .where(*conditions)
            .order_by(MarketPrice.arrival_date, MarketPrice.modal_price, MarketPrice.market)
            .limit(20000)
        )
        return list(db.scalars(query))

    @staticmethod
    def _daily(rows: Iterable[MarketPrice]) -> list[tuple[date, float, float, float, int]]:
        grouped: dict[date, list[MarketPrice]] = defaultdict(list)
        for row in rows:
            grouped[row.arrival_date].append(row)
        output: list[tuple[date, float, float, float, int]] = []
        for day in sorted(grouped):
            day_rows = grouped[day]
            modal = [r.modal_price for r in day_rows if r.modal_price > 0]
            minimum = [r.min_price for r in day_rows if r.min_price > 0]
            maximum = [r.max_price for r in day_rows if r.max_price > 0]
            if not modal:
                continue
            output.append(
                (
                    day,
                    float(np.mean(modal)),
                    float(min(minimum or modal)),
                    float(max(maximum or modal)),
                    len({r.market for r in day_rows}),
                )
            )
        return output

    @staticmethod
    def _change(values: list[float], lookback: int) -> float:
        if len(values) < 2 or values[-1] == 0:
            return 0.0
        reference_index = max(0, len(values) - 1 - lookback)
        reference = values[reference_index]
        return round((values[-1] - reference) / reference * 100, 2) if reference else 0.0

    def _forecast_history_rows(
        self,
        db: Session,
        *,
        state: str,
        district: str | None = None,
        market: str | None = None,
        variety: str | None = None,
        as_of: date | None = None,
    ) -> list[MarketPrice]:
        conditions = self._conditions(
            state=state, district=district, market=market, variety=variety, date_to=as_of
        )
        latest_date = db.scalar(select(func.max(MarketPrice.arrival_date)).where(*conditions))
        if not latest_date:
            return []
        start_date = latest_date - timedelta(days=max(self.settings.price_forecast_history_days - 1, 0))
        query = (
            select(MarketPrice)
            .where(*conditions, MarketPrice.arrival_date >= start_date, MarketPrice.arrival_date <= latest_date)
            .order_by(MarketPrice.arrival_date, MarketPrice.market, MarketPrice.variety, MarketPrice.grade)
            .limit(50000)
        )
        return list(db.scalars(query))

    def forecast_detailed(
        self,
        db: Session,
        state: str = "Karnataka",
        horizon_days: int = 30,
        district: str | None = None,
        market: str | None = None,
        variety: str | None = None,
        persist: bool = False,
        as_of: date | None = None,
    ) -> dict[str, Any]:
        """Return an operational price forecast with provenance and diagnostics.

        Numeric forecasts are intentionally restricted to at most 30 days.
        Longer-horizon planning should use seasonal outlook/scenario analysis,
        not a false-precision daily price curve.
        """
        requested = int(horizon_days)
        if requested < 1 or requested > self.settings.price_forecast_max_horizon_days:
            raise ValueError(
                f"Operational numeric forecasts support 1-{self.settings.price_forecast_max_horizon_days} days only"
            )
        rows = self._forecast_history_rows(
            db, state=state, district=district, market=market, variety=variety, as_of=as_of
        )
        result = self.forecast_engine.forecast(rows, requested)
        if persist and result.points:
            persist_forecast_snapshot(
                db,
                result=result,
                state=state,
                district=district,
                market=market,
                variety=variety,
            )
        payload = result.as_dict()
        payload.update({
            "state": state,
            "district": district,
            "market": market,
            "variety": variety,
            "horizon_days": requested,
        })
        return payload

    def forecast(
        self,
        db: Session,
        state: str = "Karnataka",
        horizon_days: int = 30,
        district: str | None = None,
        market: str | None = None,
        variety: str | None = None,
    ) -> list[dict[str, Any]]:
        return self.forecast_detailed(
            db,
            state=state,
            horizon_days=min(horizon_days, self.settings.price_forecast_max_horizon_days),
            district=district,
            market=market,
            variety=variety,
        )["points"]

    def outlook(
        self,
        db: Session,
        *,
        state: str = "Karnataka",
        horizon_days: int = 60,
        district: str | None = None,
        market: str | None = None,
        variety: str | None = None,
    ) -> dict[str, Any]:
        if horizon_days < 31 or horizon_days > 90:
            raise ValueError("Seasonal outlook supports horizons from 31 to 90 days")
        rows = self.historical_prices(
            db, state=state, days=365, district=district, market=market, variety=variety
        )
        daily = self._daily(rows)
        values = [point[1] for point in daily]
        if len(values) < 30:
            return {
                "state": state, "district": district, "market": market, "variety": variety,
                "horizon_days": horizon_days, "direction": "insufficient_data", "strength": "low",
                "confidence": "low", "change_30d_percent": 0.0, "change_90d_percent": 0.0,
                "volatility_percent": 0.0,
                "note": "Not enough history for a 31-90 day seasonal outlook. No numeric long-range price is fabricated.",
                "methodology": ["Long-range outlook is directional only; TuberIntel deliberately caps precise numeric price forecasts at 30 days."],
            }
        change30 = self._change(values, 30)
        change90 = self._change(values, 90)
        returns = np.diff(np.log(np.asarray(values, dtype=float))) if all(value > 0 for value in values) else np.array([])
        volatility = float(np.std(returns) * np.sqrt(30) * 100) if len(returns) else 0.0
        combined = change30 * 0.65 + change90 * 0.35
        threshold = max(2.0, min(6.0, volatility * 0.35))
        if combined > threshold:
            direction = "rising"
        elif combined < -threshold:
            direction = "falling"
        else:
            direction = "stable"
        magnitude = abs(combined)
        strength = "high" if magnitude >= 10 else "moderate" if magnitude >= 4 else "low"
        confidence = "medium" if len(values) >= 180 else "low"
        return {
            "state": state, "district": district, "market": market, "variety": variety,
            "horizon_days": horizon_days, "direction": direction, "strength": strength,
            "confidence": confidence, "change_30d_percent": round(change30, 2),
            "change_90d_percent": round(change90, 2), "volatility_percent": round(volatility, 2),
            "note": "Directional seasonal outlook only. A precise rupee forecast is intentionally not produced beyond 30 days.",
            "methodology": [
                "Combines recent 30-day and broader 90-day price movement with realized volatility.",
                "The threshold adapts to market volatility so noisy markets are not labelled rising/falling from small moves.",
                "No recursive 31-90 day price extrapolation is used.",
            ],
        }

    def consolidated(
        self,
        db: Session,
        *,
        state: str | None = None,
        district: str | None = None,
    ) -> dict[str, Any]:
        base_conditions = self._conditions(state=state, district=district)
        latest_date = db.scalar(select(func.max(MarketPrice.arrival_date)).where(*base_conditions))
        if not latest_date:
            return {
                "state": state,
                "district": district,
                "date": None,
                "active_mandis": 0,
                "records": 0,
                "average_modal_price": 0.0,
                "median_modal_price": 0.0,
                "minimum_price": 0.0,
                "maximum_price": 0.0,
                "average_spread": 0.0,
                "change_percent_7d": 0.0,
                "direction": "stable",
                "source_note": "No market records available",
                "freshness": "unavailable",
                "arrival_volume_available": False,
            }
        rows = self.list_prices(db, state=state, district=district, date_from=latest_date, date_to=latest_date, limit=1000)
        modals = [r.modal_price for r in rows if r.modal_price > 0]
        mins = [r.min_price for r in rows if r.min_price > 0]
        maxs = [r.max_price for r in rows if r.max_price > 0]
        spreads = [r.max_price - r.min_price for r in rows if r.max_price >= r.min_price]
        history = self.historical_prices(db, state=state or "Karnataka", district=district, days=14)
        daily = self._daily(history)
        values = [d[1] for d in daily]
        change = self._change(values, 7)
        sources = sorted({r.source for r in rows})
        return {
            "state": state,
            "district": district,
            "date": latest_date,
            "active_mandis": len({r.market for r in rows}),
            "records": len(rows),
            "average_modal_price": round(float(np.mean(modals)) if modals else 0.0, 2),
            "median_modal_price": round(float(median(modals)) if modals else 0.0, 2),
            "minimum_price": round(float(min(mins or modals)) if (mins or modals) else 0.0, 2),
            "maximum_price": round(float(max(maxs or modals)) if (maxs or modals) else 0.0, 2),
            "average_spread": round(float(np.mean(spreads)) if spreads else 0.0, 2),
            "change_percent_7d": change,
            "direction": "rising" if change > 1 else "falling" if change < -1 else "stable",
            "source_note": ", ".join(sources) if sources else "No source",
            "freshness": latest_date.isoformat(),
            "arrival_volume_available": False,
        }

    def rankings(
        self,
        db: Session,
        *,
        state: str,
        district: str | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        rows = self.list_prices(db, state=state, district=district, latest_only=True, limit=1000)
        output = []
        for rank, row in enumerate(sorted(rows, key=lambda item: item.modal_price, reverse=True)[:limit], start=1):
            output.append(
                {
                    "rank": rank,
                    "state": row.state,
                    "district": row.district,
                    "market": row.market,
                    "variety": row.variety,
                    "modal_price": round(row.modal_price, 2),
                    "minimum_price": round(row.min_price, 2),
                    "maximum_price": round(row.max_price, 2),
                    "price_spread": round(max(0.0, row.max_price - row.min_price), 2),
                    "arrival_date": row.arrival_date,
                }
            )
        return output

    def analytics(
        self,
        db: Session,
        *,
        state: str = "Karnataka",
        district: str | None = None,
        market: str | None = None,
        variety: str | None = None,
        window_days: int = 90,
    ) -> dict[str, Any]:
        window_days = min(max(window_days, 7), 365)
        rows = self.historical_prices(
            db,
            state=state,
            district=district,
            market=market,
            variety=variety,
            days=window_days,
        )
        daily = self._daily(rows)
        values = [point[1] for point in daily]
        series = []
        for idx, point in enumerate(daily):
            start7 = max(0, idx - 6)
            start30 = max(0, idx - 29)
            series.append(
                {
                    "date": point[0],
                    "average_modal_price": round(point[1], 2),
                    "minimum_price": round(point[2], 2),
                    "maximum_price": round(point[3], 2),
                    "market_count": point[4],
                    "moving_average_7d": round(float(np.mean(values[start7 : idx + 1])), 2),
                    "moving_average_30d": round(float(np.mean(values[start30 : idx + 1])), 2),
                }
            )
        current = values[-1] if values else 0.0
        returns = np.diff(np.log(np.array(values, dtype=float))) if len(values) > 2 and all(v > 0 for v in values) else np.array([])
        volatility = float(np.std(returns) * np.sqrt(30) * 100) if len(returns) else 0.0
        latest_rows = self.list_prices(db, state=state, district=district, market=market, variety=variety, latest_only=True, limit=1000)
        variety_means: dict[str, list[float]] = defaultdict(list)
        for row in latest_rows:
            variety_means[row.variety].append(row.modal_price)
        strongest_variety = max(variety_means, key=lambda key: np.mean(variety_means[key])) if variety_means else "Unavailable"
        forecast_payload = self.forecast_detailed(
            db, state=state, district=district, market=market, variety=variety, horizon_days=30
        )
        confidence = forecast_payload["confidence"]
        return {
            "state": state,
            "district": district,
            "market": market,
            "variety": variety,
            "window_days": window_days,
            "daily_series": series,
            "rankings": self.rankings(db, state=state, district=district, limit=10),
            "forecast": forecast_payload["points"],
            "current_average": round(current, 2),
            "change_percent_7d": self._change(values, 7),
            "change_percent_30d": self._change(values, 30),
            "volatility_percent": round(volatility, 2),
            "price_range": round(max(values) - min(values), 2) if values else 0.0,
            "best_market": self.rankings(db, state=state, district=district, limit=1)[0]["market"] if latest_rows else "Unavailable",
            "strongest_variety": strongest_variety,
            "data_points": len(rows),
            "market_count": len({r.market for r in rows}),
            "confidence": confidence,
            "forecast_model": forecast_payload["model_name"],
            "forecast_version": forecast_payload["model_version"],
            "forecast_fallback": forecast_payload["fallback_used"],
            "methodology": [
                "Observed prices retain their source and reporting date. Seeded demonstration prices are excluded. Public-webpage aggregates are not variety-specific quotes.",
                "Daily averages are calculated from available modal prices after removing invalid zero values.",
                *forecast_payload["methodology"],
                "The forecast is a decision-support signal, not a guaranteed future price.",
                "Arrival quantities are not shown because the selected public price resource does not contain them.",
            ],
        }

    def overview(self, db: Session, state: str = "Karnataka") -> dict[str, Any]:
        prices = self.latest_prices(db, state=state, limit=16)
        consolidated = self.consolidated(db, state=state)
        forecast_payload = self.forecast_detailed(db, state=state, horizon_days=30)
        forecast = forecast_payload["points"]
        filters = self.filters(db)
        last_sync = db.scalar(select(MarketSyncRun).order_by(MarketSyncRun.started_at.desc()).limit(1))
        live_data = any("data.gov.in" in p.source.lower() or p.source.startswith("Public webpage:") for p in prices)
        return {
            "latest_prices": prices,
            "forecast": forecast,
            "price_direction": consolidated["direction"],
            "change_percent": consolidated["change_percent_7d"],
            "best_market": self.rankings(db, state=state, limit=1)[0]["market"] if prices else "No market data",
            "source_note": consolidated["source_note"],
            "freshness": consolidated["freshness"],
            "consolidated": consolidated,
            "top_markets": self.rankings(db, state=state, limit=8),
            "states": filters["states"],
            "live_data": live_data,
            "forecast_model": forecast_payload["model_name"],
            "forecast_confidence": forecast_payload["confidence"],
            "forecast_fallback": forecast_payload["fallback_used"],
            "last_sync": last_sync,
        }

    @staticmethod
    def storage_plan(payload: StoragePlanRequest) -> dict[str, Any]:
        quintals = payload.quantity_kg / 100.0
        sell_now = quintals * payload.current_price_per_quintal
        retained_quantity = quintals * (1.0 - payload.expected_loss_percent / 100.0)
        stored_revenue = retained_quantity * payload.expected_price_per_quintal
        storage_cost = quintals * payload.storage_days * payload.storage_cost_per_quintal_day
        handling_cost = quintals * payload.handling_cost_per_quintal
        expected_loss_value = (quintals - retained_quantity) * payload.expected_price_per_quintal
        net_storage = stored_revenue - storage_cost - handling_cost
        advantage = net_storage - sell_now
        break_even = (sell_now + storage_cost + handling_cost) / max(retained_quantity, 0.0001)
        return {
            "sell_now_revenue": round(sell_now, 2),
            "stored_sale_revenue": round(stored_revenue, 2),
            "storage_cost": round(storage_cost, 2),
            "handling_cost": round(handling_cost, 2),
            "expected_loss_value": round(expected_loss_value, 2),
            "net_storage_value": round(net_storage, 2),
            "advantage_over_sell_now": round(advantage, 2),
            "recommendation": "STORE" if advantage > 0 else "SELL_NOW",
            "break_even_price_per_quintal": round(break_even, 2),
        }

    @staticmethod
    def transport_plan(payload: TransportPlanRequest) -> dict[str, Any]:
        tonnes = payload.quantity_kg / 1000.0
        linehaul = tonnes * payload.distance_km * payload.rate_per_km_tonne
        total = linehaul + payload.loading_cost + payload.unloading_cost + payload.tolls_and_other
        quintals = payload.quantity_kg / 100.0
        return {
            "tonnes": round(tonnes, 3),
            "linehaul_cost": round(linehaul, 2),
            "loading_cost": round(payload.loading_cost, 2),
            "unloading_cost": round(payload.unloading_cost, 2),
            "tolls_and_other": round(payload.tolls_and_other, 2),
            "total_cost": round(total, 2),
            "cost_per_quintal": round(total / max(quintals, 0.0001), 2),
        }
