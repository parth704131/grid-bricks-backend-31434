from decimal import Decimal

from app.domain.metrics import MatchedValues, calculate_metrics


def test_calculates_accuracy_metrics_and_signed_energy() -> None:
    metrics = calculate_metrics(
        [
            MatchedValues(Decimal("110"), Decimal("100")),
            MatchedValues(Decimal("80"), Decimal("100")),
            MatchedValues(Decimal("100"), Decimal("100")),
        ]
    )

    assert metrics.mae_mw == Decimal("10")
    assert metrics.bias_mw == Decimal("-3.333333333333333333333333333")
    assert metrics.p90_absolute_error_mw == Decimal("20")
    assert metrics.positive_error_mwh == Decimal("5.0")
    assert metrics.negative_error_mwh == Decimal("-10.0")


def test_empty_metrics_are_json_safe() -> None:
    metrics = calculate_metrics([])

    assert metrics.mae_mw is None
    assert metrics.rmse_mw is None
    assert metrics.bias_mw is None
    assert metrics.p90_absolute_error_mw is None
