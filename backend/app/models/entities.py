from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Batch(Base):
    __tablename__ = "batches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    batch_code: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    variety: Mapped[str] = mapped_column(String(80), default="Unknown")
    quantity_kg: Mapped[float] = mapped_column(Float)
    farmer_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    source_location: Mapped[str] = mapped_column(String(160))
    state: Mapped[str] = mapped_column(String(80), default="Karnataka")
    district: Mapped[str | None] = mapped_column(String(80), nullable=True)
    harvest_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    intended_market: Mapped[str | None] = mapped_column(String(120), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="created", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    images: Mapped[list[BatchImage]] = relationship(back_populates="batch", cascade="all, delete-orphan")
    assessment: Mapped[QualityAssessment | None] = relationship(back_populates="batch", uselist=False, cascade="all, delete-orphan")
    recommendation: Mapped[Recommendation | None] = relationship(back_populates="batch", uselist=False, cascade="all, delete-orphan")
    feedback: Mapped[list[Feedback]] = relationship(back_populates="batch", cascade="all, delete-orphan")


class BatchImage(Base):
    __tablename__ = "batch_images"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey("batches.id", ondelete="CASCADE"), index=True)
    file_name: Mapped[str] = mapped_column(String(255))
    file_path: Mapped[str] = mapped_column(String(500))
    annotated_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    mime_type: Mapped[str] = mapped_column(String(80))
    analysis_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    batch: Mapped[Batch] = relationship(back_populates="images")


class QualityAssessment(Base):
    __tablename__ = "quality_assessments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey("batches.id", ondelete="CASCADE"), unique=True, index=True)
    quality_score: Mapped[float] = mapped_column(Float)
    quality_grade: Mapped[str] = mapped_column(String(32))
    commercial_class: Mapped[str] = mapped_column(String(64))
    rejection_probability: Mapped[float] = mapped_column(Float)
    size_uniformity: Mapped[float] = mapped_column(Float)
    bruise_severity: Mapped[float] = mapped_column(Float)
    crack_severity: Mapped[float] = mapped_column(Float)
    scab_severity: Mapped[float] = mapped_column(Float)
    discoloration_severity: Mapped[float] = mapped_column(Float)
    deformity_severity: Mapped[float] = mapped_column(Float)
    sprout_severity: Mapped[float] = mapped_column(Float)
    surface_defect_severity: Mapped[float] = mapped_column(Float)
    confidence: Mapped[float] = mapped_column(Float)
    model_mode: Mapped[str] = mapped_column(String(40))
    feature_summary: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    batch: Mapped[Batch] = relationship(back_populates="assessment")


class Recommendation(Base):
    __tablename__ = "recommendations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey("batches.id", ondelete="CASCADE"), unique=True, index=True)
    recommended_action: Mapped[str] = mapped_column(String(32))
    recommended_market: Mapped[str] = mapped_column(String(160))
    recommended_timing: Mapped[str] = mapped_column(String(100))
    expected_selling_price: Mapped[float] = mapped_column(Float)
    expected_gross_revenue: Mapped[float] = mapped_column(Float)
    expected_net_profit: Mapped[float] = mapped_column(Float)
    expected_roi: Mapped[float] = mapped_column(Float)
    risk_score: Mapped[float] = mapped_column(Float)
    confidence: Mapped[float] = mapped_column(Float)
    alternatives: Mapped[list[dict[str, Any]]] = mapped_column(JSON)
    explanation: Mapped[list[str]] = mapped_column(JSON)
    cost_breakdown: Mapped[dict[str, float]] = mapped_column(JSON)
    decision_factors: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    batch: Mapped[Batch] = relationship(back_populates="recommendation")


class MarketState(Base):
    __tablename__ = "market_states"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(4), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    state_type: Mapped[str] = mapped_column(String(32), default="State")
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    source: Mapped[str] = mapped_column(String(100), default="Government of India state directory")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    mandis: Mapped[list[MandiDirectory]] = relationship(back_populates="state", cascade="all, delete-orphan")


