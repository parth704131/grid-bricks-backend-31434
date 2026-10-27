from datetime import UTC, datetime, time
from decimal import Decimal

from app.core.time import decision_cutoff_for_delivery
from app.domain.forecast_selector import ForecastVersion, select_latest_available_forecast


def test_selects_latest_version_at_or_before_cutoff() -> None:
    period_start = datetime(2026, 1, 2, 10, tzinfo=UTC)
    versions = [
        ForecastVersion(period_start, datetime(2026, 1, 1, 9, tzinfo=UTC), Decimal("100")),
        ForecastVersion(period_start, datetime(2026, 1, 1, 10, tzinfo=UTC), Decimal("110")),
        ForecastVersion(period_start, datetime(2026, 1, 1, 10, 30, tzinfo=UTC), Decimal("120")),
    ]

    selected = select_latest_available_forecast(period_start, time(10), versions)

    assert selected == versions[1]


def test_hourly_forecast_is_selected_for_second_half_hour() -> None:
    period_start = datetime(2026, 1, 2, 10, 30, tzinfo=UTC)
    version = ForecastVersion(
        datetime(2026, 1, 2, 10, tzinfo=UTC),
        datetime(2026, 1, 1, 10, tzinfo=UTC),
        Decimal("100"),
    )

    assert select_latest_available_forecast(period_start, time(10), [version]) == version


def test_uk_summer_cutoff_uses_bst() -> None:
    period_start = datetime(2026, 7, 2, 10, tzinfo=UTC)

    assert decision_cutoff_for_delivery(period_start, time(10)) == datetime(
        2026, 7, 1, 9, tzinfo=UTC
    )
