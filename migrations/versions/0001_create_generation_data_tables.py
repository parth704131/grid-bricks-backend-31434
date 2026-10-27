"""Create generation source tables."""

from alembic import op
import sqlalchemy as sa

revision = "0001_create_generation_tables"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "generation_actuals",
        sa.Column("start_time", sa.DateTime(timezone=True), primary_key=True),
        sa.Column("fuel_type", sa.String(32), primary_key=True),
        sa.Column("generation_mw", sa.Numeric(12, 3), nullable=False),
        sa.Column("ingested_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.CheckConstraint("generation_mw >= 0", name="ck_generation_actuals_generation_nonnegative"),
    )
    op.create_table(
        "generation_forecasts",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("publish_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fuel_type", sa.String(32), nullable=False),
        sa.Column("generation_mw", sa.Numeric(12, 3), nullable=False),
        sa.Column("ingested_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.CheckConstraint("generation_mw >= 0", name="ck_generation_forecasts_generation_nonnegative"),
        sa.UniqueConstraint("start_time", "publish_time", "fuel_type", name="uq_generation_forecasts_start_publish_fuel"),
    )
    op.create_index("ix_generation_forecasts_fuel_start_publish_desc", "generation_forecasts", ["fuel_type", "start_time", sa.text("publish_time DESC")])


def downgrade() -> None:
    op.drop_index("ix_generation_forecasts_fuel_start_publish_desc", table_name="generation_forecasts")
    op.drop_table("generation_forecasts")
    op.drop_table("generation_actuals")
