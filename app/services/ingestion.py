from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.clients.elexon import ElexonClient
from app.models.import_run import DataImportRun, ImportRunStatus
from app.repositories.actuals import upsert_actuals
from app.repositories.forecasts import upsert_forecasts
from app.repositories.import_runs import complete_import_run, start_import_run
from app.schemas.elexon import FuelHalfHourlyRecord, WindForecastRecord

MARKET_ZONE = ZoneInfo("Europe/London")


@dataclass(frozen=True)
class ImportSummary:
    dataset: str
    received: int
    written: int
    duplicates: int
    rejected: int


class IngestionError(RuntimeError):
    pass


def import_actuals(
    session: Session, delivery_from: date, delivery_to: date, client: ElexonClient
) -> ImportSummary:
    run = start_import_run(session, "FUELHH")
    session.commit()
    try:
        payload = client.fetch_actuals(delivery_from, delivery_to)
        records, rejected = _validate_actuals(payload)
        written, duplicates = upsert_actuals(session, records)
        status = ImportRunStatus.PARTIAL if rejected else ImportRunStatus.SUCCESSFUL
        complete_import_run(session, run, status, len(payload), written, rejected)
        session.commit()
        return ImportSummary("FUELHH", len(payload), written, duplicates, rejected)
    except Exception as exc:
        session.rollback()
        _mark_failed(session, run, "Elexon actuals import failed")
        raise IngestionError("Unable to import FUELHH data") from exc


def import_forecasts(
    session: Session, delivery_from: date, delivery_to: date, client: ElexonClient
) -> ImportSummary:
    run = start_import_run(session, "WINDFOR")
    session.commit()
    try:
        published_from = datetime.combine(
            delivery_from - timedelta(days=3), time.min, tzinfo=MARKET_ZONE
        ).astimezone(UTC)
        published_to = datetime.combine(
            delivery_to + timedelta(days=1), time.max, tzinfo=MARKET_ZONE
        ).astimezone(UTC)
        payload = client.fetch_forecasts(published_from, published_to)
        records, rejected = _validate_forecasts(payload, delivery_from, delivery_to)
        written, duplicates = upsert_forecasts(session, records)
        status = ImportRunStatus.PARTIAL if rejected else ImportRunStatus.SUCCESSFUL
        complete_import_run(session, run, status, len(payload), written, rejected)
        session.commit()
        return ImportSummary("WINDFOR", len(payload), written, duplicates, rejected)
    except Exception as exc:
        session.rollback()
        _mark_failed(session, run, "Elexon forecast import failed")
        raise IngestionError("Unable to import WINDFOR data") from exc


def _validate_actuals(payload: list[dict]) -> tuple[list[FuelHalfHourlyRecord], int]:
    records: list[FuelHalfHourlyRecord] = []
    rejected = 0
    for item in payload:
        try:
            record = FuelHalfHourlyRecord.model_validate(item)
            if record.fuel_type != "WIND":
                continue
            records.append(record)
        except ValidationError:
            rejected += 1
    return records, rejected


def _validate_forecasts(
    payload: list[dict], delivery_from: date, delivery_to: date
) -> tuple[list[WindForecastRecord], int]:
    records: list[WindForecastRecord] = []
    rejected = 0
    for item in payload:
        try:
            record = WindForecastRecord.model_validate(item)
            delivery_date = record.start_time.astimezone(MARKET_ZONE).date()
            if delivery_from <= delivery_date <= delivery_to:
                records.append(record)
        except ValidationError:
            rejected += 1
    return records, rejected


def _mark_failed(session: Session, run: DataImportRun, message: str) -> None:
    complete_import_run(session, run, ImportRunStatus.FAILED, 0, 0, 0, message)
    session.commit()
