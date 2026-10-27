from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, time
from decimal import Decimal

from app.core.time import decision_cutoff_for_delivery, source_hour_start


@dataclass(frozen=True)
class ForecastVersion:
    start_time: datetime
    publish_time: datetime
    generation_mw: Decimal


def select_latest_available_forecast(
    period_start: datetime,
    decision_time: time,
    forecast_versions: Iterable[ForecastVersion],
) -> ForecastVersion | None:
    cutoff = decision_cutoff_for_delivery(period_start, decision_time)
    hourly_start = source_hour_start(period_start)
    eligible = [
        version
        for version in forecast_versions
        if version.start_time == hourly_start and version.publish_time <= cutoff
    ]
    return max(eligible, key=lambda version: version.publish_time, default=None)
