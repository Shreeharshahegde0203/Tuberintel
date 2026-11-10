"""Validated price forecasting model registry and forecast snapshots."""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0005_price_forecasting"
down_revision: Union[str, None] = "0004_trade_and_services"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "price_model_versions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("model_name", sa.String(80), nullable=False),
        sa.Column("model_version", sa.String(120), nullable=False),
        sa.Column("feature_version", sa.String(40), nullable=False),
        sa.Column("training_start", sa.Date()),
        sa.Column("training_end", sa.Date()),
        sa.Column("training_rows", sa.Integer(), nullable=False),
        sa.Column("markets", sa.Integer(), nullable=False),
        sa.Column("metrics_json", sa.JSON(), nullable=False),
        sa.Column("artifact_path", sa.String(500)),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("model_version", name="uq_price_model_version"),
    )
    op.create_index("ix_price_model_versions_model_name", "price_model_versions", ["model_name"])
    op.create_index("ix_price_model_versions_model_version", "price_model_versions", ["model_version"], unique=True)
    op.create_index("ix_price_model_versions_active", "price_model_versions", ["active"])

    op.create_table(
        "price_forecasts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("state", sa.String(80), nullable=False),
        sa.Column("district", sa.String(100)),
        sa.Column("market", sa.String(160)),
        sa.Column("variety", sa.String(80)),
        sa.Column("grade", sa.String(40)),
        sa.Column("forecast_origin", sa.Date(), nullable=False),
        sa.Column("target_date", sa.Date(), nullable=False),
        sa.Column("horizon_days", sa.Integer(), nullable=False),
        sa.Column("predicted_price", sa.Float(), nullable=False),
        sa.Column("lower_bound", sa.Float(), nullable=False),
        sa.Column("upper_bound", sa.Float(), nullable=False),
        sa.Column("confidence", sa.String(20), nullable=False),
        sa.Column("model_name", sa.String(80), nullable=False),
        sa.Column("model_version", sa.String(120), nullable=False),
        sa.Column("actual_price", sa.Float()),
        sa.Column("absolute_error", sa.Float()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "state", "district", "market", "variety", "grade", "forecast_origin", "target_date", "model_version",
            name="uq_price_forecast_snapshot",
        ),
    )
    for column in ("state", "district", "market", "variety", "forecast_origin", "target_date", "model_version"):
        op.create_index(f"ix_price_forecasts_{column}", "price_forecasts", [column])
    op.create_index(
        "ix_price_forecast_lookup",
        "price_forecasts",
        ["market", "variety", "forecast_origin", "target_date"],
    )


def downgrade() -> None:
    op.drop_table("price_forecasts")
    op.drop_table("price_model_versions")
