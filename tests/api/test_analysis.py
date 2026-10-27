from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.main import app
from app.services.analysis import PeriodAnalysis


def test_analysis_returns_dashboard_response(monkeypatch) -> None:
    period = PeriodAnalysis(
        start_time=datetime(2026, 1, 1, tzinfo=UTC),
        forecast_mw=Decimal("110"),
        actual_mw=Decimal("100"),
        forecast_publish_time=datetime(2025, 12, 31, 9, 30, tzinfo=UTC),
        decision_cutoff=datetime(2025, 12, 31, 10, tzinfo=UTC),
    )
    monkeypatch.setattr(
        "app.api.analysis.analyse_period",
        lambda *_: ([period], datetime(2026, 2, 1, tzinfo=UTC)),
    )

    response = TestClient(app).get("/api/v1/analysis?from=2026-01-01&to=2026-01-01")

    assert response.status_code == 200
    assert response.json()["coverage"]["matchedPeriods"] == 1
    assert response.json()["series"][0]["errorMw"] == 10.0
    assert (
        response.headers["cache-control"] == "public, s-maxage=3600, stale-while-revalidate=86400"
    )


def test_analysis_invalid_date_range_uses_standard_error() -> None:
    response = TestClient(app).get("/api/v1/analysis?from=2026-01-02&to=2026-01-01")

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_DATE_RANGE"
    assert response.json()["error"]["requestId"]


def test_analysis_invalid_decision_time_uses_standard_error() -> None:
    response = TestClient(app).get(
        "/api/v1/analysis?from=2026-01-01&to=2026-01-01&decisionTime=25:00"
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_DECISION_TIME"


def test_readiness_returns_safe_database_error(monkeypatch) -> None:
    monkeypatch.setattr("app.api.health.database_is_ready", lambda: False)

    response = TestClient(app).get("/health/ready")

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "DATABASE_UNAVAILABLE"


def test_forecast_versions_marks_latest_eligible_version(monkeypatch) -> None:
    versions = [
        SimpleNamespace(
            id=1,
            publish_time=datetime(2025, 12, 31, 9, 30, tzinfo=UTC),
            generation_mw=Decimal("100"),
        ),
        SimpleNamespace(
            id=2,
            publish_time=datetime(2025, 12, 31, 11, 30, tzinfo=UTC),
            generation_mw=Decimal("120"),
        ),
    ]
    monkeypatch.setattr("app.api.analysis.forecast_versions_for_start_time", lambda *_: versions)

    response = TestClient(app).get(
        "/api/v1/forecast-versions?startTime=2026-01-01T10:00:00Z&decisionTime=10:00"
    )

    assert response.status_code == 200
    assert response.json()["versions"] == [
        {
            "publishTime": "2025-12-31T09:30:00Z",
            "generationMw": 100.0,
            "eligible": True,
            "selected": True,
        },
        {
            "publishTime": "2025-12-31T11:30:00Z",
            "generationMw": 120.0,
            "eligible": False,
            "selected": False,
        },
    ]
