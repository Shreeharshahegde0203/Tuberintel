"""Market intelligence, synchronization audit and potato news cache."""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0002_market_intelligence"
down_revision: Union[str, None] = "0001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Existing demonstration databases may contain duplicate seed observations.
    # Keep the earliest row before adding the business key.
    connection = op.get_bind()
    if connection.dialect.name == "postgresql":
        connection.execute(sa.text("""
            DELETE FROM market_prices a
            USING market_prices b
            WHERE a.id > b.id
              AND a.state = b.state
              AND a.district = b.district
              AND a.market = b.market
              AND a.commodity = b.commodity
              AND a.variety = b.variety
              AND a.grade = b.grade
              AND a.arrival_date = b.arrival_date
        """))
    else:
        connection.execute(sa.text("""
            DELETE FROM market_prices
            WHERE id NOT IN (
                SELECT MIN(id) FROM market_prices
                GROUP BY state, district, market, commodity, variety, grade, arrival_date
            )
        """))

    with op.batch_alter_table("market_prices") as batch_op:
        batch_op.create_unique_constraint(
            "uq_market_price_observation",
            ["state", "district", "market", "commodity", "variety", "grade", "arrival_date"],
        )

    op.create_table(
        "market_sync_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source", sa.String(100), nullable=False),
        sa.Column("resource_id", sa.String(80), nullable=False),
        sa.Column("state", sa.String(80)),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("records_received", sa.Integer(), nullable=False),
        sa.Column("records_inserted", sa.Integer(), nullable=False),
        sa.Column("records_updated", sa.Integer(), nullable=False),
        sa.Column("error", sa.Text()),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_market_sync_runs_state", "market_sync_runs", ["state"])
    op.create_index("ix_market_sync_runs_status", "market_sync_runs", ["status"])

    op.create_table(
        "news_articles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source", sa.String(140), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("url", sa.String(1000), nullable=False),
        sa.Column("image_url", sa.String(1000)),
        sa.Column("category", sa.String(80), nullable=False),
        sa.Column("language", sa.String(12), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True)),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("url", name="uq_news_articles_url"),
    )
    op.create_index("ix_news_articles_source", "news_articles", ["source"])
    op.create_index("ix_news_articles_url", "news_articles", ["url"], unique=True)
    op.create_index("ix_news_articles_category", "news_articles", ["category"])
    op.create_index("ix_news_articles_published_at", "news_articles", ["published_at"])


def downgrade() -> None:
    op.drop_table("news_articles")
    op.drop_table("market_sync_runs")
    with op.batch_alter_table("market_prices") as batch_op:
        batch_op.drop_constraint("uq_market_price_observation", type_="unique")
