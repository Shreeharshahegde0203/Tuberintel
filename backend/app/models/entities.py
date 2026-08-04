from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Batch(Base):
    __tablename__ = "batches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    batch_code: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    owner_user_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
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


class MarketPrice(Base):
    __tablename__ = "market_prices"
    __table_args__ = (
        UniqueConstraint(
            "market_id",
            "commodity",
            "variety",
            "grade",
            "arrival_date",
            "source",
            name="uq_market_prices_market_commodity_variety_grade_date_source",
        ),
        Index("ix_market_prices_state_district_market", "state", "district", "market"),
        Index("ix_market_prices_commodity_variety_date", "commodity", "variety", "arrival_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    market_id: Mapped[int | None] = mapped_column(ForeignKey("markets.id", ondelete="SET NULL"), nullable=True, index=True)
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
    source_record_id: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)

    market_ref: Mapped["Market | None"] = relationship(back_populates="prices")


class MarketState(Base):
    __tablename__ = "market_states"
    __table_args__ = (
        UniqueConstraint("normalized_name", name="uq_market_states_normalized_name"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), index=True)
    normalized_name: Mapped[str] = mapped_column(String(120), index=True)
    code: Mapped[str | None] = mapped_column(String(16), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    districts: Mapped[list["MarketDistrict"]] = relationship(back_populates="state_ref", cascade="all, delete-orphan")
    markets: Mapped[list["Market"]] = relationship(back_populates="state_ref")


class MarketDistrict(Base):
    __tablename__ = "market_districts"
    __table_args__ = (
        UniqueConstraint("state_id", "normalized_name", name="uq_market_districts_state_normalized_name"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    state_id: Mapped[int] = mapped_column(ForeignKey("market_states.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(120), index=True)
    normalized_name: Mapped[str] = mapped_column(String(120), index=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    state_ref: Mapped["MarketState"] = relationship(back_populates="districts")
    markets: Mapped[list["Market"]] = relationship(back_populates="district_ref")


class Market(Base):
    __tablename__ = "markets"
    __table_args__ = (
        UniqueConstraint("state_id", "district_id", "normalized_name", name="uq_markets_state_district_normalized_name"),
        Index("ix_markets_source_active", "source", "active"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    state_id: Mapped[int] = mapped_column(ForeignKey("market_states.id", ondelete="CASCADE"), index=True)
    district_id: Mapped[int] = mapped_column(ForeignKey("market_districts.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(160), index=True)
    normalized_name: Mapped[str] = mapped_column(String(160), index=True)
    external_market_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    external_id: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    source: Mapped[str] = mapped_column(String(80), default="manual")
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    state_ref: Mapped["MarketState"] = relationship(back_populates="markets")
    district_ref: Mapped["MarketDistrict"] = relationship(back_populates="markets")
    prices: Mapped[list[MarketPrice]] = relationship(back_populates="market_ref")


class MarketSyncRun(Base):
    __tablename__ = "market_sync_runs"
    __table_args__ = (
        Index("ix_market_sync_runs_source_status", "source", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source: Mapped[str] = mapped_column(String(80), index=True)
    state: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(32), index=True)
    records_received: Mapped[int] = mapped_column(Integer, default=0)
    records_inserted: Mapped[int] = mapped_column(Integer, default=0)
    records_updated: Mapped[int] = mapped_column(Integer, default=0)
    triggered_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)


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
