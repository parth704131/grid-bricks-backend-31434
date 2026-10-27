# Wind Procurement Insight Backend

FastAPI backend for analysing UK national wind-generation forecasts against actual outturn. It recreates the latest forecast available before a day-ahead decision cutoff and returns dashboard-ready accuracy metrics.

## Status

Project foundation is in place. The next phase adds the Elexon import pipeline, PostgreSQL schema, forecast selection, and analysis API.

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
```

The liveness endpoint is available at `http://localhost:8000/health` and interactive API documentation at `http://localhost:8000/docs`.

For local Python development:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload
pytest
```

## Configuration

See `.env.example`. Never commit `.env`. Production must use a managed PostgreSQL pooled `DATABASE_URL` and set `FRONTEND_ORIGIN` to the deployed React application.

## Decision-cutoff assumption

Unless a request specifies another valid time, the day-ahead decision cutoff is **10:00 Europe/London on the calendar day before delivery**. Timestamps are stored in UTC; UK timezone conversion uses IANA timezone rules.

## API

The intended public API is:

- `GET /health`
- `GET /health/ready`
- `GET /api/v1/analysis`
- `GET /api/v1/forecast-versions`

Only the process liveness endpoint is active in this foundation commit.

## AI-tool disclosure

This repository was bootstrapped with assistance from OpenAI Codex. All implementation choices and changes should be reviewed and verified before production use.

## License

MIT. See [LICENSE](LICENSE).
