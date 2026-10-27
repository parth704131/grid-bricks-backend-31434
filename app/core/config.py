from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration loaded from environment variables and a local `.env` file."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql+psycopg://wind:wind@localhost:5432/wind_procurement"
    frontend_origin: str = "http://localhost:5173"
    default_decision_time: str = "10:00"
    market_timezone: str = "Europe/London"
    log_level: str = "INFO"
    elexon_base_url: str = "https://data.elexon.co.uk/bmrs/api/v1"

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_database_url(cls, value: str) -> str:
        if value.startswith("postgres://"):
            return "postgresql+psycopg://" + value.removeprefix("postgres://")
        if value.startswith("postgresql://"):
            return "postgresql+psycopg://" + value.removeprefix("postgresql://")
        return value

    @field_validator("default_decision_time")
    @classmethod
    def validate_decision_time(cls, value: str) -> str:
        try:
            hour, minute = value.split(":", maxsplit=1)
            if not (0 <= int(hour) <= 23 and 0 <= int(minute) <= 59 and len(value) == 5):
                raise ValueError
        except ValueError as exc:
            raise ValueError("DEFAULT_DECISION_TIME must be a 24-hour HH:MM value") from exc
        return value

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.frontend_origin.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
