from decimal import Decimal
from unittest.mock import Mock

from app.repositories.generation_actuals import upsert_generation_actuals
from app.repositories.generation_forecasts import upsert_generation_forecasts
from app.schemas.elexon import FuelHalfHourlyRecord, WindForecastRecord


def test_actual_upsert_deduplicates_same_source_key() -> None:
    session = Mock()
    session.execute.return_value = []
    records = [
        FuelHalfHourlyRecord(
            startTime="2026-01-01T10:00:00Z", fuelType="WIND", generation=Decimal("100")
        ),
        FuelHalfHourlyRecord(
            startTime="2026-01-01T10:00:00Z", fuelType="WIND", generation=Decimal("105")
        ),
    ]

    written, duplicates = upsert_generation_actuals(session, records)

    assert written == 1
    assert duplicates == 1
    insert_statement = session.execute.call_args_list[-1].args[0]
    assert len(insert_statement.compile().params) == 4


def test_forecast_upsert_deduplicates_same_source_key() -> None:
    session = Mock()
    existing_result = Mock()
    existing_result.all.return_value = []
    session.execute.side_effect = [existing_result, None]
    records = [
        WindForecastRecord(
            startTime="2026-01-01T10:00:00Z",
            publishTime="2025-12-31T09:30:00Z",
            generation=Decimal("100"),
        ),
        WindForecastRecord(
            startTime="2026-01-01T10:00:00Z",
            publishTime="2025-12-31T09:30:00Z",
            generation=Decimal("105"),
        ),
    ]

    written, duplicates = upsert_generation_forecasts(session, records)

    assert written == 1
    assert duplicates == 1
    insert_statement = session.execute.call_args_list[-1].args[0]
    assert len(insert_statement.compile().params) == 5
