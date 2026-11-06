# elt-pipeline

Cloudflare-based ELT pipeline for NFL and NCAAF data: ingest games and betting
markets, land them in R2, model them with dbt, and serve analytics from Apache
Iceberg tables in Basin Catalog.

Production entry point is GitHub Actions — the pipeline runs autonomously on
schedule (see [Autonomous operation](#autonomous-operation)).

## Architecture

```text
nflverse (games CSV) ─┐
Covers (spreads,      ├─ elt-ingest ─► R2 bucket `nfl`
         totals)      ┘   (Python)     ├─ ingestion/raw/nfl/…   partitioned Parquet
                                       ├─ ingestion/_manifests/…  run state / watermarks
                                       └─ Iceberg nfl.raw_nfl_*   (Basin Catalog)
                                              │
                        dbt (DuckDB) ─────────┤ bronze views (1:1 casts)
                                              ├─ silver: clean staging, dims, facts
                                              └─ gold: analytics marts
                                                     │
                        publish_warehouse ─► Iceberg silver.* / gold.*
                                           + data_warehouse/{silver,gold}/*.parquet
```

- **Ingestion** ([`data-integration/`](data-integration/)): games from
  [nflverse](data-integration/src/elt_ingest/nflverse.py) (one CSV download,
  no scraping), spreads/totals scraped from Covers. Writes are content-addressed
  and idempotent — re-runs write zero new objects. State (watermarks,
  missing-date detection) lives in R2 run manifests, not a database.
- **Warehouse** ([`dbt-transform/`](dbt-transform/)): 15 dbt models —
  bronze views over raw, silver staging/core (dims, facts, betting), gold
  analytics — with schema tests, source freshness, and singular data tests.
  dbt builds in DuckDB; silver/gold are published to Basin Catalog Iceberg
  tables via PyIceberg (DuckDB cannot `CREATE OR REPLACE` Iceberg tables —
  see [dbt-transform/README.md](dbt-transform/README.md) for the write-path
  decision) and exported as Parquet under `data_warehouse/`.
- **Infrastructure** ([`infra/`](infra/)): Terraform provisions the R2 bucket
  `nfl` and its Basin Catalog (`cloudflare_r2_data_catalog`). Nothing is
  provisioned by hand or by Wrangler.
- **NCAAF connector**: mirrors NFL end-to-end in its own bucket `ncaaf`
  (Terraform-provisioned, same `ingestion/` + `data_warehouse/` layout).
  Games come from ESPN's scoreboard API (`elt-ingest --sport ncaaf`, with
  Top-25 ranks from `curatedRank`), spreads/totals from the Covers NCAAF
  consensus pages. dbt models under `models/connector/ncaaf/` mirror the NFL
  bronze/silver/gold/semantic layers, adding `home_rank`/`away_rank`/
  `is_top25_matchup`; the Covers-code → ESPN-name mapping lives in
  `seeds/ncaaf_team_mappings.csv`. Published to the `ncaaf` Basin Catalog
  with `publish_warehouse --sport=ncaaf`.

## Repository structure

```text
elt-pipeline/
├── data-integration/       # Ingestion package (elt-ingest CLI)
│   ├── src/elt_ingest/     # nflverse, Covers scrapers, storage, Iceberg, jobs
│   ├── tests/              # pytest (mocked sources, offline)
│   └── Dockerfile          # Stateless runner image
├── dbt-transform/          # dbt warehouse (DuckDB)
│   ├── models/connector/nfl/{bronze,silver,gold}/
│   └── tests/fixtures/     # 10-row mock raw samples for CI
├── infra/                  # Terraform: R2 bucket `nfl` + Basin Catalog
└── .github/workflows/      # Autonomous ingest + per-module CI
```

## Autonomous operation

| Workflow | Trigger | What it does |
|---|---|---|
| `nfl-ingest` | Sun 07:00, Mon 13:00, Thu 13:00 Pacific (15:00/21:00 UTC) + manual | `elt-ingest all` → `dbt build --target prod` → publish warehouse tables; ahead of game days |
| `ci/data-integration` | Changes under `data-integration/**` | pytest, byte-compile, CLI smoke |
| `ci/dbt` | Changes under `dbt-transform/**` | Slim dbt build (`state:modified+` vs prod manifest) + data tests on 10-row mock fixtures |
| `ci/infra` | Changes under `infra/**`, PR comments | fmt/validate; `.deploy` / `.deploy noop` IssueOps via branch-deploy |

Workflows are path-filtered and independent: a dbt-only change runs only
`ci/dbt`, etc.

Terraform applies happen via the branch-deploy flow (`.deploy` on a PR,
production environment). **Prerequisite:** the repo variable
`TF_STATE_BACKEND_CONFIG` must point at a remote backend — state is
currently local-only, and the deploy job deliberately refuses to apply
against an empty runner-local state until that is configured.

## Local development

Prerequisites: Python 3.11, Terraform ≥ 1.5 (infra only).

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e "./data-integration[iceberg,dev]" dbt-duckdb duckdb
cp .env.example .env   # fill in values, never commit .env
```

```bash
# Ingest (local storage backend when R2 keys are absent)
elt-ingest games
elt-ingest all --mode backfill --start-year 2015

# Warehouse
cd dbt-transform
dbt build --profiles-dir .                      # dev: local DuckDB over data/raw/ingestion
RAW_BASE_PATH=s3://nfl/ingestion dbt build --target prod --profiles-dir .
python -m elt_ingest.publish_warehouse warehouse.duckdb

# Tests
python -m pytest data-integration/tests -q
```

## Configuration

Local runs use `.env`; GitHub Actions uses repository secrets — the variable
names are identical. See [`.env.example`](.env.example) for the full list.

| Secret | Source |
|---|---|
| `R2_ACCOUNT_ID` | Cloudflare account ID |
| `R2_ACCESS_KEY_ID` / `R2_SECRET_ACCESS_KEY` | R2 API token S3 credentials |
| `R2_S3_HOST` | `<account-id>.r2.cloudflarestorage.com` |
| `BASIN_CATALOG_URI` / `BASIN_WAREHOUSE` | `terraform -chdir=infra output` |
| `BASIN_TOKEN` | R2 API token value (catalog permission) |
| `CLOUDFLARE_API_TOKEN` | Terraform only (branch-deploy / manual runs) |

## Data notes

- Games cover 1999–present from nflverse; warehouse history in production
  starts at the 2015 season. Yards/turnovers are not in the nflverse
  dataset and stay null (bronze-only columns; nothing downstream uses them).
- Raw schemas are frozen contracts in `elt_ingest/iceberg.py`; a source
  schema change fails bronze casts loudly instead of drifting.
- Full-refresh dbt builds throughout; the switch to incremental merge on
  `game_id` is planned when a full build exceeds ~10 minutes.
