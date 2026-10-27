from datetime import date
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.models.import_run import ImportRunStatus
from app.services.ingestion import (
    IngestionError,
    _validate_actuals,
    _validate_forecasts,
    import_actuals,
)


def test_validate_actuals_ignores_non_wind_and_rejects_invalid_records() -> None:
    records, rejected = _validate_actuals(
        [
            {
                "startTime": "2026-01-01T00:00:00Z",
                "fuelType": "WIND",
                "generation": 100,
            },
            {
                "startTime": "2026-01-01T00:30:00Z",
                "fuelType": "GAS",
                "generation": 200,
            },
            {
                "startTime": "2026-01-01T01:00:00Z",
                "fuelType": "WIND",
                "generation": -1,
            },
        ]
    )

    assert len(records) == 1
    assert records[0].fuel_type == "WIND"
    assert rejected == 1


def test_validate_forecasts_keeps_only_requested_delivery_dates() -> None:
    records, rejected = _validate_forecasts(
        [
            {
                "startTime": "2026-01-01T00:00:00Z",
                "publishTime": "2025-12-31T09:30:00Z",
                "generation": 100,
            },
            {
                "startTime": "2026-02-01T00:00:00Z",
                "publishTime": "2026-01-31T09:30:00Z",
                "generation": 120,
            },
            {
                "startTime": "2026-01-01T01:00:00Z",
                "publishTime": "2025-12-31T09:30:00Z",
                "generation": -1,
            },
        ],
        date(2026, 1, 1),
        date(2026, 1, 31),
    )

    assert len(records) == 1
    assert records[0].generation == 100
    assert rejected == 1


def test_actual_import_records_partial_run_and_duplicate_count(monkeypatch) -> None:
    session = SimpleNamespace(commit=Mock(), rollback=Mock())
    run = SimpleNamespace()
    completed: list[tuple] = []
    client = SimpleNamespace(
        fetch_actuals=lambda *_: [
            {
                "startTime": "2026-01-01T00:00:00Z",
                "fuelType": "WIND",
                "generation": 100,
            },
            {
                "startTime": "2026-01-01T00:30:00Z",
                "fuelType": "GAS",
                "generation": 200,
            },
            {
                "startTime": "2026-01-01T01:00:00Z",
                "fuelType": "WIND",
                "generation": -1,
            },
        ]
    )
    monkeypatch.setattr("app.services.ingestion.start_import_run", lambda *_: run)
    monkeypatch.setattr("app.services.ingestion.upsert_actuals", lambda *_: (0, 1))
    monkeypatch.setattr(
        "app.services.ingestion.complete_import_run", lambda *arguments: completed.append(arguments)
    )

    summary = import_actuals(session, date(2026, 1, 1), date(2026, 1, 1), client)

    assert summary.written == 0
    assert summary.duplicates == 1
    assert summary.rejected == 1
    assert completed[0][2] == ImportRunStatus.PARTIAL
    assert completed[0][3:6] == (3, 0, 1)
    assert session.commit.call_count == 2


def test_actual_import_marks_run_failed_without_exposing_source_error(monkeypatch) -> None:
    session = SimpleNamespace(commit=Mock(), rollback=Mock())
    run = SimpleNamespace()
    completed: list[tuple] = []
    client = SimpleNamespace(fetch_actuals=Mock(side_effect=RuntimeError("source credentials")))
    monkeypatch.setattr("app.services.ingestion.start_import_run", lambda *_: run)
    monkeypatch.setattr(
        "app.services.ingestion.complete_import_run", lambda *arguments: completed.append(arguments)
    )

    with pytest.raises(IngestionError, match="Unable to import FUELHH data"):
        import_actuals(session, date(2026, 1, 1), date(2026, 1, 1), client)

    assert session.rollback.call_count == 1
    assert completed[0][2] == ImportRunStatus.FAILED
    assert completed[0][-1] == "Elexon actuals import failed"
