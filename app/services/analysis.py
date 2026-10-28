from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, time
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.time import decision_cutoff_for_delivery, delivery_period_starts, source_hour_start
from app.domain.forecast_selector import ForecastVersion, select_latest_available_forecast
from app.domain.metrics import MatchedValues, calculate_metrics
from app.models.generation_actual import GenerationActual
from app.models.generation_forecast import GenerationForecast
from app.repositories.import_runs import latest_completed_import


@dataclass(frozen=True)
class PeriodAnalysis:
    start_time: datetime
    forecast_mw: Decimal | None
    actual_mw: Decimal | None
    forecast_publish_time: datetime | None
    decision_cutoff: datetime

    @property
    def status(self) -> str:
        if self.forecast_mw is None:
            return "missing_forecast"
        if self.actual_mw is None:
            return "missing_actual"
        return "matched"


def analyse_period(
    session: Session, delivery_from: date, delivery_to: date, decision_time: time
) -> tuple[list[PeriodAnalysis], datetime | None]:
    periods = delivery_period_starts(delivery_from, delivery_to)
    return _analyse_periods(session, periods, decision_time)


def analyse_period_page(
    session: Session,
    delivery_from: date,
    delivery_to: date,
    decision_time: time,
    page: int,
    page_size: int,
) -> tuple[list[PeriodAnalysis], datetime | None, int]:
    all_periods = delivery_period_starts(delivery_from, delivery_to)
    total_items = len(all_periods)
    start = (page - 1) * page_size
    page_series, data_as_of = _analyse_periods(
        session, all_periods[start : start + page_size], decision_time
    )
    return page_series, data_as_of, total_items


def _analyse_periods(
    session: Session, periods: list[datetime], decision_time: time
) -> tuple[list[PeriodAnalysis], datetime | None]:
    if not periods:
        return [], None
    actuals = {
        row.start_time: row.generation_mw
        for row in session.scalars(
            select(GenerationActual).where(
                GenerationActual.fuel_type == "WIND",
                GenerationActual.start_time >= periods[0],
                GenerationActual.start_time <= periods[-1],
            )
        )
    }
    source_start = periods[0].replace(minute=0)
    source_end = periods[-1].replace(minute=0)
    forecasts = list(
        session.scalars(
            select(GenerationForecast).where(
                GenerationForecast.fuel_type == "WIND",
                GenerationForecast.start_time >= source_start,
                GenerationForecast.start_time <= source_end,
            )
        )
    )
    versions_by_start: dict[datetime, list[ForecastVersion]] = defaultdict(list)
    for row in forecasts:
        versions_by_start[row.start_time].append(
            ForecastVersion(row.start_time, row.publish_time, row.generation_mw)
        )
    series = []
    for start_time in periods:
        selected = select_latest_available_forecast(
            start_time,
            decision_time,
            versions_by_start[source_hour_start(start_time)],
        )
        series.append(
            PeriodAnalysis(
                start_time=start_time,
                forecast_mw=selected.generation_mw if selected else None,
                actual_mw=actuals.get(start_time),
                forecast_publish_time=selected.publish_time if selected else None,
                decision_cutoff=decision_cutoff_for_delivery(start_time, decision_time),
            )
        )
    imports = [
        latest_completed_import(session, "FUELHH"),
        latest_completed_import(session, "WINDFOR"),
    ]
    completed = [run.completed_at for run in imports if run and run.completed_at]
    return series, max(completed) if completed else None


def metrics_for_series(series: list[PeriodAnalysis]):
    return calculate_metrics(
        MatchedValues(item.forecast_mw, item.actual_mw)
        for item in series
        if item.status == "matched" and item.forecast_mw is not None and item.actual_mw is not None
    )


def forecast_versions_for_start_time(
    session: Session, start_time: datetime
) -> list[GenerationForecast]:
    source_start_time = source_hour_start(start_time)
    return list(
        session.scalars(
            select(GenerationForecast)
            .where(
                GenerationForecast.fuel_type == "WIND",
                GenerationForecast.start_time == source_start_time,
            )
            .order_by(GenerationForecast.publish_time)
        )
    )
