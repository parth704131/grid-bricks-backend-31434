from collections import defaultdict
from datetime import date, datetime, time
from decimal import Decimal

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.core.errors import ApiError
from app.core.time import MARKET_ZONE, decision_cutoff_for_delivery
from app.services.analysis import analyse_period, forecast_versions_for_start_time, metrics_for_series

router = APIRouter(prefix="/api/v1", tags=["analysis"])


def numeric(value: Decimal | None) -> float | None:
    return float(value) if value is not None else None


def daily_summaries(series: list) -> list[dict]:
    periods_by_day: dict[date, list] = defaultdict(list)
    for period in series:
        periods_by_day[period.start_time.astimezone(MARKET_ZONE).date()].append(period)
    summaries = []
    for delivery_date, day_periods in sorted(periods_by_day.items()):
        daily_metrics = metrics_for_series(day_periods)
        matched_periods = [period for period in day_periods if period.status == "matched"]
        summaries.append(
            {
                "date": delivery_date.isoformat(),
                "maeMw": numeric(daily_metrics.mae_mw),
                "rmseMw": numeric(daily_metrics.rmse_mw),
                "biasMw": numeric(daily_metrics.bias_mw),
                "coverage": round(100 * len(matched_periods) / len(day_periods), 2),
            }
        )
    return summaries


@router.get("/analysis")
def analysis(
    response: Response,
    from_date: date = Query(alias="from"),
    to_date: date = Query(alias="to"),
    decision_time: time = Query(default=time(10), alias="decisionTime"),
    timezone: str = Query(default="Europe/London"),
    session: Session = Depends(get_session),
) -> dict:
    if from_date > to_date:
        raise ApiError("INVALID_DATE_RANGE", "The start date must not be after the end date.", 422)
    if timezone != "Europe/London":
        raise ApiError("INVALID_TIMEZONE", "Only Europe/London is supported.", 422)
    if from_date < date(2026, 1, 1) or to_date > date(2026, 1, 31):
        raise ApiError("UNSUPPORTED_DATE_RANGE", "Only January 2026 is supported.", 422)
    series, data_as_of = analyse_period(session, from_date, to_date, decision_time)
    if not data_as_of:
        raise ApiError("NO_DATA_AVAILABLE", "No data is available for this request.", 404)
    metrics = metrics_for_series(series)
    matched = [item for item in series if item.status == "matched"]
    warnings = [] if len(matched) == len(series) else ["Some requested periods have missing actuals or forecasts."]
    response.headers["Cache-Control"] = "public, s-maxage=3600, stale-while-revalidate=86400"
    return {
        "period": {"from": from_date, "to": to_date},
        "decisionPolicy": {"time": decision_time.strftime("%H:%M"), "timezone": timezone, "daysBeforeDelivery": 1},
        "summary": {
            "maeMw": numeric(metrics.mae_mw),
            "rmseMw": numeric(metrics.rmse_mw),
            "biasMw": numeric(metrics.bias_mw),
            "p90AbsoluteErrorMw": numeric(metrics.p90_absolute_error_mw),
            "positiveErrorMwh": numeric(metrics.positive_error_mwh),
            "negativeErrorMwh": numeric(metrics.negative_error_mwh),
        },
        "coverage": {"expectedPeriods": len(series), "matchedPeriods": len(matched), "percentage": round(100 * len(matched) / len(series), 2)},
        "daily": daily_summaries(series),
        "series": [
            {
                "startTime": item.start_time,
                "forecastMw": numeric(item.forecast_mw),
                "actualMw": numeric(item.actual_mw),
                "errorMw": numeric(item.forecast_mw - item.actual_mw) if item.status == "matched" else None,
                "absoluteErrorMw": numeric(abs(item.forecast_mw - item.actual_mw)) if item.status == "matched" else None,
                "energyErrorMwh": numeric((item.forecast_mw - item.actual_mw) * Decimal("0.5")) if item.status == "matched" else None,
                "forecastPublishTime": item.forecast_publish_time,
                "decisionCutoff": item.decision_cutoff,
                "status": item.status,
            }
            for item in series
        ],
        "dataAsOf": data_as_of,
        "warnings": warnings,
    }


@router.get("/forecast-versions")
def forecast_versions(
    start_time: datetime = Query(alias="startTime"),
    decision_time: time = Query(default=time(10), alias="decisionTime"),
    timezone: str = Query(default="Europe/London"),
    session: Session = Depends(get_session),
) -> dict:
    if timezone != "Europe/London":
        raise ApiError("INVALID_TIMEZONE", "Only Europe/London is supported.", 422)
    if start_time.tzinfo is None:
        raise ApiError("INVALID_START_TIME", "startTime must include a timezone.", 422)
    versions = forecast_versions_for_start_time(session, start_time)
    cutoff = decision_cutoff_for_delivery(start_time, decision_time)
    selected = max((version for version in versions if version.publish_time <= cutoff), key=lambda version: version.publish_time, default=None)
    return {
        "startTime": start_time,
        "decisionPolicy": {"time": decision_time.strftime("%H:%M"), "timezone": timezone, "daysBeforeDelivery": 1},
        "decisionCutoff": cutoff,
        "versions": [
            {
                "publishTime": version.publish_time,
                "generationMw": numeric(version.generation_mw),
                "eligible": version.publish_time <= cutoff,
                "selected": selected is not None and version.id == selected.id,
            }
            for version in versions
        ],
    }
