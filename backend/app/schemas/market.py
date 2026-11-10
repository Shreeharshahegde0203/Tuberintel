from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class MarketPriceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int | None = None
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


class ForecastPoint(BaseModel):
    date: date
    predicted_price: float
    lower_bound: float
    upper_bound: float
    horizon_days: int | None = None
    model_name: str | None = None
    confidence: str | None = None
    interval_level: float | None = None


class MarketForecastResponse(BaseModel):
    state: str
    district: str | None = None
    market: str | None = None
    variety: str | None = None
    horizon_days: int
    points: list[ForecastPoint]
    model_name: str
    model_version: str
    confidence: str
    training_points: int
    fallback_used: bool
    data_start: date | None = None
    data_end: date | None = None
    methodology: list[str]
    diagnostics: dict


class MarketOutlookResponse(BaseModel):
    state: str
    district: str | None = None
    market: str | None = None
    variety: str | None = None
    horizon_days: int
    direction: str
    strength: str
    confidence: str
    change_30d_percent: float
    change_90d_percent: float
    volatility_percent: float
    note: str
    methodology: list[str]


class DailyPricePoint(BaseModel):
    date: date
    average_modal_price: float
    minimum_price: float
    maximum_price: float
    market_count: int
    moving_average_7d: float | None = None
    moving_average_30d: float | None = None


class MarketRank(BaseModel):
    rank: int
    state: str
    district: str
    market: str
    variety: str
    modal_price: float
    minimum_price: float
    maximum_price: float
    price_spread: float
    arrival_date: date


class MarketStateOption(BaseModel):
    code: str
    name: str
    type: str
    mandi_count: int


class MandiDirectoryItem(BaseModel):
    id: int
    state: str
    district: str
    market: str
    source: str
    is_enam: bool | None = None
    last_seen_at: datetime


class MandiDirectoryResponse(BaseModel):
    state: str
    districts: list[str]
    mandis: list[MandiDirectoryItem]
    count: int
    source: str
    last_synced_at: datetime | None = None
    api_configured: bool


class MarketFilters(BaseModel):
    states: list[str]
    districts: list[str]
    markets: list[str]
    varieties: list[str]
    grades: list[str]
    latest_date: date | None = None


class ConsolidatedMarketReport(BaseModel):
    state: str | None
    district: str | None
    date: date | None
    active_mandis: int
    records: int
    average_modal_price: float
    median_modal_price: float
    minimum_price: float
    maximum_price: float
    average_spread: float
    change_percent_7d: float
    direction: str
    source_note: str
    freshness: str
    arrival_volume_available: bool = False
    arrival_volume_note: str = (
        "The public AGMARKNET price resource does not include mandi arrival quantity. "
        "Arrival volume is therefore not estimated or fabricated."
    )


class MarketAnalytics(BaseModel):
    state: str
    district: str | None
    market: str | None
    variety: str | None
    window_days: int
    daily_series: list[DailyPricePoint]
    rankings: list[MarketRank]
    forecast: list[ForecastPoint]
    current_average: float
    change_percent_7d: float
    change_percent_30d: float
    volatility_percent: float
    price_range: float
    best_market: str
    strongest_variety: str
    data_points: int
    market_count: int
    confidence: str
    forecast_model: str | None = None
    forecast_version: str | None = None
    forecast_fallback: bool | None = None
    methodology: list[str]


class SyncRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source: str
    resource_id: str
    state: str | None
    status: str
    records_received: int
    records_inserted: int
    records_updated: int
    error: str | None
    started_at: datetime
    finished_at: datetime | None


class MarketOverview(BaseModel):
    latest_prices: list[MarketPriceRead]
    forecast: list[ForecastPoint]
    price_direction: str
    change_percent: float
    best_market: str
    source_note: str
    freshness: str
    consolidated: ConsolidatedMarketReport
    top_markets: list[MarketRank]
    states: list[str]
    live_data: bool
    forecast_model: str | None = None
    forecast_confidence: str | None = None
    forecast_fallback: bool | None = None
    last_sync: SyncRunRead | None = None


class NewsArticleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source: str
    title: str
    summary: str
    url: str
    image_url: str | None
    category: str
    language: str
    published_at: datetime | None
    fetched_at: datetime


class NewsResponse(BaseModel):
    articles: list[NewsArticleRead]
    categories: list[str]
    sources: list[str]
    freshness: str
    live_data: bool
    note: str


class WeatherDay(BaseModel):
    date: date
    weather_code: int
    minimum_temperature: float
    maximum_temperature: float
    precipitation_probability: float
    precipitation_mm: float


class WeatherResponse(BaseModel):
    latitude: float
    longitude: float
    timezone: str
    current_temperature: float | None
    current_humidity: float | None
    current_wind_speed: float | None
    current_weather_code: int | None
    daily: list[WeatherDay]
    fetched_at: datetime
    source: str = "Open-Meteo"


class StoragePlanRequest(BaseModel):
    quantity_kg: float = Field(gt=0)
    current_price_per_quintal: float = Field(gt=0)
    expected_price_per_quintal: float = Field(gt=0)
    storage_days: int = Field(ge=1, le=365)
    storage_cost_per_quintal_day: float = Field(ge=0)
    expected_loss_percent: float = Field(ge=0, le=100)
    handling_cost_per_quintal: float = Field(ge=0)


class StoragePlanResponse(BaseModel):
    sell_now_revenue: float
    stored_sale_revenue: float
    storage_cost: float
    handling_cost: float
    expected_loss_value: float
    net_storage_value: float
    advantage_over_sell_now: float
    recommendation: str
    break_even_price_per_quintal: float


class TransportPlanRequest(BaseModel):
    quantity_kg: float = Field(gt=0)
    distance_km: float = Field(ge=0)
    rate_per_km_tonne: float = Field(ge=0)
    loading_cost: float = Field(ge=0)
    unloading_cost: float = Field(ge=0)
    tolls_and_other: float = Field(ge=0)


class TransportPlanResponse(BaseModel):
    tonnes: float
    linehaul_cost: float
    loading_cost: float
    unloading_cost: float
    tolls_and_other: float
    total_cost: float
    cost_per_quintal: float
