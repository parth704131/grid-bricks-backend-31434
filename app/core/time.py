from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

MARKET_ZONE = ZoneInfo("Europe/London")


def parse_decision_time(value: str) -> time:
    return time.fromisoformat(value)


def decision_cutoff_for_delivery(start_time: datetime, decision_time: time) -> datetime:
    delivery_date = start_time.astimezone(MARKET_ZONE).date()
    cutoff_date = delivery_date - timedelta(days=1)
    return datetime.combine(cutoff_date, decision_time, tzinfo=MARKET_ZONE).astimezone(UTC)


def delivery_period_starts(delivery_from: date, delivery_to: date) -> list[datetime]:
    start = datetime.combine(delivery_from, time.min, tzinfo=MARKET_ZONE).astimezone(UTC)
    end = datetime.combine(delivery_to + timedelta(days=1), time.min, tzinfo=MARKET_ZONE).astimezone(UTC)
    periods: list[datetime] = []
    current = start
    while current < end:
        periods.append(current)
        current += timedelta(minutes=30)
    return periods


def source_hour_start(period_start: datetime) -> datetime:
    return period_start.astimezone(UTC).replace(minute=0, second=0, microsecond=0)
