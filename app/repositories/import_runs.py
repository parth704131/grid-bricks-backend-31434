from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.import_run import DataImportRun, ImportRunStatus


def start_import_run(session: Session, dataset: str) -> DataImportRun:
    run = DataImportRun(dataset=dataset, status=ImportRunStatus.RUNNING)
    session.add(run)
    session.flush()
    return run


def complete_import_run(
    session: Session,
    run: DataImportRun,
    status: ImportRunStatus,
    received: int,
    written: int,
    rejected: int,
    error_message: str | None = None,
) -> None:
    run.status = status
    run.completed_at = datetime.now(UTC)
    run.records_received = received
    run.records_written = written
    run.records_rejected = rejected
    run.error_message = error_message
    session.flush()


def latest_completed_import(session: Session, dataset: str) -> DataImportRun | None:
    statement = (
        select(DataImportRun)
        .where(DataImportRun.dataset == dataset, DataImportRun.status.in_([ImportRunStatus.SUCCESSFUL, ImportRunStatus.PARTIAL]))
        .order_by(DataImportRun.completed_at.desc())
        .limit(1)
    )
    return session.scalar(statement)
