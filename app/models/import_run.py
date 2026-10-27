import enum
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Enum, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ImportRunStatus(str, enum.Enum):
    RUNNING = "running"
    SUCCESSFUL = "successful"
    PARTIAL = "partial"
    FAILED = "failed"


class DataImportRun(Base):
    __tablename__ = "data_import_runs"
    __table_args__ = (
        CheckConstraint("records_received >= 0", name="ck_import_runs_received_nonnegative"),
        CheckConstraint("records_written >= 0", name="ck_import_runs_written_nonnegative"),
        CheckConstraint("records_rejected >= 0", name="ck_import_runs_rejected_nonnegative"),
        Index("ix_import_runs_dataset_completed", "dataset", "completed_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    dataset: Mapped[str] = mapped_column(String(16), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[ImportRunStatus] = mapped_column(Enum(ImportRunStatus, name="import_run_status"), nullable=False)
    records_received: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    records_written: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    records_rejected: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
