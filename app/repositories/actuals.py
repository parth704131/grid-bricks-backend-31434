from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models.actual import WindActual
from app.schemas.elexon import FuelHalfHourlyRecord


def upsert_actuals(session: Session, records: list[FuelHalfHourlyRecord]) -> tuple[int, int]:
    if not records:
        return 0, 0
    values = [
        {
            "start_time": record.start_time.astimezone(UTC),
            "generation_mw": record.generation,
            "ingested_at": datetime.now(UTC),
        }
        for record in records
    ]
    existing_times = set(
        session.scalars(select(WindActual.start_time).where(WindActual.start_time.in_([value["start_time"] for value in values])))
    )
    statement = insert(WindActual).values(values)
    statement = statement.on_conflict_do_update(
        index_elements=[WindActual.start_time],
        set_={"generation_mw": statement.excluded.generation_mw, "ingested_at": statement.excluded.ingested_at},
    )
    session.execute(statement)
    duplicates = len(existing_times)
    return len(values) - duplicates, duplicates