class MandiDirectory(Base):
    __tablename__ = "mandi_directory"
    __table_args__ = (
        UniqueConstraint("state_id", "district", "market", name="uq_mandi_directory_location"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    state_id: Mapped[int] = mapped_column(ForeignKey("market_states.id", ondelete="CASCADE"), index=True)
    district: Mapped[str] = mapped_column(String(100), index=True)
    market: Mapped[str] = mapped_column(String(160), index=True)
    source: Mapped[str] = mapped_column(String(120), default="data.gov.in / AGMARKNET")
    source_market_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_enam: Mapped[bool | None] = mapped_column(Boolean, nullable=True, default=None)
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    state: Mapped[MarketState] = relationship(back_populates="mandis")


class MarketPrice(Base):
    __tablename__ = "market_prices"
    __table_args__ = (
        UniqueConstraint(
            "state", "district", "market", "commodity", "variety", "grade", "arrival_date",
            name="uq_market_price_observation",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    state: Mapped[str] = mapped_column(String(80), index=True)
    district: Mapped[str] = mapped_column(String(80), index=True)
    market: Mapped[str] = mapped_column(String(120), index=True)
    commodity: Mapped[str] = mapped_column(String(80), default="Potato")
    variety: Mapped[str] = mapped_column(String(80), default="Local")
    grade: Mapped[str] = mapped_column(String(40), default="FAQ")
    arrival_date: Mapped[date] = mapped_column(Date, index=True)
    min_price: Mapped[float] = mapped_column(Float)
    max_price: Mapped[float] = mapped_column(Float)
    modal_price: Mapped[float] = mapped_column(Float)
    source: Mapped[str] = mapped_column(String(100), default="seed")
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class PriceModelVersion(Base):
    __tablename__ = "price_model_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    model_name: Mapped[str] = mapped_column(String(80), index=True)
    model_version: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    feature_version: Mapped[str] = mapped_column(String(40), default="forecast-v2")
    training_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    training_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    training_rows: Mapped[int] = mapped_column(Integer, default=0)
    markets: Mapped[int] = mapped_column(Integer, default=0)
    metrics_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    artifact_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class PriceForecast(Base):
    __tablename__ = "price_forecasts"
    __table_args__ = (
        UniqueConstraint(
            "state", "district", "market", "variety", "grade",
            "forecast_origin", "target_date", "model_version",
            name="uq_price_forecast_snapshot",
        ),
        Index("ix_price_forecast_lookup", "market", "variety", "forecast_origin", "target_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    state: Mapped[str] = mapped_column(String(80), index=True)
    district: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    market: Mapped[str | None] = mapped_column(String(160), nullable=True, index=True)
    variety: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    grade: Mapped[str | None] = mapped_column(String(40), nullable=True)
    forecast_origin: Mapped[date] = mapped_column(Date, index=True)
    target_date: Mapped[date] = mapped_column(Date, index=True)
    horizon_days: Mapped[int] = mapped_column(Integer)
    predicted_price: Mapped[float] = mapped_column(Float)
    lower_bound: Mapped[float] = mapped_column(Float)
    upper_bound: Mapped[float] = mapped_column(Float)
    confidence: Mapped[str] = mapped_column(String(20), default="low")
    model_name: Mapped[str] = mapped_column(String(80))
    model_version: Mapped[str] = mapped_column(String(120), index=True)
    actual_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    absolute_error: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class MarketSyncRun(Base):
    __tablename__ = "market_sync_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source: Mapped[str] = mapped_column(String(100), default="data.gov.in / AGMARKNET")
    resource_id: Mapped[str] = mapped_column(String(80))
    state: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(24), default="running", index=True)
    records_received: Mapped[int] = mapped_column(Integer, default=0)
    records_inserted: Mapped[int] = mapped_column(Integer, default=0)
    records_updated: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class NewsArticle(Base):
    __tablename__ = "news_articles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source: Mapped[str] = mapped_column(String(140), index=True)
    title: Mapped[str] = mapped_column(String(500))
    summary: Mapped[str] = mapped_column(Text, default="")
    url: Mapped[str] = mapped_column(String(1000), unique=True, index=True)
    image_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    category: Mapped[str] = mapped_column(String(80), default="Potato industry", index=True)
    language: Mapped[str] = mapped_column(String(12), default="en")
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class Feedback(Base):
    __tablename__ = "feedback"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey("batches.id", ondelete="CASCADE"), index=True)
    action_taken: Mapped[str] = mapped_column(String(40))
    actual_price_per_quintal: Mapped[float | None] = mapped_column(Float, nullable=True)
    actual_profit: Mapped[float | None] = mapped_column(Float, nullable=True)
    rating: Mapped[int] = mapped_column(Integer)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    batch: Mapped[Batch] = relationship(back_populates="feedback")


class TradeListing(Base):
    __tablename__ = "trade_listings"
    __table_args__ = (
        UniqueConstraint("listing_code", name="uq_trade_listing_code"),
        UniqueConstraint("idempotency_key", name="uq_trade_listing_idempotency_key"),
        Index("ix_trade_listing_discovery", "status", "listing_type", "state", "district", "variety"),
        Index("ix_trade_listing_price_created", "price_per_quintal", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    listing_code: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    listing_type: Mapped[str] = mapped_column(String(8), index=True)
    owner_ref: Mapped[str] = mapped_column(String(160), index=True)
    owner_name: Mapped[str] = mapped_column(String(120))
    contact_phone: Mapped[str | None] = mapped_column(String(24), nullable=True)
    variety: Mapped[str] = mapped_column(String(80), index=True)
    quantity_kg: Mapped[float] = mapped_column(Float)
    price_per_quintal: Mapped[float] = mapped_column(Float, index=True)
    state: Mapped[str] = mapped_column(String(80), index=True)
    district: Mapped[str] = mapped_column(String(100), index=True)
    location: Mapped[str] = mapped_column(String(160))
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="ACTIVE", index=True)
    source_batch_id: Mapped[int | None] = mapped_column(ForeignKey("batches.id", ondelete="SET NULL"), nullable=True, index=True)
    quality_grade: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    quality_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    size_class: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    verified_quality: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(128), nullable=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class TradeFavorite(Base):
    __tablename__ = "trade_favorites"
    __table_args__ = (
        UniqueConstraint("owner_ref", "listing_id", name="uq_trade_favorite_owner_listing"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_ref: Mapped[str] = mapped_column(String(160), index=True)
    listing_id: Mapped[int] = mapped_column(ForeignKey("trade_listings.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class ColdStorageFacility(Base):
    __tablename__ = "cold_storage_facilities"
    __table_args__ = (
        Index("ix_cold_storage_location", "state", "district"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(160), index=True)
    state: Mapped[str] = mapped_column(String(80), index=True)
    district: Mapped[str] = mapped_column(String(100), index=True)
    location: Mapped[str] = mapped_column(String(180))
    total_capacity_tonnes: Mapped[float] = mapped_column(Float)
    available_capacity_tonnes: Mapped[float] = mapped_column(Float)
    estimated_cost_per_quintal_day: Mapped[float] = mapped_column(Float)
    phone: Mapped[str | None] = mapped_column(String(24), nullable=True)
    source: Mapped[str] = mapped_column(String(120), default="seeded demonstration directory")
    verified: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class TransportProvider(Base):
    __tablename__ = "transport_providers"
    __table_args__ = (
        Index("ix_transport_provider_location", "state", "district"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(160), index=True)
    state: Mapped[str] = mapped_column(String(80), index=True)
    district: Mapped[str] = mapped_column(String(100), index=True)
    base_location: Mapped[str] = mapped_column(String(180))
    vehicle_types: Mapped[list[str]] = mapped_column(JSON, default=list)
    rate_per_km_tonne: Mapped[float] = mapped_column(Float)
    phone: Mapped[str | None] = mapped_column(String(24), nullable=True)
    source: Mapped[str] = mapped_column(String(120), default="seeded demonstration directory")
    verified: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
