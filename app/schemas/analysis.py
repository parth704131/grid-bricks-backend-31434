from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ApiSchema(BaseModel):
    model_config = ConfigDict(populate_by_name=True)


class Period(ApiSchema):
    from_date: date = Field(alias="from")
    to: date


class DecisionPolicy(ApiSchema):
    time: str
    timezone: str
    days_before_delivery: int = Field(alias="daysBeforeDelivery")


class Summary(ApiSchema):
    mae_mw: float | None = Field(alias="maeMw")
    rmse_mw: float | None = Field(alias="rmseMw")
    bias_mw: float | None = Field(alias="biasMw")
    p90_absolute_error_mw: float | None = Field(alias="p90AbsoluteErrorMw")
    positive_error_mwh: float = Field(alias="positiveErrorMwh")
    negative_error_mwh: float = Field(alias="negativeErrorMwh")


class Coverage(ApiSchema):
    expected_periods: int = Field(alias="expectedPeriods")
    matched_periods: int = Field(alias="matchedPeriods")
    percentage: float


class DailySummary(ApiSchema):
    date: date
    mae_mw: float | None = Field(alias="maeMw")
    rmse_mw: float | None = Field(alias="rmseMw")
    bias_mw: float | None = Field(alias="biasMw")
    coverage: float


class SeriesPeriod(ApiSchema):
    start_time: datetime = Field(alias="startTime")
    forecast_mw: float | None = Field(alias="forecastMw")
    actual_mw: float | None = Field(alias="actualMw")
    error_mw: float | None = Field(alias="errorMw")
    absolute_error_mw: float | None = Field(alias="absoluteErrorMw")
    energy_error_mwh: float | None = Field(alias="energyErrorMwh")
    forecast_publish_time: datetime | None = Field(alias="forecastPublishTime")
    decision_cutoff: datetime = Field(alias="decisionCutoff")
    status: Literal["matched", "missing_forecast", "missing_actual"]


class AnalysisResponse(ApiSchema):
    period: Period
    decision_policy: DecisionPolicy = Field(alias="decisionPolicy")
    summary: Summary
    coverage: Coverage
    daily: list[DailySummary]
    series: list[SeriesPeriod]
    data_as_of: datetime = Field(alias="dataAsOf")
    warnings: list[str]


class ForecastVersion(ApiSchema):
    publish_time: datetime = Field(alias="publishTime")
    generation_mw: float = Field(alias="generationMw")
    eligible: bool
    selected: bool


class ForecastVersionsResponse(ApiSchema):
    start_time: datetime = Field(alias="startTime")
    decision_policy: DecisionPolicy = Field(alias="decisionPolicy")
    decision_cutoff: datetime = Field(alias="decisionCutoff")
    versions: list[ForecastVersion]
