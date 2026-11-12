from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    app_name: str = "TuberIntel API"
    environment: str = "development"
    api_prefix: str = "/api/v1"
    database_url: str = f"sqlite:///{BASE_DIR / 'tuberintel.db'}"
    frontend_origin: str = "http://localhost:5173"
    auth_mode: str = "demo"
    upload_dir: Path = BASE_DIR / "storage" / "uploads"
    annotated_dir: Path = BASE_DIR / "storage" / "annotated"

    storage_backend: str = "local"
    supabase_url: str | None = None
    supabase_service_role_key: str | None = None
    supabase_storage_bucket: str = "potato-inspections"

    # Official data.gov.in / AGMARKNET daily mandi-price feed.
    data_gov_api_key: str | None = None
    data_gov_resource_id: str = "9ef84268-d588-465a-a308-a864a43d0070"
    # Direct AGMARKNET 2.0 is the primary mandi-price source.
    # data.gov.in remains configured as a secondary fallback.
    agmarknet_base_url: str = "https://api.agmarknet.gov.in/v1"
    agmarknet_timeout_seconds: float = 30.0
    agmarknet_sync_months: int = 2
    agmarknet_potato_commodity_id: int = 24
    market_cache_minutes: int = 60
    analysis_market_max_age_days: int = Field(default=7, ge=0)
    market_page_size: int = 500
    market_max_pages: int = 8
    market_directory_max_pages: int = 80

    # Price forecasting. The API never returns precise numeric forecasts beyond
    # the operational 30-day window. If a validated artifact is unavailable the
    # runtime falls back to an auditable seasonal/trend ensemble.
    price_forecast_model_path: Path | None = BASE_DIR.parent / "ml" / "artifacts" / "price_forecaster_v2.joblib"
    price_forecast_max_horizon_days: int = 30
    price_forecast_min_history_days: int = 90
    price_forecast_history_days: int = 1825
    price_forecast_interval_level: float = 0.80

    # News headline feeds. Only title, short summary and outbound link are stored.
    potato_news_feeds: str = (
        "https://news.google.com/rss/search?q=potato+India&hl=en-IN&gl=IN&ceid=IN:en,"
        "https://news.google.com/rss/search?q=potato+farmer+India&hl=en-IN&gl=IN&ceid=IN:en"
    )
    news_cache_minutes: int = 90

    # Open-Meteo does not require an API key. Coordinates are supplied by the client.
    weather_base_url: str = "https://api.open-meteo.com/v1/forecast"

    # Vision runtime.
    #
    # cv_demo:
    #   deterministic OpenCV fallback only.
    #
    # vision_v1 / hybrid:
    #   use trained Model A/B/C whenever their weights exist,
    #   while preserving the OpenCV capture-quality and fallback path.
    model_mode: str = Field(
        default="cv_demo",
        description="cv_demo, vision_v1, hybrid, classifier, or detector",
    )

    # TuberIntel Vision v1
    roi_model_path: Path | None = None
    condition_model_path: Path | None = None
    defect_model_path: Path | None = None

    # Legacy compatibility only. New deployments should use
    # CONDITION_MODEL_PATH instead.
    quality_model_path: Path | None = None
    max_upload_mb: int = 12

    # Optional LLM enhancement for Tuber Mitra. The assistant remains fully
    # functional in local-grounded mode when no key is configured.
    openai_api_key: str | None = None
    openai_model: str = "gpt-5"

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def news_feed_urls(self) -> list[str]:
        return [item.strip() for item in self.potato_news_feeds.split(",") if item.strip()]

    def ensure_directories(self) -> None:
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.annotated_dir.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_directories()
    return settings

