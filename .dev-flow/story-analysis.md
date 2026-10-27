# Story Analysis: Wind Procurement Insight Backend MVP

## Problem and intended outcome

A UK energy utility needs an auditable view of national wind generation uncertainty at a day-ahead decision point. The service must import Elexon actuals and all available forecast versions into PostgreSQL, reconstruct the latest forecast published by a configurable preceding-day cutoff, compare it with actuals, and return analytical API responses for a separate React dashboard.

The system supports risk awareness only. It must not recommend an electricity purchase quantity.

## Users and primary flows

1. **Operator/developer** runs the authenticated local CLI backfill for 1–31 January 2026. Each dataset import records diagnostics and leaves previously valid records untouched if a refresh fails.
2. **Dashboard user** requests analysis for a supported UK delivery-date range and optional decision time. The API returns selected forecast/actual periods, metrics, coverage, warnings, and source freshness from PostgreSQL only.
3. **Dashboard user/auditor** requests forecast versions for one target instant and sees every version, its cutoff eligibility, and the selected version.
4. **Platform/monitoring** calls liveness and readiness routes without triggering ingestion.

## Acceptance criteria

- FUELHH input is restricted to `fuelType=WIND`; invalid or negative/null records are rejected rather than transformed.
- WINDFOR retains all valid WIND versions under `(start_time, publish_time, fuel_type)` and imports forecasts published before delivery as needed.
- Imports are idempotent, count received/written/duplicate/rejected records, retry transient upstream failures twice, and persist a sanitized terminal import run for each dataset.
- For every requested delivery period, forecast selection uses the latest `publish_time <=` preceding-calendar-day UK cutoff; an exact-cutoff publication is eligible.
- Output explicitly reports `matched`, `missing_forecast`, or `missing_actual`; missing data is never zero-filled.
- Matched periods calculate signed error (`forecast - actual`), absolute error, and half-hour energy error. Aggregate and daily MAE, RMSE, bias, P90 absolute error, coverage, and signed energy totals are finite JSON values.
- `/api/v1/analysis`, `/api/v1/forecast-versions`, `/health`, `/health/ready`, and `/docs` follow the specified contracts, error shape, CORS policy, cache headers, and no-Elexon-at-request-time constraint.
- Docker starts PostgreSQL and the API locally; Vercel has a separate backend entrypoint.

## Affected areas and integration points

| Area | Planned work |
| --- | --- |
| `app/core` | DB/session lifecycle, UTC/London time helpers, request ID/error handling, structured logging |
| `app/models` and `migrations` | Fuel-aware generation models and two schema-only Alembic revisions |
| `app/clients/elexon.py` | HTTPX timeout/retry client for FUELHH and WINDFOR, with source schema validation |
| `app/repositories` | Safe parameterized upsert and read queries |
| `app/services/ingestion.py` and `app/cli/backfill.py` | Repeatable import orchestration and process exit semantics |
| `app/domain` | Pure decision-cutoff, matching, selection, and metric functions |
| `app/services/analysis.py` and `app/api` | Dashboard response composition, warnings, error contract, cache headers, readiness |
| `tests` | Deterministic fixtures plus domain, ingestion, and API tests |
| `README.md`, Compose, Vercel config | Updated operating and deployment instructions |

## Edge cases and failure behavior

- UK daylight-saving rules must be applied with `Europe/London`; never calculate market time with a fixed UTC offset.
- Not every UK delivery day has 48 half-hours, so expected periods must derive from timezone-aware date boundaries.
- Null, invalid timestamp, negative generation, and malformed records are rejected individually and counted.
- No rows eligible for a cutoff result in `missing_forecast`, not a future forecast or zero.
- Partial availability returns HTTP 200 with warnings and coverage; no usable requested data returns `NO_DATA_AVAILABLE` (404).
- Database unavailability maps to sanitized `DATABASE_UNAVAILABLE` (503); unknown failures map to `INTERNAL_ERROR` (500).
- HTTP 4xx upstream responses and payload validation failures are not retried. Network errors and HTTP 5xx retry twice with bounded exponential backoff.
- Import-run messages are sanitized summaries only; no payload, stack trace, credentials, SQL, or hostname is stored.

## Assumptions and non-goals

### Fixed by the assignment

- Delivery range is 2026-01-01 through 2026-01-31.
- Default policy is 10:00 Europe/London on the calendar day preceding delivery.
- The backend is read-only to public callers and does not calculate purchase quantities.
- PostgreSQL is the persistent source cache; Redis, workers, queues, and direct Elexon dashboard calls are out of scope.

### Explicit non-goals

- Demand, price, reserve, contract, solar, thermal, or trading analysis. The persistence model is fuel-aware, but only WIND is imported and analysed in the MVP.
- Authentication, accounts, roles, live market execution, machine learning, multi-year analytics, and real-time features.

## Ambiguities

### Resolved: forecast cadence alignment

The documented FUELHH dataset is half-hourly. A real WINDFOR response sampled during discovery returned hourly `startTime` values. The product requires an output for every half-hour and says forecasts and actuals match by `startTime`, but does not specify how an hourly forecast relates to two half-hour actuals.

**Approved MVP policy:** expand each hourly WINDFOR value to the two half-hour start times in its clock hour. The response and README must disclose that WINDFOR is hourly and that this is an assignment-level modelling policy. The original forecast publication and source start time remain auditable. The series remains half-hourly as required by the assignment.

### Resolved: P90 percentile convention

The required P90 absolute error does not specify its finite-sample method. A nearest-rank method is transparent and easy to verify, but percentile interpolation would yield different values for small fixtures.

**Approved MVP policy:** use nearest-rank P90: after sorting matched absolute errors ascending, select one-based position `ceil(0.90 * n)`. Document and fixture-test this convention.

### Non-blocking: forecast-version audit query policy

The route parameter list specifies only `startTime`, while the response description refers to a supplied or default decision policy. Recommended addition: optional `decisionTime` (default `10:00`) and `timezone` (default/only `Europe/London`) so audit results always mirror analysis requests.

## Verification strategy

- Unit test pure selection at before/exact/after cutoff, latest eligible selection, missing records, January GMT, and summer BST.
- Unit test MAE, RMSE, bias, selected P90 convention, coverage, signed energy, and empty matched data JSON safety.
- Mock HTTPX with fixture payloads for filtering WIND actuals, invalid rows, retries, idempotent upserts, and import-run terminal states.
- API-test success, standard error responses, partial warnings, no-data, cache headers, and health/readiness behavior against a disposable PostgreSQL test database.
- Run Ruff, pytest, Docker Compose startup, Alembic upgrade, CLI backfill, and API smoke checks before delivery. Live Elexon verification remains an operator check and is never part of deterministic tests.
