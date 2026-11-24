# elt-pipeline

[![ingest](https://github.com/holmbergf/elt-pipeline/actions/workflows/ingest.yml/badge.svg)](https://github.com/holmbergf/elt-pipeline/actions/workflows/ingest.yml)
[![ci/data-integration](https://github.com/holmbergf/elt-pipeline/actions/workflows/data-integration.yml/badge.svg)](https://github.com/holmbergf/elt-pipeline/actions/workflows/data-integration.yml)
[![ci/dbt](https://github.com/holmbergf/elt-pipeline/actions/workflows/dbt.yml/badge.svg)](https://github.com/holmbergf/elt-pipeline/actions/workflows/dbt.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

Cloudflare-based ELT pipeline for NFL and NCAAF data: ingest games and betting
markets, land them in R2, model them with dbt, and serve analytics from Apache
Iceberg tables in Basin Catalog.

## Live dashboard

The **Matchup Board** — upcoming NFL/NCAAF matchups with lines, market
consensus, team form, trends, and consensus-band history — is a
Streamlit app in [`dashboard/`](dashboard/):

**▶ [Open the live board](https://dzzheeqfpuy774nutwccl2.streamlit.app/)**

To run or deploy your own copy (it reads the published warehouse
exports with a read-only R2 token), see
[dashboard/README.md](dashboard/README.md).

Production entry point is GitHub Actions — the pipeline runs autonomously on
schedule (see [Autonomous operation](#autonomous-operation)).

For the full design — ingestion, R2 layout, Basin Catalog/Iceberg, dbt
layers, publishing, orchestration, dashboard, and why each technology was
chosen — see [docs/architecture.md](docs/architecture.md).

## Architecture

```text
nflverse (games CSV) ─┐
Covers NFL consensus ─┤  elt-ingest ─► R2 bucket `nfl`
                      ┘   (Python)     ├─ ingestion/raw/nfl/…   partitioned Parquet
ESPN scoreboard API ──┐                ├─ ingestion/_manifests/…  run state / watermarks
Covers NCAAF consensus┤  elt-ingest ─► └─ Iceberg nfl.raw_nfl_* / ncaaf.raw_ncaaf_*
                      ┘  --sport ncaaf    R2 bucket `ncaaf` (same layout)
                                              │
                        dbt (DuckDB) ─────────┤ bronze views (1:1 casts)
                                              ├─ silver: clean staging, dims, facts
                                              ├─ gold: analytics marts
                                              └─ semantic: human-readable layer
                                                     │
                        publish_warehouse ─► Iceberg silver.* / gold.* / semantic.*
                                           + data_warehouse/{silver,gold,semantic}/*.parquet
                                                     │
                        Streamlit dashboard (NFL + NCAAF sections)
```

- **Ingestion** ([`data-integration/`](data-integration/)): games from
  [nflverse](data-integration/src/elt_ingest/nflverse.py) (one CSV download,
  no scraping), spreads/totals scraped from Covers. Writes are content-addressed
  and idempotent — re-runs write zero new objects. State (watermarks,
  missing-date detection) lives in R2 run manifests, not a database.
- **Warehouse** ([`dbt-transform/`](dbt-transform/)): 46 dbt models
  (23 per sport) — bronze views over raw, silver staging/core (dims, facts,
  betting), gold analytics, and a semantic layer with human-readable names
  (fractions at 2 decimals, `against_the_spread_*`, consensus/line bands) —
  with schema tests, source freshness, and singular data tests.
  dbt builds in DuckDB; silver/gold/semantic are published to Basin Catalog
  Iceberg tables via PyIceberg (DuckDB cannot `CREATE OR REPLACE` Iceberg
  tables — see [dbt-transform/README.md](dbt-transform/README.md) for the
  write-path decision) and exported as Parquet under `data_warehouse/`.
- **Infrastructure** ([`infra/`](infra/)): Terraform provisions the R2
  buckets `nfl` and `ncaaf` and their Basin Catalogs
  (`cloudflare_r2_data_catalog`). Nothing is provisioned by hand or by Wrangler.
- **NCAAF connector**: mirrors NFL end-to-end in its own bucket `ncaaf`
  (Terraform-provisioned, same `ingestion/` + `data_warehouse/` layout).
  Games come from ESPN's scoreboard API (`elt-ingest --sport ncaaf`, with
  Top-25 ranks from `curatedRank`), spreads/totals from the Covers NCAAF
  consensus pages. Game dates are US Eastern sports dates (ESPN kickoff
  timestamps are UTC; using the UTC date shifts evening kickoffs a day and
  breaks the Covers join). dbt models under `models/connector/ncaaf/`
  mirror the NFL layers, adding `home_rank`/`away_rank`/`is_top25_matchup`;
  the Covers-code → ESPN-name mapping lives in
  `seeds/ncaaf_team_mappings.csv`. Published to the `ncaaf` Basin Catalog
  with `publish_warehouse --sport=ncaaf`.
- **Dashboard** ([`dashboard/`](dashboard/)): Streamlit app with an NFL
  and an NCAAF section (sidebar sport switcher, same pages:
  Upcoming/next slate with a historical-games view, Team Form, Trends,
  Consensus). It reads the published `data_warehouse/` Parquet exports
  from both buckets with a read-only R2 token (see
  [dashboard/README.md](dashboard/README.md)). Public read-only by
  default (optional `app_password` gate); deployed on Streamlit
  Community Cloud directly from this repository.

## Repository structure

```text
elt-pipeline/
├── data-integration/       # Ingestion package (elt-ingest CLI)
│   ├── src/elt_ingest/     # nflverse, Covers scrapers, storage, Iceberg, jobs
│   ├── tests/              # pytest (mocked sources, offline)
│   └── Dockerfile          # Stateless runner image
├── dbt-transform/          # dbt warehouse (DuckDB)
│   ├── models/connector/{nfl,ncaaf}/{bronze,silver,gold,semantic}/
│   ├── seeds/              # team mappings (NFL + Covers→ESPN for NCAAF)
│   └── tests/fixtures/     # 10-row mock raw samples (both sports) for CI
├── dashboard/              # Streamlit app (NFL + NCAAF) + tests
├── infra/                  # Terraform: R2 buckets `nfl`/`ncaaf` + Basin Catalogs
└── .github/workflows/      # Autonomous ingest + per-module CI
```

## Autonomous operation

| Workflow | Trigger | What it does |
|---|---|---|
| `ingest` | NFL Sun 07:00, Mon 13:00, Thu 13:00 Pacific; NCAAF Fri + Sat 07:00 Pacific (15:00/21:00 UTC) + manual | `elt-ingest all` (NFL + `--sport ncaaf`) → `dbt build --target prod` → publish warehouse tables; ahead of game days |
| `ci/data-integration` | Changes under `data-integration/**` | pytest, byte-compile, CLI smoke |
| `ci/dbt` | Changes under `dbt-transform/**` | Full dbt build + data tests on 10-row mock fixtures (both sports); slim selection vs prod manifest reported informationally |
| `ci/infra` | Changes under `infra/**`, PR comments | fmt/validate; `.deploy` / `.deploy noop` IssueOps via branch-deploy |

Workflows are path-filtered and independent: a dbt-only change runs only
`ci/dbt`, etc.

Terraform applies happen via the branch-deploy flow (`.deploy` on a PR,
production environment). State is remote (S3 backend on R2, bucket
`elt-tfstate`); the backend config is account-specific, so only the
template `infra/backend.hcl.example` is committed — copy it to
`infra/backend.hcl` locally (the deploy job renders it from the
template with the repo's account ID). The repo variable
`TF_STATE_BACKEND_CONFIG` points the deploy job at it, and the job
refuses to apply against an empty runner-local state if it is unset.

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
elt-ingest --sport ncaaf all        # NCAAF: ESPN games + Covers markets

# Warehouse
cd dbt-transform
dbt build --profiles-dir .                      # dev: local DuckDB over data/raw/ingestion
RAW_BASE_PATH=s3://nfl/ingestion RAW_BASE_PATH_NCAAF=s3://ncaaf/ingestion dbt build --target prod --profiles-dir .
python -m elt_ingest.publish_warehouse warehouse.duckdb
python -m elt_ingest.publish_warehouse warehouse.duckdb --sport=ncaaf

# Tests
python -m pytest data-integration/tests -q
python -m pytest dashboard/tests -q

# Dashboard (local)
LOCAL_WAREHOUSE_DIR=/path/to/mirror streamlit run dashboard/streamlit_app.py
```

## Configuration

Local runs use `.env`; GitHub Actions uses repository secrets — the variable
names are identical. See [`.env.example`](.env.example) for the full list.

| Secret | Source |
|---|---|
| `R2_ACCOUNT_ID` | Cloudflare account ID |
| `R2_ACCESS_KEY_ID` / `R2_SECRET_ACCESS_KEY` | R2 API token S3 credentials |
| `R2_S3_HOST` | `<account-id>.r2.cloudflarestorage.com` |
| `BASIN_CATALOG_URI` / `BASIN_WAREHOUSE` | `terraform -chdir=infra output` (NCAAF values derive from these; `NCAAF_BASIN_*` overrides optional) |
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
- NCAAF history currently covers the 2025 season onward (ESPN feed).
  Covers market rows for FCS-vs-FCS games cannot join the FBS game feed
  and drop out in silver; a handful of Covers team codes (e.g. `GSU`) are
  mapped by best convention in the seed and may mis-join in rare cases.
- The dashboard's Upcoming page filters the silver upcoming fixtures to the
  current Pacific date at read time (next slate shown when idle), so it
  never displays a stale build-day game as "today".
- "Today" is timezone-sensitive throughout: game dates are US Eastern
  sports dates, the warehouse keeps fixtures by the Eastern date (CI
  builds run in UTC, where the date rolls over at 19:00 ET), and the
  dashboard filters by Pacific date when the page loads.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Security reports:
[SECURITY.md](SECURITY.md) (please don't open public issues for
vulnerabilities).

## License

[MIT](LICENSE). Game and market data are provided by their respective
sources (nflverse, ESPN, Covers) under their own terms; this license
covers the code in this repository, not the upstream data.
