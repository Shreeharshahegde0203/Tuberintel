from __future__ import annotations

import re
from datetime import date, datetime, timezone
from typing import Any, Iterable

import httpx
from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.core.config import get_settings

# We deliberately reuse the existing market models and mandi helper
# from market_service so this patch does not change the database schema.
import app.services.market_service as market_module


class AgmarknetUpstreamError(RuntimeError):
    pass


def _normalise_text(value: Any) -> str:
    return " ".join(str(value or "").strip().split()).casefold()


def _clean_text(value: Any, default: str = "") -> str:
    result = " ".join(str(value or "").strip().split())
    return result or default


def _canonical_location(value: Any) -> str:
    value = _clean_text(value)

    if not value:
        return value

    # Keep TuberIntel's existing Bengaluru naming consistent with
    # possible upstream AGMARKNET "Bangalore" spellings.
    value = re.sub(r"\bBangalore\b", "Bengaluru", value, flags=re.IGNORECASE)

    return value


def _to_float(value: Any) -> float | None:
    if value is None:
        return None

    if isinstance(value, (int, float)):
        return float(value)

    text = str(value).replace(",", "").strip()

    if not text:
        return None

    try:
        return float(text)
    except (TypeError, ValueError):
        return None


def _parse_date(value: Any) -> date | None:
    if isinstance(value, datetime):
        return value.date()

    if isinstance(value, date):
        return value

    text = str(value or "").strip()

    if not text:
        return None

    formats = (
        "%d/%m/%Y",
        "%Y-%m-%d",
        "%d-%m-%Y",
        "%d-%b-%Y",
        "%d %b %Y",
    )

    for fmt in formats:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue

    return None


def _pick(mapping: dict[str, Any], *names: str) -> Any:
    for name in names:
        if name in mapping:
            value = mapping[name]

            if value is not None and value != "":
                return value

    return None


def _walk_dicts(value: Any) -> Iterable[dict[str, Any]]:
    if isinstance(value, dict):
        yield value

        for child in value.values():
            yield from _walk_dicts(child)

    elif isinstance(value, list):
        for child in value:
            yield from _walk_dicts(child)


def _model_columns(model: Any) -> set[str]:
    try:
        return set(model.__table__.columns.keys())
    except Exception:
        return set()


def _supported_values(model: Any, values: dict[str, Any]) -> dict[str, Any]:
    columns = _model_columns(model)

    return {
        key: value
        for key, value in values.items()
        if key in columns
    }


