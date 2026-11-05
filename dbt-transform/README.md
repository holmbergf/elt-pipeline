# dbt-transform — NFL warehouse layer

Raw (Basin Catalog, bucket `nfl`, `ingestion/` zone)
  `nfl.raw_nfl_games` (nflverse) · `nfl.raw_nfl_spreads` / `nfl.raw_nfl_totals` (Covers)
        │
        ▼  bronze: views, 1:1 casts only (models/connector/nfl/bronze)
Silver staging: clean_nfl_games / clean_nfl_spreads / clean_nfl_totals
        │
        ▼  silver core: dim_nfl_date, dim_nfl_teams, fct_nfl_games,
           fct_nfl_betting_settled, fct_nfl_betting_upcoming, fct_nfl_team_performance
Gold: analytics_nfl_team_rankings, analytics_nfl_team_betting_stats,
      analytics_nfl_upcoming_matchups
Semantic (human surface, views): semantic_team_season_form,
      semantic_game_results, semantic_upcoming_matchups — fractions 0-1
      at 2dp, integer W/L/T, *_points spreads/lines. Streamlit should
      read the `semantic` namespace, not gold.

## Storage layout (bucket `nfl`, provisioned by ../infra Terraform)

| Zone | Contents |
|---|---|
| `ingestion/raw/nfl/…` | Partitioned raw Parquet (content-addressed, idempotent) |
| `ingestion/_manifests/…` | Ingestion run manifests — the watermark/state store |
| `__r2_data_catalog/…` | Catalog-managed Iceberg data (raw `nfl.*`, warehouse `silver.*`, `gold.*`) |
| `data_warehouse/{silver,gold}/*.parquet` | Parquet exports of every published warehouse model |

## Write-path decision (spike, 2026-11-04)

- DuckDB **can** ATTACH to Basin Catalog (REST + bearer token), read raw
  Iceberg tables, and CREATE/INSERT Iceberg tables.
- DuckDB-Iceberg does **not** support `CREATE OR REPLACE TABLE`, which is
  dbt's `table` materialization — so dbt cannot write silver/gold directly.
- Basin Catalog rejects custom table locations outside
  `s3://<bucket>/__r2_data_catalog`, so Iceberg tables cannot physically sit
  under `data_warehouse/`.

Chosen path: dbt builds silver/gold in DuckDB → `elt_ingest.publish_warehouse`
overwrites the `silver`/`gold` Iceberg tables (PyIceberg) and exports Parquet
to `data_warehouse/{silver,gold}/`. Bronze stays views over raw.

## Run

```bash
source ../.venv/bin/activate
# dev: local DuckDB over the local ingestion mirror (data/raw/ingestion)
dbt build --profiles-dir .
# prod: raw Parquet from R2 (RAW_BASE_PATH=s3://nfl/ingestion, R2_* secrets),
# then publish Iceberg + data_warehouse/ exports
dbt seed --target prod --profiles-dir .
dbt build --target prod --profiles-dir .
python -m elt_ingest.publish_warehouse warehouse.duckdb
```

Tests: `_schema.yml` (unique/not_null/relationships), source freshness
(8d warn / 15d error), singular tests in `tests/` (duplicate games,
betting-join coverage at warn severity). Full refresh everywhere;
switch `fct_*` to incremental merge on `game_id` when a full build
exceeds ~10 minutes.

## CI

`ci/dbt` (path-filtered to `dbt-transform/**`) runs a slim build
(`state:modified+` against the production manifest from the latest
`nfl-ingest` run, full-build fallback) plus all data tests, against the
10-row mock raw fixtures in `tests/fixtures/`.
