# Wind Procurement Insight Backend

FastAPI backend for analysing UK national wind-generation forecasts against actual outturn. It recreates the latest forecast available before a day-ahead decision cutoff and returns dashboard-ready accuracy metrics.

## Status

The backend MVP is implemented locally. It imports Elexon FUELHH wind actuals and
WINDFOR forecast versions into PostgreSQL, reconstructs the forecast available at a
day-ahead cutoff, and exposes dashboard-ready analysis endpoints.

## Tech stack

- Python 3.12
- FastAPI and Pydantic v2
- PostgreSQL, SQLAlchemy 2, and Alembic
- HTTPX for Elexon ingestion
- Pytest and Ruff
- Docker Compose for local development

## Local setup

```bash
cp .env.example .env
docker compose up --build
docker compose exec backend alembic upgrade head
docker compose exec backend python -m app.cli.backfill \\
  --delivery-from 2026-01-01 \\
  --delivery-to 2026-01-31
```

The API is available at `http://localhost:8000`; interactive documentation is at
`http://localhost:8000/docs`.

For local Python development:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload
pytest
ruff check .
ruff format --check .
```

## Configuration

See `.env.example`. Never commit `.env`. Production must use a managed PostgreSQL pooled `DATABASE_URL` and set `FRONTEND_ORIGIN` to the deployed React application.

## Decision-cutoff assumption

Unless a request specifies another valid time, the day-ahead decision cutoff is **10:00 Europe/London on the calendar day before delivery**. Timestamps are stored in UTC; UK timezone conversion uses IANA timezone rules.

## API

All analysis responses are calculated from PostgreSQL; dashboard requests never call Elexon.

- `GET /health`
- `GET /health/ready`
- `GET /api/v1/analysis?from=2026-01-01&to=2026-01-31&decisionTime=10:00`
- `GET /api/v1/analysis/periods?from=2026-01-01&to=2026-01-31&decisionTime=10:00&page=1&pageSize=20`
- `GET /api/v1/forecast-versions?startTime=2026-01-01T10:00:00Z&decisionTime=10:00`

The MVP accepts only the January 2026 delivery range. `decisionTime` is optional and
uses `DEFAULT_DECISION_TIME` when omitted. Analysis requests return partial data with
coverage and warnings when source periods are missing. Public errors use a safe,
request-ID-bearing error envelope.

The paginated periods endpoint defaults to 20 rows per page and accepts a maximum of
100 rows. It is intended for the detailed dashboard table; the analysis endpoint remains
the source for complete chart series and aggregate metrics.

## Import behaviour

The backfill command is idempotent. It validates each source record, ignores non-WIND
FUELHH rows, keeps all valid WINDFOR versions, records an import run for each dataset,
and skips invalid records without replacing them with zero. Network timeouts and Elexon
5xx responses are retried twice with exponential backoff; existing imported data remains
available if a refresh fails.

The persistence model uses generic generation tables with a `fuel_type` key, so it can
support additional generation sources later. This MVP intentionally imports and analyses
only `WIND`, as required by the assignment.

Elexon's WINDFOR dataset publishes hourly forecasts while FUELHH actuals are half-hourly.
For this MVP, the selected hourly forecast is applied to each of its two half-hour delivery
periods. The source forecast versions themselves are stored unchanged for auditability.

## Project layout

| Path | Purpose |
| --- | --- |
| `app/api` | Public FastAPI routes and HTTP error mapping |
| `app/cli` | Safe, non-HTTP backfill command |
| `app/clients` | Elexon HTTP client with bounded retries |
| `app/domain` | Pure cutoff, selection, and metric logic |
| `app/models`, `app/repositories` | SQLAlchemy persistence layer |
| `app/services` | Ingestion and analysis use-cases |
| `migrations` | Schema-only Alembic migrations |
| `tests` | Deterministic API and domain tests |

## Deployment

Deploy this `backend` directory as its own Vercel project and configure a pooled managed
PostgreSQL `DATABASE_URL` plus the production `FRONTEND_ORIGIN`. Run migrations and the
January backfill against that database before verifying `/health`, `/health/ready`, `/docs`,
and an analysis URL from an incognito browser.

## AI-tool disclosure

This repository was bootstrapped with assistance from OpenAI Codex. All implementation choices and changes should be reviewed and verified before production use.

## License

MIT. See [LICENSE](LICENSE).
