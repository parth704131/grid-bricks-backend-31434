from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal
from math import ceil


@dataclass(frozen=True)
class MatchedValues:
    forecast_mw: Decimal
    actual_mw: Decimal

    @property
    def error_mw(self) -> Decimal:
        return self.forecast_mw - self.actual_mw

    @property
    def absolute_error_mw(self) -> Decimal:
        return abs(self.error_mw)


@dataclass(frozen=True)
class AccuracyMetrics:
    mae_mw: Decimal | None
    rmse_mw: Decimal | None
    bias_mw: Decimal | None
    p90_absolute_error_mw: Decimal | None
    positive_error_mwh: Decimal
    negative_error_mwh: Decimal


def calculate_metrics(matched_values: Iterable[MatchedValues]) -> AccuracyMetrics:
    values = list(matched_values)
    if not values:
        return AccuracyMetrics(None, None, None, None, Decimal("0"), Decimal("0"))

    errors = [value.error_mw for value in values]
    absolute_errors = sorted(abs(error) for error in errors)
    count = Decimal(len(errors))
    mae = sum(absolute_errors, Decimal("0")) / count
    rmse = (sum((error * error for error in errors), Decimal("0")) / count).sqrt()
    bias = sum(errors, Decimal("0")) / count
    p90 = absolute_errors[ceil(len(absolute_errors) * 0.9) - 1]
    positive_energy = sum((error * Decimal("0.5") for error in errors if error > 0), Decimal("0"))
    negative_energy = sum((error * Decimal("0.5") for error in errors if error < 0), Decimal("0"))
    return AccuracyMetrics(mae, rmse, bias, p90, positive_energy, negative_energy)
