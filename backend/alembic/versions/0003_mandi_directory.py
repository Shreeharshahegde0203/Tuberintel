"""Persist the canonical India state list and the synchronized mandi directory."""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0003_mandi_directory"
down_revision: Union[str, None] = "0002_market_intelligence"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "market_states",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(4), nullable=False),
        sa.Column("name", sa.String(80), nullable=False),
        sa.Column("state_type", sa.String(32), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("source", sa.String(100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("code", name="uq_market_states_code"),
        sa.UniqueConstraint("name", name="uq_market_states_name"),
    )
    op.create_index("ix_market_states_code", "market_states", ["code"], unique=True)
    op.create_index("ix_market_states_name", "market_states", ["name"], unique=True)
    op.create_index("ix_market_states_active", "market_states", ["active"])

    op.create_table(
        "mandi_directory",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("state_id", sa.Integer(), sa.ForeignKey("market_states.id", ondelete="CASCADE"), nullable=False),
        sa.Column("district", sa.String(100), nullable=False),
        sa.Column("market", sa.String(160), nullable=False),
        sa.Column("source", sa.String(120), nullable=False),
        sa.Column("source_market_id", sa.String(100)),
        sa.Column("is_enam", sa.Boolean()),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("state_id", "district", "market", name="uq_mandi_directory_location"),
    )
    op.create_index("ix_mandi_directory_state_id", "mandi_directory", ["state_id"])
    op.create_index("ix_mandi_directory_district", "mandi_directory", ["district"])
    op.create_index("ix_mandi_directory_market", "mandi_directory", ["market"])
    op.create_index("ix_mandi_directory_active", "mandi_directory", ["active"])
    op.create_index("ix_mandi_directory_last_seen_at", "mandi_directory", ["last_seen_at"])


def downgrade() -> None:
    op.drop_table("mandi_directory")
    op.drop_table("market_states")
