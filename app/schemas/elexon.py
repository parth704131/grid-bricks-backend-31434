from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ElexonRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")

    start_time: datetime = Field(alias="startTime")
    generation: Decimal = Field(ge=0)

    @field_validator("start_time")
    @classmethod
    def require_aware_start_time(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("startTime must include a timezone")
        return value


class FuelHalfHourlyRecord(ElexonRecord):
    fuel_type: str = Field(alias="fuelType")


class WindForecastRecord(ElexonRecord):
    publish_time: datetime = Field(alias="publishTime")

    @field_validator("publish_time")
    @classmethod
    def require_aware_publish_time(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("publishTime must include a timezone")
        return value
