from pydantic import BaseModel

from app.schemas.batches import BatchListItem
from app.schemas.market import ForecastPoint


class DashboardSummary(BaseModel):
    total_batches: int
    analyzed_batches: int
    average_quality_score: float
    projected_value: float
    latest_modal_price: float
    price_change_percent: float
    recent_batches: list[BatchListItem]
    price_forecast: list[ForecastPoint]
    grade_distribution: dict[str, int]
    action_distribution: dict[str, int]
