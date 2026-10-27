# Repository Guidance

## Scope and safety

- This repository is the API backend for Wind Procurement Insight. Keep it independent of the React frontend.
- Treat the database as a persistent record of imported Elexon data. Never replace missing data with zero.
- Do not run destructive SQL (`DELETE`, `TRUNCATE`, `DROP`, `ALTER ... DROP`, data resets, or schema resets) unless the user explicitly authorizes the exact target.
- Never run broad or recursive filesystem deletion commands. Do not remove files, directories, Docker volumes, databases, migrations, branches, or Git history without explicit approval of the exact target.
- Do not force-push, push directly to `main`, rewrite published history, or merge branches without explicit user approval. Use feature branches and pull requests for feature work.
- Do not run `git reset --hard`, `git clean`, `git checkout --`, `git restore` on user files, or equivalent discard operations unless explicitly authorized.
- Use SQLAlchemy expressions or bound parameters for every database query. Never create SQL by interpolating request values into SQL strings.
- Validate and constrain every API input before it reaches a repository, query, URL, filesystem path, or external request.
- Do not disable TLS verification, CORS restrictions, authentication protections added in the future, dependency integrity checks, or test failures merely to unblock a task.
- Do not put credentials, source payloads, stack traces, database URLs, or internal hostnames in commits, logs, or API responses.
- Never log authorization headers, environment variables, database connection strings, or raw upstream payloads.
- Do not add a public HTTP endpoint that triggers ingestion/backfill.
- Treat production database access as read-only unless the user has explicitly requested an approved ingestion or migration operation.

## Engineering conventions

- Python 3.12+, FastAPI, Pydantic v2, SQLAlchemy 2, Alembic, HTTPX, and pytest are the approved MVP stack.
- Store timestamps as timezone-aware UTC datetimes. Derive market dates and cutoffs using `Europe/London` and `zoneinfo`.
- Keep forecast selection and metric calculations pure functions under `app/domain/`.
- Use `Decimal` for persisted MW values and only JSON-safe finite numeric values in responses.
- Keep database access in repositories/services; API routes should validate input and map errors only.
- Use focused Alembic migrations. Never load source data from migrations.

## Required verification

- Run `pytest` for every change affecting Python behavior.
- Run `ruff check .` and `ruff format --check .` before committing when dependencies are installed.
- Keep tests deterministic; never use the live Elexon API in the test suite.
