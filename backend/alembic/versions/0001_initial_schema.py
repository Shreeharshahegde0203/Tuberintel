"""Reconciled initial TuberIntel schema."""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def has_table(inspector: sa.Inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def has_column(inspector: sa.Inspector, table_name: str, column_name: str) -> bool:
    return column_name in {column["name"] for column in inspector.get_columns(table_name)}


def has_index(inspector: sa.Inspector, table_name: str, index_name: str) -> bool:
    return index_name in {index["name"] for index in inspector.get_indexes(table_name)}


def has_unique(inspector: sa.Inspector, table_name: str, constraint_name: str) -> bool:
    return constraint_name in {item["name"] for item in inspector.get_unique_constraints(table_name)}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not has_table(inspector, "batches"):
        op.create_table(
            "batches",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("batch_code", sa.String(32), nullable=False),
            sa.Column("owner_user_id", sa.String(128)),
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
    else:
        if not has_column(inspector, "batches", "owner_user_id"):
            op.add_column("batches", sa.Column("owner_user_id", sa.String(128), nullable=True))

    if not has_index(inspector, "batches", "ix_batches_batch_code"):
        op.create_index("ix_batches_batch_code", "batches", ["batch_code"], unique=True)
    if not has_index(inspector, "batches", "ix_batches_status"):
        op.create_index("ix_batches_status", "batches", ["status"])
    if not has_index(inspector, "batches", "ix_batches_owner_user_id"):
        op.create_index("ix_batches_owner_user_id", "batches", ["owner_user_id"])

    inspector = sa.inspect(bind)
    if not has_table(inspector, "batch_images"):
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
    if not has_index(inspector, "batch_images", "ix_batch_images_batch_id"):
        op.create_index("ix_batch_images_batch_id", "batch_images", ["batch_id"])

    if not has_table(inspector, "quality_assessments"):
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
    if not has_index(inspector, "quality_assessments", "ix_quality_assessments_batch_id"):
        op.create_index("ix_quality_assessments_batch_id", "quality_assessments", ["batch_id"], unique=True)

    if not has_table(inspector, "recommendations"):
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
    if not has_index(inspector, "recommendations", "ix_recommendations_batch_id"):
        op.create_index("ix_recommendations_batch_id", "recommendations", ["batch_id"], unique=True)

    if not has_table(inspector, "market_states"):
        op.create_table(
            "market_states",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("name", sa.String(120), nullable=False),
            sa.Column("normalized_name", sa.String(120), nullable=False),
            sa.Column("code", sa.String(16)),
            sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("normalized_name", name="uq_market_states_normalized_name"),
        )
    if not has_index(inspector, "market_states", "ix_market_states_name"):
        op.create_index("ix_market_states_name", "market_states", ["name"])
    if not has_index(inspector, "market_states", "ix_market_states_normalized_name"):
        op.create_index("ix_market_states_normalized_name", "market_states", ["normalized_name"])
    if not has_index(inspector, "market_states", "ix_market_states_active"):
        op.create_index("ix_market_states_active", "market_states", ["active"])

    if not has_table(inspector, "market_districts"):
        op.create_table(
            "market_districts",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("state_id", sa.Integer(), sa.ForeignKey("market_states.id", ondelete="CASCADE"), nullable=False),
            sa.Column("name", sa.String(120), nullable=False),
            sa.Column("normalized_name", sa.String(120), nullable=False),
            sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("state_id", "normalized_name", name="uq_market_districts_state_normalized_name"),
        )
    if not has_index(inspector, "market_districts", "ix_market_districts_state_id"):
        op.create_index("ix_market_districts_state_id", "market_districts", ["state_id"])
    if not has_index(inspector, "market_districts", "ix_market_districts_name"):
        op.create_index("ix_market_districts_name", "market_districts", ["name"])
    if not has_index(inspector, "market_districts", "ix_market_districts_normalized_name"):
        op.create_index("ix_market_districts_normalized_name", "market_districts", ["normalized_name"])
    if not has_index(inspector, "market_districts", "ix_market_districts_active"):
        op.create_index("ix_market_districts_active", "market_districts", ["active"])

    if not has_table(inspector, "markets"):
        op.create_table(
            "markets",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("state_id", sa.Integer(), sa.ForeignKey("market_states.id", ondelete="CASCADE"), nullable=False),
            sa.Column("district_id", sa.Integer(), sa.ForeignKey("market_districts.id", ondelete="CASCADE"), nullable=False),
            sa.Column("name", sa.String(160), nullable=False),
            sa.Column("normalized_name", sa.String(160), nullable=False),
            sa.Column("external_market_name", sa.String(160)),
            sa.Column("external_id", sa.String(120)),
            sa.Column("source", sa.String(80), nullable=False),
            sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("latitude", sa.Float()),
            sa.Column("longitude", sa.Float()),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("state_id", "district_id", "normalized_name", name="uq_markets_state_district_normalized_name"),
        )
    if not has_index(inspector, "markets", "ix_markets_state_id"):
        op.create_index("ix_markets_state_id", "markets", ["state_id"])
    if not has_index(inspector, "markets", "ix_markets_district_id"):
        op.create_index("ix_markets_district_id", "markets", ["district_id"])
    if not has_index(inspector, "markets", "ix_markets_name"):
        op.create_index("ix_markets_name", "markets", ["name"])
    if not has_index(inspector, "markets", "ix_markets_normalized_name"):
        op.create_index("ix_markets_normalized_name", "markets", ["normalized_name"])
    if not has_index(inspector, "markets", "ix_markets_external_id"):
        op.create_index("ix_markets_external_id", "markets", ["external_id"])
    if not has_index(inspector, "markets", "ix_markets_active"):
        op.create_index("ix_markets_active", "markets", ["active"])
    if not has_index(inspector, "markets", "ix_markets_source_active"):
        op.create_index("ix_markets_source_active", "markets", ["source", "active"])

    inspector = sa.inspect(bind)
    if not has_table(inspector, "market_prices"):
        op.create_table(
            "market_prices",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("market_id", sa.Integer(), sa.ForeignKey("markets.id", ondelete="SET NULL")),
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
            sa.Column("source_record_id", sa.String(120)),
        )
    else:
        if not has_column(inspector, "market_prices", "market_id"):
            op.add_column("market_prices", sa.Column("market_id", sa.Integer(), nullable=True))
        if not has_column(inspector, "market_prices", "state"):
            op.add_column("market_prices", sa.Column("state", sa.String(80), nullable=True))
        if not has_column(inspector, "market_prices", "district"):
            op.add_column("market_prices", sa.Column("district", sa.String(80), nullable=True))
        if not has_column(inspector, "market_prices", "market"):
            op.add_column("market_prices", sa.Column("market", sa.String(120), nullable=True))
        if not has_column(inspector, "market_prices", "commodity"):
            op.add_column("market_prices", sa.Column("commodity", sa.String(80), nullable=True))
        if not has_column(inspector, "market_prices", "variety"):
            op.add_column("market_prices", sa.Column("variety", sa.String(80), nullable=True))
        if not has_column(inspector, "market_prices", "grade"):
            op.add_column("market_prices", sa.Column("grade", sa.String(40), nullable=True))
        if not has_column(inspector, "market_prices", "arrival_date"):
            op.add_column("market_prices", sa.Column("arrival_date", sa.Date(), nullable=True))
        if not has_column(inspector, "market_prices", "min_price"):
            op.add_column("market_prices", sa.Column("min_price", sa.Float(), nullable=True))
        if not has_column(inspector, "market_prices", "max_price"):
            op.add_column("market_prices", sa.Column("max_price", sa.Float(), nullable=True))
        if not has_column(inspector, "market_prices", "modal_price"):
            op.add_column("market_prices", sa.Column("modal_price", sa.Float(), nullable=True))
        if not has_column(inspector, "market_prices", "source"):
            op.add_column("market_prices", sa.Column("source", sa.String(100), nullable=True))
        if not has_column(inspector, "market_prices", "fetched_at"):
            op.add_column("market_prices", sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=True))
        if not has_column(inspector, "market_prices", "source_record_id"):
            op.add_column("market_prices", sa.Column("source_record_id", sa.String(120), nullable=True))
    if not has_index(inspector, "market_prices", "ix_market_prices_market_id"):
        op.create_index("ix_market_prices_market_id", "market_prices", ["market_id"])
    for column in ("state", "district", "market", "arrival_date", "source_record_id"):
        index_name = f"ix_market_prices_{column}"
        if not has_index(inspector, "market_prices", index_name):
            op.create_index(index_name, "market_prices", [column])
    if not has_index(inspector, "market_prices", "ix_market_prices_state_district_market"):
        op.create_index("ix_market_prices_state_district_market", "market_prices", ["state", "district", "market"])
    if not has_index(inspector, "market_prices", "ix_market_prices_commodity_variety_date"):
        op.create_index("ix_market_prices_commodity_variety_date", "market_prices", ["commodity", "variety", "arrival_date"])

    if not has_table(inspector, "market_sync_runs"):
        op.create_table(
            "market_sync_runs",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("source", sa.String(80), nullable=False),
            sa.Column("state", sa.String(120)),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("completed_at", sa.DateTime(timezone=True)),
            sa.Column("status", sa.String(32), nullable=False),
            sa.Column("records_received", sa.Integer(), nullable=False),
            sa.Column("records_inserted", sa.Integer(), nullable=False),
            sa.Column("records_updated", sa.Integer(), nullable=False),
            sa.Column("triggered_by", sa.String(128)),
            sa.Column("error_message", sa.Text()),
        )
    if not has_index(inspector, "market_sync_runs", "ix_market_sync_runs_source"):
        op.create_index("ix_market_sync_runs_source", "market_sync_runs", ["source"])
    if not has_index(inspector, "market_sync_runs", "ix_market_sync_runs_state"):
        op.create_index("ix_market_sync_runs_state", "market_sync_runs", ["state"])
    if not has_index(inspector, "market_sync_runs", "ix_market_sync_runs_status"):
        op.create_index("ix_market_sync_runs_status", "market_sync_runs", ["status"])
    if not has_index(inspector, "market_sync_runs", "ix_market_sync_runs_source_status"):
        op.create_index("ix_market_sync_runs_source_status", "market_sync_runs", ["source", "status"])

    if not has_table(inspector, "feedback"):
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
    if not has_index(inspector, "feedback", "ix_feedback_batch_id"):
        op.create_index("ix_feedback_batch_id", "feedback", ["batch_id"])


def downgrade() -> None:
    for table in [
        "feedback",
        "market_sync_runs",
        "market_prices",
        "markets",
        "market_districts",
        "market_states",
        "recommendations",
        "quality_assessments",
        "batch_images",
        "batches",
    ]:
        op.drop_table(table)
