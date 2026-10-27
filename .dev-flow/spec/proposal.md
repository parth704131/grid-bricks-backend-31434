# Proposal: Wind Procurement Insight Backend MVP

## Motivation

The dashboard needs a reliable, auditable API for explaining how much national wind generation was forecast to be available at a UK day-ahead decision time and how that forecast differed from actual outturn. Elexon must not be queried during dashboard requests.

## Scope

- Fuel-aware PostgreSQL generation models and two focused Alembic migrations; only WIND is imported and analysed in the MVP.
- Elexon FUELHH/WINDFOR client, source validation, idempotent backfill CLI, and import diagnostics.
- Pure UK cutoff, forecast selection, matching, and metric functions.
- Analysis, forecast-version audit, liveness, and readiness APIs with error contract, CORS, and cache headers.
- Deterministic fixtures and unit/integration/API tests.
- Updated Docker, Vercel, and operating documentation.

## Approved data policy

WINDFOR is hourly whereas FUELHH is half-hourly. To meet the assignment's required half-hour response contract, a selected hourly forecast is expanded to both half-hour periods beginning in that hour. Responses disclose this as an assignment-level modelling policy. P90 uses the nearest-rank convention.

## Acceptance criteria

- The complete requirements in the approved user story are implemented, including all mandatory endpoint fields, statuses, metrics, error codes, and operational constraints.
- Public analysis requests read only PostgreSQL and display a relevant `dataAsOf` value.
- Imports are repeatable without duplicates and retain historical forecast versions.
- Tests are deterministic and cover every listed required test scenario.

## Non-goals

Demand/purchase recommendations, price data, live trading, accounts, background workers, Redis, ingestion or analysis of other generation types, and frontend implementation remain out of scope.
