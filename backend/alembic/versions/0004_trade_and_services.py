"""Trade marketplace, favorites, cold storage and transport directories."""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0004_trade_and_services"
down_revision: Union[str, None] = "0003_mandi_directory"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "trade_listings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("listing_code", sa.String(40), nullable=False),
        sa.Column("listing_type", sa.String(8), nullable=False),
        sa.Column("owner_ref", sa.String(160), nullable=False),
        sa.Column("owner_name", sa.String(120), nullable=False),
        sa.Column("contact_phone", sa.String(24)),
        sa.Column("variety", sa.String(80), nullable=False),
        sa.Column("quantity_kg", sa.Float(), nullable=False),
        sa.Column("price_per_quintal", sa.Float(), nullable=False),
        sa.Column("state", sa.String(80), nullable=False),
        sa.Column("district", sa.String(100), nullable=False),
        sa.Column("location", sa.String(160), nullable=False),
        sa.Column("notes", sa.Text()),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("source_batch_id", sa.Integer(), sa.ForeignKey("batches.id", ondelete="SET NULL")),
        sa.Column("quality_grade", sa.String(32)),
        sa.Column("quality_score", sa.Float()),
        sa.Column("size_class", sa.String(64)),
        sa.Column("verified_quality", sa.Boolean(), nullable=False),
        sa.Column("idempotency_key", sa.String(128)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("listing_code", name="uq_trade_listing_code"),
        sa.UniqueConstraint("idempotency_key", name="uq_trade_listing_idempotency_key"),
    )
    for col in ("listing_code", "listing_type", "owner_ref", "variety", "price_per_quintal", "state", "district", "status", "source_batch_id", "quality_grade", "size_class", "verified_quality", "created_at"):
        op.create_index(f"ix_trade_listings_{col}", "trade_listings", [col], unique=(col == "listing_code"))
    op.create_index("ix_trade_listing_discovery", "trade_listings", ["status", "listing_type", "state", "district", "variety"])
    op.create_index("ix_trade_listing_price_created", "trade_listings", ["price_per_quintal", "created_at"])

    op.create_table(
        "trade_favorites",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("owner_ref", sa.String(160), nullable=False),
        sa.Column("listing_id", sa.Integer(), sa.ForeignKey("trade_listings.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("owner_ref", "listing_id", name="uq_trade_favorite_owner_listing"),
    )
    op.create_index("ix_trade_favorites_owner_ref", "trade_favorites", ["owner_ref"])
    op.create_index("ix_trade_favorites_listing_id", "trade_favorites", ["listing_id"])

    op.create_table(
        "cold_storage_facilities",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("state", sa.String(80), nullable=False),
        sa.Column("district", sa.String(100), nullable=False),
        sa.Column("location", sa.String(180), nullable=False),
        sa.Column("total_capacity_tonnes", sa.Float(), nullable=False),
        sa.Column("available_capacity_tonnes", sa.Float(), nullable=False),
        sa.Column("estimated_cost_per_quintal_day", sa.Float(), nullable=False),
        sa.Column("phone", sa.String(24)),
        sa.Column("source", sa.String(120), nullable=False),
        sa.Column("verified", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    for col in ("name", "state", "district", "verified"):
        op.create_index(f"ix_cold_storage_facilities_{col}", "cold_storage_facilities", [col])
    op.create_index("ix_cold_storage_location", "cold_storage_facilities", ["state", "district"])

    op.create_table(
        "transport_providers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("state", sa.String(80), nullable=False),
        sa.Column("district", sa.String(100), nullable=False),
        sa.Column("base_location", sa.String(180), nullable=False),
        sa.Column("vehicle_types", sa.JSON(), nullable=False),
        sa.Column("rate_per_km_tonne", sa.Float(), nullable=False),
        sa.Column("phone", sa.String(24)),
        sa.Column("source", sa.String(120), nullable=False),
        sa.Column("verified", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    for col in ("name", "state", "district", "verified"):
        op.create_index(f"ix_transport_providers_{col}", "transport_providers", [col])
    op.create_index("ix_transport_provider_location", "transport_providers", ["state", "district"])


def downgrade() -> None:
    op.drop_table("transport_providers")
    op.drop_table("cold_storage_facilities")
    op.drop_table("trade_favorites")
    op.drop_table("trade_listings")
