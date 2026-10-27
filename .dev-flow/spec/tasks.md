# Implementation Tasks

1. Add database configuration/session lifecycle, error types, request IDs, and readiness scaffolding with tests.
2. Add fuel-aware SQLAlchemy generation models and Alembic configuration; create migration `0001_create_generation_data_tables`.
3. Create `0002_create_data_import_runs`, repositories, and idempotent PostgreSQL upsert helpers.
4. Build source schemas and resilient HTTPX Elexon client with fixture-driven retry tests.
5. Implement ingestion service and `python -m app.cli.backfill`, including sanitized import-run finalization and CLI exit semantics.
6. Implement pure London cutoff, hourly expansion, forecast selection, and metric domain functions with required unit tests.
7. Implement analysis service, analysis response schemas, query validation, standard errors, cache headers, and API tests.
8. Implement forecast-version audit endpoint and database-backed readiness check.
9. Update Docker, Vercel, README, fixtures, and operating instructions; run migrations, tests, linting, Docker smoke test, and a controlled January backfill.
10. Perform independent review, test hardening, and final delivery verification.
