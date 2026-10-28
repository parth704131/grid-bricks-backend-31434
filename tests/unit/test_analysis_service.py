from datetime import UTC, datetime

from app.services.analysis import forecast_versions_for_start_time


class CapturingSession:
    def __init__(self) -> None:
        self.statement = None

    def scalars(self, statement):
        self.statement = statement
        return []


def test_forecast_audit_queries_hourly_source_for_second_half_hour() -> None:
    session = CapturingSession()

    forecast_versions_for_start_time(session, datetime(2026, 1, 1, 10, 30, tzinfo=UTC))

    assert session.statement is not None
    assert datetime(2026, 1, 1, 10, tzinfo=UTC) in session.statement.compile().params.values()
