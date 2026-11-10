from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class BatchCreate(BaseModel):
    variety: str = Field(min_length=1, max_length=80)
    quantity_kg: float = Field(gt=0, le=1_000_000)
    farmer_name: str | None = Field(default=None, max_length=120)
    source_location: str = Field(min_length=2, max_length=160)
    state: str = Field(default="Karnataka", min_length=2, max_length=80)
    district: str | None = Field(default=None, max_length=80)
    harvest_date: date | None = None
    intended_market: str | None = Field(default=None, max_length=120)


class BatchImageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    file_name: str
    mime_type: str
    image_url: str | None = None
    annotated_url: str | None = None
    analysis_json: dict[str, Any] | None = None


class QualityAssessmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    quality_score: float
    quality_grade: str
    commercial_class: str
    rejection_probability: float
    size_uniformity: float
    bruise_severity: float
    crack_severity: float
    scab_severity: float
    discoloration_severity: float
    deformity_severity: float
    sprout_severity: float
    surface_defect_severity: float
    confidence: float
    model_mode: str
    feature_summary: dict[str, Any]


class RecommendationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    recommended_action: str
    recommended_market: str
    recommended_timing: str
    expected_selling_price: float
    expected_gross_revenue: float
    expected_net_profit: float
    expected_roi: float
    risk_score: float
    confidence: float
    alternatives: list[dict[str, Any]]
    explanation: list[str]
    cost_breakdown: dict[str, float]
    decision_factors: list[dict[str, Any]]


class BatchRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    batch_code: str
    variety: str
    quantity_kg: float
    farmer_name: str | None
    source_location: str
    state: str
    district: str | None
    harvest_date: date | None
    intended_market: str | None
    status: str
    created_at: datetime
    updated_at: datetime
    images: list[BatchImageRead] = []
    assessment: QualityAssessmentRead | None = None
    recommendation: RecommendationRead | None = None


class BatchListItem(BaseModel):
    id: int
    batch_code: str
    variety: str
    quantity_kg: float
    source_location: str
    status: str
    created_at: datetime
    grade: str | None = None
    quality_score: float | None = None
    action: str | None = None
    expected_net_profit: float | None = None


class AnalysisOptions(BaseModel):
    # TUBERINTEL QUALITY VALUE V1: explicit pricing assumptions.
    quality_pricing_mode: Literal["estimated", "manual", "reference"] = "estimated"
    fresh_buyer_price_per_quintal: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    buyer_quality_discount_percent: float | None = Field(default=None, ge=0, le=100, allow_inf_nan=False)
    saleable_weight_percent: float | None = Field(default=None, ge=0, le=100, allow_inf_nan=False)
    language: Literal["en", "kn"] = "en"
    storage_cost_per_quintal_day: float = Field(default=8.0, ge=0)
    storage_days: int = Field(default=14, ge=0, le=180)
    expected_storage_loss_percent: float | None = Field(default=None, ge=0, le=100)
    transport_cost_per_km_tonne: float = Field(default=42.0, ge=0)
    distance_km: float = Field(default=65.0, ge=0, le=5000)
    processor_price_per_quintal: float | None = Field(default=None, ge=0)
    handling_cost_per_quintal: float = Field(default=35.0, ge=0)
    target_margin_percent: float = Field(default=10.0, ge=0, le=100)
    measured_length_mm: float | None = Field(default=None, gt=0, le=500)
    measured_width_mm: float | None = Field(default=None, gt=0, le=500)
    measurement_source: Literal["not_available", "manual", "potato_ruler", "calibrated_image"] = "not_available"


class FeedbackCreate(BaseModel):
    action_taken: str = Field(min_length=2, max_length=40)
    actual_price_per_quintal: float | None = Field(default=None, ge=0)
    actual_profit: float | None = None
    rating: int = Field(ge=1, le=5)
    notes: str | None = Field(default=None, max_length=2000)
