from datetime import UTC, datetime

from sqlalchemy import select, tuple_
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models.generation_actual import GenerationActual
from app.schemas.elexon import FuelHalfHourlyRecord


def upsert_generation_actuals(
    session: Session, records: list[FuelHalfHourlyRecord]
) -> tuple[int, int]:
    if not records:
        return 0, 0
    unique_records: dict[tuple[datetime, str], FuelHalfHourlyRecord] = {}
    for record in records:
        key = (record.start_time.astimezone(UTC), record.fuel_type)
        unique_records[key] = record
    incoming_duplicates = len(records) - len(unique_records)
    values = [
        {
            "start_time": record.start_time.astimezone(UTC),
            "fuel_type": record.fuel_type,
            "generation_mw": record.generation,
            "ingested_at": datetime.now(UTC),
        }
        for record in unique_records.values()
    ]
    existing_keys = set(
        session.execute(
            select(GenerationActual.start_time, GenerationActual.fuel_type).where(
                tuple_(GenerationActual.start_time, GenerationActual.fuel_type).in_(
                    [(value["start_time"], value["fuel_type"]) for value in values]
                )
            )
        )
    )
    statement = insert(GenerationActual).values(values)
    statement = statement.on_conflict_do_update(
        index_elements=[GenerationActual.start_time, GenerationActual.fuel_type],
        set_={
            "generation_mw": statement.excluded.generation_mw,
            "ingested_at": statement.excluded.ingested_at,
        },
    )
    session.execute(statement)
    existing_duplicates = len(existing_keys)
    return len(values) - existing_duplicates, incoming_duplicates + existing_duplicates
