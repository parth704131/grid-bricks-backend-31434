# Design: Wind Procurement Insight Backend MVP

## Components

```text
CLI -> ElexonClient -> Pydantic source schemas -> IngestionService -> Repositories -> PostgreSQL
                                                                      |
HTTP -> FastAPI routes -> AnalysisService -> pure domain functions ---+
```

### Persistence

- `generation_actuals(start_time, fuel_type, generation_mw, ingested_at, PRIMARY KEY(start_time, fuel_type))`
- `generation_forecasts(start_time, publish_time, fuel_type, generation_mw, ingested_at, UNIQUE(start_time, publish_time, fuel_type))`
- `data_import_runs(id, dataset, started_at, completed_at, status, counts, error_message)`
- Index `generation_forecasts(fuel_type, start_time, publish_time DESC)` supports selection.
- Alembic revision 0001 creates the first two tables and index; revision 0002 creates import runs only.

### Import strategy

- Create a `running` import run before contacting Elexon.
- Query FUELHH by settlement dates and `fuelType=WIND`; defensively filter `WIND` again in application code.
- Query WINDFOR by publish-time windows that begin before the delivery range, retain all valid WIND source versions whose delivery instant belongs to the requested UK dates, and expand only in analysis—not in persisted source data.
- Validate each individual payload item; count and skip invalid rows.
- Upsert with PostgreSQL `ON CONFLICT DO UPDATE` for source corrections while retaining every forecast version.
- Retry connection/timeouts and 5xx responses twice; do not retry normal 4xx or invalid payloads.
- Finish every run with a sanitized `successful`, `partial`, or `failed` status. A command exits non-zero when no usable data is produced.

### Analysis strategy

1. Derive all expected half-hour delivery periods from `Europe/London` date boundaries, converting each to UTC.
2. For each period, derive the preceding-calendar-day cutoff in `Europe/London`, then UTC.
3. Retrieve latest forecast version on/before cutoff for the source hour. Expand the hourly result to both half-hours in that hour.
4. Retrieve exact FUELHH actual by half-hour start time.
5. Label `matched`, `missing_forecast`, or `missing_actual` and compute values only for matches.
6. Calculate overall and daily metrics with `Decimal`; serialize finite JSON numbers or `null` for unavailable metrics.

### HTTP contract

- Use `/api/v1` routers for analysis and forecast versions; health remains unprefixed.
- A request-ID middleware creates/propagates a safe request ID. Exception handlers return the required error envelope.
- Only `Europe/London` is accepted for the MVP timezone field. Date range is restricted to January 2026.
- Analysis sends `Cache-Control: public, s-maxage=3600, stale-while-revalidate=86400`.
- Forecast audit accepts optional `decisionTime` and `timezone`, matching analysis defaults.

## Engineering invariants

### Resource lifecycle and async safety

- HTTPX clients and SQLAlchemy sessions are created/closed through context-managed lifecycles.
- Routes never share mutable session state across requests.
- CLI errors always finalize the import run in a terminal state in a `finally`/guarded error path.

### Error and empty-state recovery

- Existing valid data is never deleted by a failed refresh.
- Partial data is successful API output with warnings; no-data and unavailable-database states are distinct.
- Error messages are sanitized at the boundary and do not leak SQL, stack traces, hosts, credentials, headers, or raw payloads.

### Performance

- Analysis uses one bounded range query per source table, groups forecast versions by source hour, and selects in memory for the small January MVP range. The supporting index is `(fuel_type, start_time, publish_time DESC)`.
- One range query per source table serves an analysis request; avoid an N+1 query per half-hour.
- Metrics remain in application memory for the small January MVP range.

### Security and privacy

- Pydantic validates all external and query input.
- Repositories use SQLAlchemy/bound parameters only.
- CORS allows configured frontend origins only; public routes are read-only.
- Configuration comes from environment variables; no secrets are committed or returned.

## Risks and mitigations

| Risk | Mitigation |
| --- | --- |
| Hourly/half-hourly cadence mismatch | Explicit expansion policy, disclosed in API warnings/documentation, source rows untouched |
| Upstream availability/rate limits | Timeouts, bounded retries, persisted cache, no live requests in analytics |
| DST ambiguity | `zoneinfo.ZoneInfo('Europe/London')`, delivery-date boundaries rather than fixed period counts |
| Partial historical data | Explicit statuses, coverage, warnings, and latest usable `dataAsOf` |
| Deployment DB connection limits | Managed pooled `DATABASE_URL`, conservative SQLAlchemy pooling settings |
