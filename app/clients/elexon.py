from datetime import date, datetime
from time import sleep
from typing import Any

import httpx

from app.core.config import get_settings


class ElexonClientError(RuntimeError):
    pass


class ElexonClient:
    def __init__(self) -> None:
        settings = get_settings()
        self.client = httpx.Client(
            base_url=settings.elexon_base_url, timeout=httpx.Timeout(30.0, connect=10.0)
        )

    def __enter__(self) -> "ElexonClient":
        return self

    def __exit__(self, *_: object) -> None:
        self.client.close()

    def fetch_actuals(self, delivery_from: date, delivery_to: date) -> list[dict[str, Any]]:
        return self._get(
            "/datasets/FUELHH/stream",
            {
                "settlementDateFrom": delivery_from.isoformat(),
                "settlementDateTo": delivery_to.isoformat(),
                "fuelType": "WIND",
            },
        )

    def fetch_forecasts(
        self, published_from: datetime, published_to: datetime
    ) -> list[dict[str, Any]]:
        return self._get(
            "/datasets/WINDFOR/stream",
            {
                "publishDateTimeFrom": published_from.isoformat(),
                "publishDateTimeTo": published_to.isoformat(),
            },
        )

    def _get(self, path: str, params: dict[str, str]) -> list[dict[str, Any]]:
        last_error: Exception | None = None
        for attempt in range(3):
            try:
                response = self.client.get(path, params=params)
                if response.status_code >= 500:
                    raise httpx.HTTPStatusError(
                        "upstream server error", request=response.request, response=response
                    )
                response.raise_for_status()
                payload = response.json()
                if not isinstance(payload, list):
                    raise ElexonClientError("Elexon returned an unexpected response shape")
                return payload
            except (httpx.NetworkError, httpx.TimeoutException, httpx.HTTPStatusError) as exc:
                last_error = exc
                if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code < 500:
                    break
                if attempt < 2:
                    sleep(2**attempt)
        raise ElexonClientError("Unable to retrieve Elexon data") from last_error
