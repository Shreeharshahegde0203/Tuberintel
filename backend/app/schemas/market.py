from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


def normalize_text(value: str) -> str:
    return " ".join(value.split())


class MarketStateItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    code: str | None = None
    active: bool = True
    district_count: int = 0
    market_count: int = 0


class MarketDistrictItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    state: str
    active: bool = True
    market_count: int = 0


class MarketDirectoryItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    state: str
    district: str
    source: str
    active: bool
    latitude: float | None = None
    longitude: float | None = None
    external_market_name: str | None = None
    external_id: str | None = None
    updated_at: datetime


class MarketPriceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    market_id: int | None = None
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
    fetched_at: datetime
    source_record_id: str | None = None


class ForecastPoint(BaseModel):
    date: date
    predicted_price: float
    lower_bound: float
    upper_bound: float


class ConsolidatedMarketStats(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    report_date: date | None = Field(default=None, alias="date", serialization_alias="date")
    active_mandis: int = 0
    records: int = 0
    average_modal_price: float | None = None
    minimum_price: float | None = None
    maximum_price: float | None = None
    commodity: str = "Potato"
    data_source: str = "Unavailable"
    arrival_volume: float | None = None
    arrival_volume_note: str = "Arrival volume is unavailable for the current source."
    change_percent_7d: float = 0.0
    direction: Literal["rising", "falling", "stable"] = "stable"


class TopMarketItem(BaseModel):
    market_id: int | None = None
    state: str
    district: str
    market: str
    modal_price: float
    arrival_date: date
    variety: str
    source: str
    rank: int
    change_percent: float | None = None


class MarketOverview(BaseModel):
    latest_prices: list[MarketPriceRead]
    forecast: list[ForecastPoint]
    price_direction: Literal["rising", "falling", "stable"]
    change_percent: float
    best_market: str
    source_note: str
    freshness: str
    consolidated: ConsolidatedMarketStats
    top_markets: list[TopMarketItem]
    live_data: bool
    states: list[str]


class MarketFilters(BaseModel):
    states: list[str]
    districts: list[str]
    markets: list[str]
    commodities: list[str]
    varieties: list[str]
    grades: list[str]
    selected_state: str | None = None
    selected_district: str | None = None
    source: str | None = None
    freshness: str | None = None


class MarketDirectoryResponse(BaseModel):
    state: str | None = None
    district: str | None = None
    total: int
    limit: int
    offset: int
    items: list[MarketDirectoryItem]
    source: str
    live_data: bool
    note: str | None = None


class MarketAnalyticsSummary(BaseModel):
    record_count: int
    average_modal_price: float | None = None
    minimum_price: float | None = None
    maximum_price: float | None = None
    latest_price: float | None = None
    previous_price: float | None = None
    change_amount: float | None = None
    change_percent: float = 0.0
    direction: Literal["rising", "falling", "stable"] = "stable"


class MarketTrendPoint(BaseModel):
    date: date
    min_price: float
    max_price: float
    modal_price: float
    average_price: float


class MarketAnalytics(BaseModel):
    state: str | None = None
    district: str | None = None
    market: str | None = None
    commodity: str
    variety: str | None = None
    window_days: int
    summary: MarketAnalyticsSummary
    trend: list[MarketTrendPoint]
    source: str
    freshness: str
    note: str | None = None


class MarketSyncResponse(BaseModel):
    state: str | None = None
    received: int
    inserted: int
    updated: int
    mandi_count: int
    live_data: bool
    source: str
    note: str


class MarketPriceQuery(BaseModel):
    state: str | None = Field(default=None, max_length=120)
    district: str | None = Field(default=None, max_length=120)
    market: str | None = Field(default=None, max_length=160)
    commodity: str = Field(default="Potato", max_length=80)
    variety: str | None = Field(default=None, max_length=80)
    grade: str | None = Field(default=None, max_length=40)
    date_from: date | None = None
    date_to: date | None = None
    latest_only: bool = False
    limit: int = Field(default=50, ge=1, le=200)
    offset: int = Field(default=0, ge=0, le=10_000)

    @field_validator("state", "district", "market", "commodity", "variety", "grade")
    @classmethod
    def trim_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        trimmed = normalize_text(value)
        return trimmed or None

    @field_validator("date_to")
    @classmethod
    def validate_date_range(cls, value: date | None, info) -> date | None:
        date_from = info.data.get("date_from")
        if value and date_from and value < date_from:
            raise ValueError("date_to must be on or after date_from")
        return value
