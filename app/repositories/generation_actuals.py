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
    values = [
        {
            "start_time": record.start_time.astimezone(UTC),
            "fuel_type": record.fuel_type,
            "generation_mw": record.generation,
            "ingested_at": datetime.now(UTC),
        }
        for record in records
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
    duplicates = len(existing_keys)
    return len(values) - duplicates, duplicates
