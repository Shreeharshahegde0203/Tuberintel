"""Initial TuberIntel relational schema."""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "batches",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("batch_code", sa.String(32), nullable=False),
        sa.Column("variety", sa.String(80), nullable=False),
        sa.Column("quantity_kg", sa.Float(), nullable=False),
        sa.Column("farmer_name", sa.String(120)),
        sa.Column("source_location", sa.String(160), nullable=False),
        sa.Column("state", sa.String(80), nullable=False),
        sa.Column("district", sa.String(80)),
        sa.Column("harvest_date", sa.Date()),
        sa.Column("intended_market", sa.String(120)),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("batch_code"),
    )
    op.create_index("ix_batches_batch_code", "batches", ["batch_code"], unique=True)
    op.create_index("ix_batches_status", "batches", ["status"])
    op.create_table(
        "batch_images",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("batch_id", sa.Integer(), sa.ForeignKey("batches.id", ondelete="CASCADE"), nullable=False),
        sa.Column("file_name", sa.String(255), nullable=False),
        sa.Column("file_path", sa.String(500), nullable=False),
        sa.Column("annotated_path", sa.String(500)),
        sa.Column("mime_type", sa.String(80), nullable=False),
        sa.Column("analysis_json", sa.JSON()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_batch_images_batch_id", "batch_images", ["batch_id"])
    op.create_table(
        "quality_assessments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("batch_id", sa.Integer(), sa.ForeignKey("batches.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("quality_score", sa.Float(), nullable=False),
        sa.Column("quality_grade", sa.String(32), nullable=False),
        sa.Column("commercial_class", sa.String(64), nullable=False),
        sa.Column("rejection_probability", sa.Float(), nullable=False),
        sa.Column("size_uniformity", sa.Float(), nullable=False),
        sa.Column("bruise_severity", sa.Float(), nullable=False),
        sa.Column("crack_severity", sa.Float(), nullable=False),
        sa.Column("scab_severity", sa.Float(), nullable=False),
        sa.Column("discoloration_severity", sa.Float(), nullable=False),
        sa.Column("deformity_severity", sa.Float(), nullable=False),
        sa.Column("sprout_severity", sa.Float(), nullable=False),
        sa.Column("surface_defect_severity", sa.Float(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("model_mode", sa.String(40), nullable=False),
        sa.Column("feature_summary", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_quality_assessments_batch_id", "quality_assessments", ["batch_id"], unique=True)
    op.create_table(
        "recommendations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("batch_id", sa.Integer(), sa.ForeignKey("batches.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("recommended_action", sa.String(32), nullable=False),
        sa.Column("recommended_market", sa.String(160), nullable=False),
        sa.Column("recommended_timing", sa.String(100), nullable=False),
        sa.Column("expected_selling_price", sa.Float(), nullable=False),
        sa.Column("expected_gross_revenue", sa.Float(), nullable=False),
        sa.Column("expected_net_profit", sa.Float(), nullable=False),
        sa.Column("expected_roi", sa.Float(), nullable=False),
        sa.Column("risk_score", sa.Float(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("alternatives", sa.JSON(), nullable=False),
        sa.Column("explanation", sa.JSON(), nullable=False),
        sa.Column("cost_breakdown", sa.JSON(), nullable=False),
        sa.Column("decision_factors", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_recommendations_batch_id", "recommendations", ["batch_id"], unique=True)
    op.create_table(
        "market_prices",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("state", sa.String(80), nullable=False),
        sa.Column("district", sa.String(80), nullable=False),
        sa.Column("market", sa.String(120), nullable=False),
        sa.Column("commodity", sa.String(80), nullable=False),
        sa.Column("variety", sa.String(80), nullable=False),
        sa.Column("grade", sa.String(40), nullable=False),
        sa.Column("arrival_date", sa.Date(), nullable=False),
        sa.Column("min_price", sa.Float(), nullable=False),
        sa.Column("max_price", sa.Float(), nullable=False),
        sa.Column("modal_price", sa.Float(), nullable=False),
        sa.Column("source", sa.String(100), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
    )
    for column in ("state", "district", "market", "arrival_date"):
        op.create_index(f"ix_market_prices_{column}", "market_prices", [column])
    op.create_table(
        "feedback",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("batch_id", sa.Integer(), sa.ForeignKey("batches.id", ondelete="CASCADE"), nullable=False),
        sa.Column("action_taken", sa.String(40), nullable=False),
        sa.Column("actual_price_per_quintal", sa.Float()),
        sa.Column("actual_profit", sa.Float()),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_feedback_batch_id", "feedback", ["batch_id"])


def downgrade() -> None:
    for table in ["feedback", "market_prices", "recommendations", "quality_assessments", "batch_images", "batches"]:
        op.drop_table(table)