class AgmarknetService:
    SOURCE = "AGMARKNET 2.0 direct"

    def __init__(self) -> None:
        self.settings = get_settings()

    @property
    def base_url(self) -> str:
        return str(
            getattr(
                self.settings,
                "agmarknet_base_url",
                "https://api.agmarknet.gov.in/v1",
            )
        ).rstrip("/")

    @property
    def timeout(self) -> float:
        return float(
            getattr(
                self.settings,
                "agmarknet_timeout_seconds",
                30.0,
            )
        )

    @property
    def commodity_id(self) -> int:
        return int(
            getattr(
                self.settings,
                "agmarknet_potato_commodity_id",
                24,
            )
        )

    @property
    def sync_months(self) -> int:
        value = int(
            getattr(
                self.settings,
                "agmarknet_sync_months",
                2,
            )
        )

        return max(1, min(value, 6))

    def _headers(self) -> dict[str, str]:
        return {
            "Accept": "application/json, text/plain, */*",
            "Origin": "https://agmarknet.gov.in",
            "Referer": "https://agmarknet.gov.in/",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 "
                "(KHTML, like Gecko) "
                "Chrome/154.0.0.0 Safari/537.36"
            ),
        }

    def _client(self) -> httpx.Client:
        return httpx.Client(
            timeout=self.timeout,
            follow_redirects=True,
            headers=self._headers(),
        )

    def _request_json(
        self,
        client: httpx.Client,
        path: str,
        *,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        url = f"{self.base_url}/{path.lstrip('/')}"

        try:
            response = client.get(
                url,
                params=params,
            )
        except httpx.HTTPError as exc:
            raise AgmarknetUpstreamError(
                f"AGMARKNET connection failed: {exc}"
            ) from exc

        if response.status_code == 404:
            return {}

        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            body = response.text[:300]

            raise AgmarknetUpstreamError(
                f"AGMARKNET returned HTTP "
                f"{response.status_code}: {body}"
            ) from exc

        try:
            payload = response.json()
        except ValueError as exc:
            raise AgmarknetUpstreamError(
                "AGMARKNET returned a non-JSON response"
            ) from exc

        if not isinstance(payload, dict):
            raise AgmarknetUpstreamError(
                "Unexpected AGMARKNET response format"
            )

        return payload

    def _get_filters(
        self,
        client: httpx.Client,
    ) -> dict[str, Any]:
        return self._request_json(
            client,
            "/daily-price-arrival/filters",
        )

    def _named_id(
        self,
        payload: dict[str, Any],
        wanted: str,
        *,
        name_fields: tuple[str, ...],
        id_fields: tuple[str, ...],
    ) -> int | None:
        wanted_normalised = _normalise_text(wanted)

        for item in _walk_dicts(payload):
            matched = False

            for name_field in name_fields:
                if name_field not in item:
                    continue

                if _normalise_text(item[name_field]) == wanted_normalised:
                    matched = True
                    break

            if not matched:
                continue

            for id_field in id_fields:
                value = item.get(id_field)

                if value is None:
                    continue

                try:
                    return int(value)
                except (TypeError, ValueError):
                    continue

        return None

    def _resolve_state_id(
        self,
        filters: dict[str, Any],
        state: str,
    ) -> int:
        result = self._named_id(
            filters,
            state,
            name_fields=(
                "state_name",
                "stateName",
                "state",
                "name",
            ),
            id_fields=(
                "id",
                "state_id",
                "stateId",
            ),
        )

        if result is not None:
            return result

        # Confirmed from the current AGMARKNET filter metadata.
        if _normalise_text(state) == "karnataka":
            return 16

        raise AgmarknetUpstreamError(
            f"Could not resolve AGMARKNET state ID for {state}"
        )

    def _resolve_commodity_id(
        self,
        filters: dict[str, Any],
    ) -> int:
        result = self._named_id(
            filters,
            "Potato",
            name_fields=(
                "commodity_name",
                "commodityName",
                "commodity",
                "cmdt_name",
                "cmdtName",
                "name",
            ),
            id_fields=(
                "id",
                "commodity_id",
                "commodityId",
                "cmdt_id",
            ),
        )

        # 24 is the current AGMARKNET Potato commodity ID.
        return result if result is not None else self.commodity_id

    @staticmethod
    def _market_district_map(
        payload: dict[str, Any],
        state_id: int,
    ) -> dict[str, str]:
        """
        Build:
            normalised market name -> district name

        AGMARKNET filter data stores markets and districts separately.

        Market example:
            {
                "id": 489,
                "mkt_name": "Doddaballapur APMC",
                "state_id": 16,
                "district_id": 727
            }

        District example:
            {
                "id": 727,
                "state_id": 16,
                "district_name": "..."
            }

        Therefore the correct relationship is:

            market.district_id == district.id
        """

        nodes: list[dict[str, Any]] = []

        def walk(value: Any) -> None:
            if isinstance(value, dict):
                nodes.append(value)

                for child in value.values():
                    walk(child)

            elif isinstance(value, list):
                for child in value:
                    walk(child)

        walk(payload)

        # ---------------------------------------------------------
        # 1. Build district_id -> district_name for requested state
        # ---------------------------------------------------------

        district_by_id: dict[int, str] = {}

        for item in nodes:
            district_name = _pick(
                item,
                "district_name",
                "districtName",
            )

            district_id = _pick(
                item,
                "id",
                "district_id",
                "districtId",
            )

            item_state_id = _pick(
                item,
                "state_id",
                "stateId",
            )

            if not district_name or district_id is None:
                continue

            try:
                district_id_int = int(str(district_id).strip())
            except (TypeError, ValueError):
                continue

            if item_state_id is not None:
                try:
                    if int(str(item_state_id).strip()) != int(state_id):
                        continue
                except (TypeError, ValueError):
                    continue

            district_name = _canonical_location(
                str(district_name)
            )

            if (
                district_name
                and _normalise_text(district_name) != "unknown"
            ):
                district_by_id[district_id_int] = district_name

        # ---------------------------------------------------------
        # 2. Join market.district_id -> district.id
        # ---------------------------------------------------------

        market_districts: dict[str, str] = {}

        for item in nodes:
            market_name = _pick(
                item,
                "mkt_name",
                "marketName",
                "market_name",
                "market",
                "mandiName",
                "mandi_name",
            )

            district_id = _pick(
                item,
                "district_id",
                "districtId",
            )

            item_state_id = _pick(
                item,
                "state_id",
                "stateId",
            )

            if not market_name or district_id is None:
                continue

            if item_state_id is not None:
                try:
                    if int(str(item_state_id).strip()) != int(state_id):
                        continue
                except (TypeError, ValueError):
                    continue

            try:
                district_id_int = int(str(district_id).strip())
            except (TypeError, ValueError):
                continue

            district_name = district_by_id.get(
                district_id_int
            )

            if not district_name:
                continue

            market_name = _canonical_location(
                str(market_name)
            )

            market_districts[
                _normalise_text(market_name)
            ] = district_name

        return market_districts

    @staticmethod
    def _markets_from_payload(
        payload: dict[str, Any],
    ) -> list[dict[str, Any]]:
        direct = payload.get("markets")

        if isinstance(direct, list):
            return [
                item
                for item in direct
                if isinstance(item, dict)
            ]

        data = payload.get("data")

        if isinstance(data, dict):
            markets = data.get("markets")

            if isinstance(markets, list):
                return [
                    item
                    for item in markets
                    if isinstance(item, dict)
                ]

        return []

    @staticmethod
    def _month_targets(
        months: int,
    ) -> list[tuple[int, int]]:
        today = date.today()

        year = today.year
        month = today.month

        result: list[tuple[int, int]] = []

        for _ in range(months):
            result.append((year, month))

            month -= 1

            if month == 0:
                month = 12
                year -= 1

        return result

    def _existing_district(
        self,
        db: Session,
        state: str,
        market: str,
    ) -> str | None:
        MarketPrice = getattr(
            market_module,
            "MarketPrice",
            None,
        )

        if MarketPrice is None:
            return None

        required = ("state", "market", "district")

        if not all(
            hasattr(MarketPrice, name)
            for name in required
        ):
            return None

        try:
            result = db.scalar(
                select(MarketPrice.district)
                .where(
                    MarketPrice.state == state,
                    MarketPrice.market == market,
                )
                .limit(1)
            )

            return (
                _canonical_location(result)
                if result
                else None
            )
        except Exception:
            return None

    def _flatten_payload(
        self,
        db: Session,
        payload: dict[str, Any],
        *,
        state: str,
        district_filter: str | None,
        market_districts: dict[str, str],
    ) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []

        for market_entry in self._markets_from_payload(
            payload
        ):
            market_name = _pick(
                market_entry,
                "marketName",
                "market_name",
                "market",
                "mandiName",
                "mandi_name",
            )

            if market_name is None:
                continue

            market_name = _canonical_location(
                market_name
            )

            district_name = _pick(
                market_entry,
                "districtName",
                "district_name",
                "district",
            )

            if district_name:
                district_name = _canonical_location(
                    district_name
                )
            else:
                district_name = market_districts.get(
                    _normalise_text(market_name)
                )

            if not district_name:
                district_name = self._existing_district(
                    db,
                    state,
                    market_name,
                )

            if not district_name:
                district_name = (
                    _canonical_location(district_filter)
                    if district_filter
                    else "Unknown"
                )

            if (
                district_filter
                and _normalise_text(district_name)
                != _normalise_text(district_filter)
            ):
                continue

            date_groups = (
                market_entry.get("dates")
                or market_entry.get("dateWiseData")
                or []
            )

            if not isinstance(date_groups, list):
                continue

            for date_group in date_groups:
                if not isinstance(date_group, dict):
                    continue

                arrival = _parse_date(
                    _pick(
                        date_group,
                        "arrivalDate",
                        "arrival_date",
                        "date",
                    )
                )

                if arrival is None:
                    continue

                price_rows = (
                    date_group.get("data")
                    or date_group.get("prices")
                    or []
                )

                if not isinstance(price_rows, list):
                    continue

                for price in price_rows:
                    if not isinstance(price, dict):
                        continue

                    minimum = _to_float(
                        _pick(
                            price,
                            "minimumPrice",
                            "minimum_price",
                            "minPrice",
                            "min_price",
                        )
                    )

                    maximum = _to_float(
                        _pick(
                            price,
                            "maximumPrice",
                            "maximum_price",
                            "maxPrice",
                            "max_price",
                        )
                    )

                    modal = _to_float(
                        _pick(
                            price,
                            "modalPrice",
                            "modal_price",
                            "modelPrice",
                        )
                    )

                    if modal is None or modal <= 0:
                        continue

                    if minimum is None:
                        minimum = modal

                    if maximum is None:
                        maximum = modal

                    variety = _clean_text(
                        _pick(
                            price,
                            "variety",
                            "varietyName",
                            "variety_name",
                        ),
                        "Local",
                    )

                    grade = _clean_text(
                        _pick(
                            price,
                            "grade",
                            "gradeName",
                            "grade_name",
                        ),
                        "FAQ",
                    )

                    rows.append(
                        {
                            "state": _canonical_location(
                                state
                            ),
                            "district": district_name,
                            "market": market_name,
                            "commodity": "Potato",
                            "variety": variety,
                            "grade": grade,
                            "arrival_date": arrival,
                            "minimum_price": minimum,
                            "maximum_price": maximum,
                            "modal_price": modal,
                            "source": self.SOURCE,
                        }
                    )

        return rows

    def _fetch_records(
        self,
        db: Session,
        *,
        state: str,
        district: str | None,
    ) -> tuple[list[dict[str, Any]], int, int]:
        with self._client() as client:
            filters = self._get_filters(client)

            state_id = self._resolve_state_id(
                filters,
                state,
            )

            commodity_id = self._resolve_commodity_id(
                filters
            )

            market_districts = self._market_district_map(
                filters,
                state_id,
            )

            records: list[dict[str, Any]] = []

            for year, month in self._month_targets(
                self.sync_months
            ):
                payload = self._request_json(
                    client,
                    "/prices-and-arrivals/"
                    "date-wise/specific-commodity",
                    params={
                        "year": year,
                        "month": month,
                        "stateId": state_id,
                        "commodityId": commodity_id,
                        "includeExcel": "false",
                    },
                )

                records.extend(
                    self._flatten_payload(
                        db,
                        payload,
                        state=state,
                        district_filter=district,
                        market_districts=market_districts,
                    )
                )

        # De-duplicate in case upstream returns repeated entries.
        unique: dict[
            tuple[str, str, str, str, str, date],
            dict[str, Any],
        ] = {}

        for record in records:
            key = (
                record["state"],
                record["district"],
                record["market"],
                record["variety"],
                record["grade"],
                record["arrival_date"],
            )

            unique[key] = record

        return list(unique.values()), state_id, commodity_id

    @staticmethod
    def _set_price_value(
        values: dict[str, Any],
        columns: set[str],
        candidates: tuple[str, ...],
        value: Any,
    ) -> None:
        for candidate in candidates:
            if candidate in columns:
                values[candidate] = value
                return

    def _upsert_price(
        self,
        db: Session,
        record: dict[str, Any],
    ) -> tuple[int, int]:
        MarketPrice = getattr(
            market_module,
            "MarketPrice",
            None,
        )

        if MarketPrice is None:
            raise RuntimeError(
                "Existing MarketPrice model could not be loaded"
            )

        columns = _model_columns(MarketPrice)

        values: dict[str, Any] = {}

        for field in (
            "state",
            "district",
            "market",
            "commodity",
            "variety",
            "grade",
            "arrival_date",
            "source",
        ):
            if field in columns:
                values[field] = record[field]

        self._set_price_value(
            values,
            columns,
            ("minimum_price", "min_price"),
            record["minimum_price"],
        )

        self._set_price_value(
            values,
            columns,
            ("maximum_price", "max_price"),
            record["maximum_price"],
        )

        self._set_price_value(
            values,
            columns,
            ("modal_price", "model_price"),
            record["modal_price"],
        )

        key_fields = (
            "state",
            "district",
            "market",
            "commodity",
            "variety",
            "grade",
            "arrival_date",
        )

        conditions = []

        for field in key_fields:
            if (
                field in values
                and hasattr(MarketPrice, field)
            ):
                conditions.append(
                    getattr(MarketPrice, field)
                    == values[field]
                )

        if not conditions:
            raise RuntimeError(
                "Could not determine MarketPrice identity columns"
            )

        existing = db.scalar(
            select(MarketPrice)
            .where(and_(*conditions))
            .limit(1)
        )

        if existing is None:
            db.add(
                MarketPrice(
                    **_supported_values(
                        MarketPrice,
                        values,
                    )
                )
            )

            return 1, 0

        changed = False

        for field, value in values.items():
            if not hasattr(existing, field):
                continue

            if getattr(existing, field) != value:
                setattr(existing, field, value)
                changed = True

        return 0, 1 if changed else 0

    def _start_sync_run(
        self,
        db: Session,
        *,
        state: str,
    ) -> Any | None:
        Model = getattr(
            market_module,
            "MarketSyncRun",
            None,
        )

        if Model is None:
            return None

        values = _supported_values(
            Model,
            {
                "source": self.SOURCE,
                "resource_id": (
                    f"potato-{self.commodity_id}"
                ),
                "state": state,
                "status": "running",
            },
        )

        try:
            run = Model(**values)
            db.add(run)
            db.commit()
            db.refresh(run)
            return run
        except Exception:
            db.rollback()
            return None

    @staticmethod
    def _finish_sync_run(
        db: Session,
        run: Any | None,
        *,
        status: str,
        received: int,
        inserted: int,
        updated: int,
    ) -> None:
        if run is None:
            return

        mapping = {
            "status": status,
            "records_received": received,
            "records_inserted": inserted,
            "records_updated": updated,
            "finished_at": datetime.now(
                timezone.utc
            ),
        }

        try:
            for field, value in mapping.items():
                if hasattr(run, field):
                    setattr(run, field, value)

            db.add(run)
            db.commit()
        except Exception:
            db.rollback()

    def _update_mandi_directory(
        self,
        db: Session,
        record: dict[str, Any],
    ) -> None:
        service = getattr(
            market_module,
            "market_service",
            None,
        )

        helper = getattr(
            service,
            "_upsert_mandi",
            None,
        )

        if not callable(helper):
            return

        try:
            helper(
                db,
                state=record["state"],
                district=record["district"],
                market=record["market"],
                source=self.SOURCE,
            )
        except Exception:
            # MarketPrice sync must not fail only because the optional
            # directory helper changed internally.
            pass

    def refresh(
        self,
        db: Session,
        *,
        state: str = "Karnataka",
        district: str | None = None,
    ) -> dict[str, Any]:
        state = _canonical_location(
            state or "Karnataka"
        )

        district = (
            _canonical_location(district)
            if district
            else None
        )

        run = self._start_sync_run(
            db,
            state=state,
        )

        received = 0
        inserted = 0
        updated = 0

        try:
            records, state_id, commodity_id = (
                self._fetch_records(
                    db,
                    state=state,
                    district=district,
                )
            )

            received = len(records)

            if not records:
                raise AgmarknetUpstreamError(
                    "AGMARKNET returned no Potato price "
                    "records for the requested location/months"
                )

            for record in records:
                self._update_mandi_directory(
                    db,
                    record,
                )

                added, changed = self._upsert_price(
                    db,
                    record,
                )

                inserted += added
                updated += changed

            db.commit()

            latest = max(
                record["arrival_date"]
                for record in records
            )

            self._finish_sync_run(
                db,
                run,
                status="completed",
                received=received,
                inserted=inserted,
                updated=updated,
            )

            return {
                "updated": updated,
                "inserted": inserted,
                "received": received,
                "source": self.SOURCE,
                "live_data": True,
                "state_id": state_id,
                "commodity_id": commodity_id,
                "latest_date": latest.isoformat(),
                "note": (
                    "Live Potato mandi prices refreshed "
                    "directly from AGMARKNET 2.0."
                ),
            }

        except Exception:
            db.rollback()

            self._finish_sync_run(
                db,
                run,
                status="failed",
                received=received,
                inserted=inserted,
                updated=updated,
            )

            raise

    def probe(
        self,
        *,
        state: str = "Karnataka",
    ) -> dict[str, Any]:
        state = _canonical_location(state)

        with self._client() as client:
            filters = self._get_filters(client)

            state_id = self._resolve_state_id(
                filters,
                state,
            )

            commodity_id = self._resolve_commodity_id(
                filters
            )

            results = []

            for year, month in self._month_targets(
                self.sync_months
            ):
                payload = self._request_json(
                    client,
                    "/prices-and-arrivals/"
                    "date-wise/specific-commodity",
                    params={
                        "year": year,
                        "month": month,
                        "stateId": state_id,
                        "commodityId": commodity_id,
                        "includeExcel": "false",
                    },
                )

                markets = self._markets_from_payload(
                    payload
                )

                results.append(
                    {
                        "year": year,
                        "month": month,
                        "markets": len(markets),
                    }
                )

            return {
                "ok": True,
                "source": self.SOURCE,
                "state": state,
                "state_id": state_id,
                "commodity": "Potato",
                "commodity_id": commodity_id,
                "months_checked": results,
            }


agmarknet_service = AgmarknetService()
