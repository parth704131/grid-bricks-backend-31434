from collections import defaultdict
from datetime import date, datetime, time
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_session
from app.core.errors import ApiError
from app.core.time import MARKET_ZONE, decision_cutoff_for_delivery, delivery_period_starts
from app.schemas.analysis import AnalysisPeriodsResponse, AnalysisResponse, ForecastVersionsResponse
from app.services.analysis import (
    analyse_period,
    analyse_period_page,
    forecast_versions_for_start_time,
    metrics_for_series,
)

router = APIRouter(prefix="/api/v1", tags=["analysis"])
DEFAULT_DECISION_TIME = time.fromisoformat(get_settings().default_decision_time)


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


def series_period_payload(item) -> dict:
    return {
        "startTime": item.start_time,
        "forecastMw": numeric(item.forecast_mw),
        "actualMw": numeric(item.actual_mw),
        "errorMw": numeric(item.forecast_mw - item.actual_mw) if item.status == "matched" else None,
        "absoluteErrorMw": numeric(abs(item.forecast_mw - item.actual_mw))
        if item.status == "matched"
        else None,
        "energyErrorMwh": numeric((item.forecast_mw - item.actual_mw) * Decimal("0.5"))
        if item.status == "matched"
        else None,
        "forecastPublishTime": item.forecast_publish_time,
        "decisionCutoff": item.decision_cutoff,
        "status": item.status,
    }


def validate_analysis_request(from_date: date, to_date: date, timezone: str) -> None:
    if from_date > to_date:
        raise ApiError("INVALID_DATE_RANGE", "The start date must not be after the end date.", 422)
    if timezone != "Europe/London":
        raise ApiError("INVALID_TIMEZONE", "Only Europe/London is supported.", 422)
    if from_date < date(2026, 1, 1) or to_date > date(2026, 1, 31):
        raise ApiError("UNSUPPORTED_DATE_RANGE", "Only January 2026 is supported.", 422)


@router.get("/analysis", response_model=AnalysisResponse)
def analysis(
    response: Response,
    from_date: Annotated[date, Query(alias="from")],
    to_date: Annotated[date, Query(alias="to")],
    session: Annotated[Session, Depends(get_session)],
    decision_time: Annotated[time, Query(alias="decisionTime")] = DEFAULT_DECISION_TIME,
    timezone: Annotated[str, Query()] = "Europe/London",
) -> AnalysisResponse:
    validate_analysis_request(from_date, to_date, timezone)
    series, data_as_of = analyse_period(session, from_date, to_date, decision_time)
    if not data_as_of:
        raise ApiError("NO_DATA_AVAILABLE", "No data is available for this request.", 404)
    metrics = metrics_for_series(series)
    matched = [item for item in series if item.status == "matched"]
    warnings = (
        []
        if len(matched) == len(series)
        else ["Some requested periods have missing actuals or forecasts."]
    )
    response.headers["Cache-Control"] = "public, s-maxage=3600, stale-while-revalidate=86400"
    return AnalysisResponse.model_validate(
        {
            "period": {"from": from_date, "to": to_date},
            "decisionPolicy": {
                "time": decision_time.strftime("%H:%M"),
                "timezone": timezone,
                "daysBeforeDelivery": 1,
            },
            "summary": {
                "maeMw": numeric(metrics.mae_mw),
                "rmseMw": numeric(metrics.rmse_mw),
                "biasMw": numeric(metrics.bias_mw),
                "p90AbsoluteErrorMw": numeric(metrics.p90_absolute_error_mw),
                "positiveErrorMwh": numeric(metrics.positive_error_mwh),
                "negativeErrorMwh": numeric(metrics.negative_error_mwh),
            },
            "coverage": {
                "expectedPeriods": len(series),
                "matchedPeriods": len(matched),
                "percentage": round(100 * len(matched) / len(series), 2),
            },
            "daily": daily_summaries(series),
            "series": [series_period_payload(item) for item in series],
            "dataAsOf": data_as_of,
            "warnings": warnings,
        }
    )


@router.get("/analysis/periods", response_model=AnalysisPeriodsResponse)
def analysis_periods(
    response: Response,
    from_date: Annotated[date, Query(alias="from")],
    to_date: Annotated[date, Query(alias="to")],
    session: Annotated[Session, Depends(get_session)],
    decision_time: Annotated[time, Query(alias="decisionTime")] = DEFAULT_DECISION_TIME,
    timezone: Annotated[str, Query()] = "Europe/London",
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(alias="pageSize", ge=1, le=100)] = 20,
) -> AnalysisPeriodsResponse:
    validate_analysis_request(from_date, to_date, timezone)
    all_periods = delivery_period_starts(from_date, to_date)
    total_items = len(all_periods)
    total_pages = max(1, (total_items + page_size - 1) // page_size)
    if page > total_pages:
        raise ApiError("INVALID_PAGE", "The requested page is outside the available range.", 422)
    series, data_as_of, total_items = analyse_period_page(
        session, from_date, to_date, decision_time, page, page_size
    )
    if not data_as_of:
        raise ApiError("NO_DATA_AVAILABLE", "No data is available for this request.", 404)
    page_items = series
    response.headers["Cache-Control"] = "public, s-maxage=3600, stale-while-revalidate=86400"
    return AnalysisPeriodsResponse.model_validate(
        {
            "period": {"from": from_date, "to": to_date},
            "decisionPolicy": {
                "time": decision_time.strftime("%H:%M"),
                "timezone": timezone,
                "daysBeforeDelivery": 1,
            },
            "series": [series_period_payload(item) for item in page_items],
            "pagination": {
                "page": page,
                "pageSize": page_size,
                "totalItems": total_items,
                "totalPages": total_pages,
            },
            "dataAsOf": data_as_of,
        }
    )


@router.get("/forecast-versions", response_model=ForecastVersionsResponse)
def forecast_versions(
    start_time: Annotated[datetime, Query(alias="startTime")],
    session: Annotated[Session, Depends(get_session)],
    decision_time: Annotated[time, Query(alias="decisionTime")] = DEFAULT_DECISION_TIME,
    timezone: Annotated[str, Query()] = "Europe/London",
) -> ForecastVersionsResponse:
    if timezone != "Europe/London":
        raise ApiError("INVALID_TIMEZONE", "Only Europe/London is supported.", 422)
    if start_time.tzinfo is None:
        raise ApiError("INVALID_START_TIME", "startTime must include a timezone.", 422)
    versions = forecast_versions_for_start_time(session, start_time)
    cutoff = decision_cutoff_for_delivery(start_time, decision_time)
    selected = max(
        (version for version in versions if version.publish_time <= cutoff),
        key=lambda version: version.publish_time,
        default=None,
    )
    return ForecastVersionsResponse.model_validate(
        {
            "startTime": start_time,
            "decisionPolicy": {
                "time": decision_time.strftime("%H:%M"),
                "timezone": timezone,
                "daysBeforeDelivery": 1,
            },
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
    )
