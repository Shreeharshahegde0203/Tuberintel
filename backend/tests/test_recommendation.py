from __future__ import annotations

from datetime import date

from app.models import Batch, MarketPrice, QualityAssessment
from app.schemas.batches import AnalysisOptions
from app.services.recommendation_engine import RecommendationEngine


def assessment(grade: str, quality: float, rejection: float, sprouts: float = 5) -> QualityAssessment:
    return QualityAssessment(
        batch_id=1,
        quality_score=quality,
        quality_grade=grade,
        commercial_class="test",
        rejection_probability=rejection,
        size_uniformity=85,
        bruise_severity=18,
        crack_severity=8,
        scab_severity=14,
        discoloration_severity=10,
        deformity_severity=8,
        sprout_severity=sprouts,
        surface_defect_severity=15,
        confidence=82,
        model_mode="test",
        feature_summary={},
    )


def test_low_grade_storage_is_not_blindly_preferred() -> None:
    batch = Batch(batch_code="T", variety="Local", quantity_kg=1000, source_location="Kolar", state="Karnataka")
    market = MarketPrice(
        state="Karnataka", district="Kolar", market="Kolar APMC", arrival_date=date.today(),
        min_price=1800, max_price=2400, modal_price=2200,
    )
    forecast = [{"date": date.today(), "predicted_price": 2350, "lower_bound": 2200, "upper_bound": 2500} for _ in range(30)]
    result = RecommendationEngine().evaluate(batch, assessment("D", 44, 52, sprouts=42), [market], forecast, AnalysisOptions())
    assert result["recommended_action"] not in {"STORE", "WAIT"}
    assert len(result["decision_factors"]) == 5


def test_kannada_recommendation_explanation() -> None:
    batch = Batch(batch_code="KN", variety="Kufri Jyoti", quantity_kg=800, source_location="Kolar", state="Karnataka")
    market = MarketPrice(
        state="Karnataka", district="Kolar", market="Kolar APMC", arrival_date=date.today(),
        min_price=1800, max_price=2400, modal_price=2200,
    )
    forecast = [{"date": date.today(), "predicted_price": 2250, "lower_bound": 2100, "upper_bound": 2400} for _ in range(30)]
    result = RecommendationEngine().evaluate(batch, assessment("B", 78, 12), [market], forecast, AnalysisOptions(language="kn"))
    joined = " ".join(result["explanation"])
    assert any("\u0c80" <= char <= "\u0cff" for char in joined)
    assert result["alternatives"][0]["title"]
