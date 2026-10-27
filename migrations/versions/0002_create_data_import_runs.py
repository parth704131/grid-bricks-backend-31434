"""Create import run diagnostics."""

from alembic import op
import sqlalchemy as sa

revision = "0002_create_data_import_runs"
down_revision = "0001_create_wind_data_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    status_type = sa.Enum("running", "successful", "partial", "failed", name="import_run_status")
    op.create_table(
        "data_import_runs",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("dataset", sa.String(16), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("status", status_type, nullable=False),
        sa.Column("records_received", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("records_written", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("records_rejected", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text()),
        sa.CheckConstraint("records_received >= 0", name="ck_import_runs_received_nonnegative"),
        sa.CheckConstraint("records_written >= 0", name="ck_import_runs_written_nonnegative"),
        sa.CheckConstraint("records_rejected >= 0", name="ck_import_runs_rejected_nonnegative"),
    )
    op.create_index("ix_import_runs_dataset_completed", "data_import_runs", ["dataset", "completed_at"])


def downgrade() -> None:
    op.drop_index("ix_import_runs_dataset_completed", table_name="data_import_runs")
    op.drop_table("data_import_runs")
    sa.Enum(name="import_run_status").drop(op.get_bind(), checkfirst=True)
