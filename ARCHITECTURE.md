# Wind Procurement Insight Backend Architecture

## Purpose

This API reconstructs the wind forecast available before a configurable UK day-ahead decision cutoff, compares it to actual wind generation, and exposes dashboard-ready analysis. It informs purchasing risk; it does not calculate a purchase quantity.

## Boundaries

```
Elexon FUELHH + WINDFOR -> backfill CLI -> PostgreSQL -> FastAPI -> React dashboard
```

- Elexon is contacted only by the CLI import process.
- PostgreSQL retains normalized source records and import diagnostics.
- FastAPI only reads PostgreSQL for analytical endpoints.
- The frontend never calls Elexon directly.

## Layering

| Layer | Responsibility |
| --- | --- |
| `app/api` | HTTP routing, query validation, response and error mapping |
| `app/services` | Application use-cases: ingestion and analysis orchestration |
| `app/domain` | Pure cutoff, forecast-selection, and metric calculations |
| `app/repositories` | SQLAlchemy database queries and upserts |
| `app/models` | Persisted SQLAlchemy models |
| `app/clients` | Resilient HTTPX Elexon client |
| `app/schemas` | Pydantic request, response, and source-payload models |
| `app/core` | Configuration, logging, time utilities, and error types |

## Data and time invariants

- Persist all instants in UTC with timezone information.
- Use `Europe/London` only for delivery-date and day-ahead cutoff calculations.
- `wind_actuals.start_time` is the primary key.
- Forecast versions are immutable by `(start_time, publish_time)`; refreshes are idempotent.
- Missing values remain missing. Analysis labels periods as `matched`, `missing_forecast`, or `missing_actual`.
- Error is always `forecast - actual`; positive values signify overforecasting.

## Planned schema migrations

1. `0001_create_wind_data_tables` creates `wind_actuals` and `wind_forecasts`, including the forecast selection index.
2. `0002_create_data_import_runs` creates operational import diagnostics.

## Operational decisions

- The default cutoff is 10:00 Europe/London on the preceding calendar day; every response displays the policy used.
- Historical GET endpoints send CDN-safe cache headers and include `dataAsOf` based on the latest usable import.
- Upstream network failures are retried only when transient. Failed refreshes never remove existing records.
- `/health` checks process liveness; `/health/ready` will check PostgreSQL and required tables.

## Initial project scope

This initial commit establishes the application shell, configuration, testing, container, and deployment foundations. Database models, migrations, ingestion, selection, metrics, and analysis routes are implemented in the feature phases that follow.
