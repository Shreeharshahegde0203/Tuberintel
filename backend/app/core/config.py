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
    frontend_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    upload_dir: Path = BASE_DIR / "storage" / "uploads"
    annotated_dir: Path = BASE_DIR / "storage" / "annotated"

    storage_backend: str = "local"
    supabase_url: str | None = None
    supabase_service_role_key: str | None = None
    supabase_storage_bucket: str = "potato-inspections"

    data_gov_api_key: str | None = None
    data_gov_resource_id: str = "9ef84268-d588-465a-a308-a864a43d0070"
    market_cache_minutes: int = 60
    market_page_size: int = 100
    market_max_pages: int = 5
    market_retry_attempts: int = 3
    market_connect_timeout: float = 5.0
    market_read_timeout: float = 20.0

    supabase_jwt_secret: str | None = None
    admin_user_ids: str = ""
    admin_emails: str = ""
    internal_service_key: str | None = None
    cors_allow_credentials: bool = True
    enable_request_logging: bool = True

    model_mode: str = Field(
        default="cv_demo",
        description="cv_demo, classifier, detector, or hybrid",
    )
    quality_model_path: Path | None = None
    defect_model_path: Path | None = None
    max_upload_mb: int = 12

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def ensure_directories(self) -> None:
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.annotated_dir.mkdir(parents=True, exist_ok=True)

    @property
    def frontend_origin_list(self) -> list[str]:
        origins = [item.strip() for item in self.frontend_origins.split(",") if item.strip()]
        if self.frontend_origin and self.frontend_origin not in origins:
            origins.append(self.frontend_origin)
        return origins

    @property
    def admin_user_id_list(self) -> set[str]:
        return {item.strip() for item in self.admin_user_ids.split(",") if item.strip()}

    @property
    def admin_email_list(self) -> set[str]:
        return {item.strip().lower() for item in self.admin_emails.split(",") if item.strip()}


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_directories()
    return settings
