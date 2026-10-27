from datetime import UTC, datetime

from sqlalchemy import select, tuple_
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models.generation_forecast import GenerationForecast
from app.schemas.elexon import WindForecastRecord


def upsert_generation_forecasts(
    session: Session, records: list[WindForecastRecord]
) -> tuple[int, int]:
    if not records:
        return 0, 0
    values = [
        {
            "start_time": record.start_time.astimezone(UTC),
            "publish_time": record.publish_time.astimezone(UTC),
            "fuel_type": "WIND",
            "generation_mw": record.generation,
            "ingested_at": datetime.now(UTC),
        }
        for record in records
    ]
    duplicates = 0
    for batch_start in range(0, len(values), 1_000):
        batch = values[batch_start : batch_start + 1_000]
        keys = [(value["start_time"], value["publish_time"], value["fuel_type"]) for value in batch]
        existing = session.execute(
            select(
                GenerationForecast.start_time,
                GenerationForecast.publish_time,
                GenerationForecast.fuel_type,
            ).where(
                tuple_(
                    GenerationForecast.start_time,
                    GenerationForecast.publish_time,
                    GenerationForecast.fuel_type,
                ).in_(keys)
            )
        ).all()
        duplicates += len(existing)
        statement = insert(GenerationForecast).values(batch)
        statement = statement.on_conflict_do_update(
            constraint="uq_generation_forecasts_start_publish_fuel",
            set_={
                "generation_mw": statement.excluded.generation_mw,
                "ingested_at": statement.excluded.ingested_at,
            },
        )
        session.execute(statement)
    return len(values) - duplicates, duplicates
