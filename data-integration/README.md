# data-integration

Ingestion for both sports:

- **NFL** — games from nflverse (one CSV, no scraping), spreads/totals
  scraped from Covers consensus pages.
- **NCAAF** — games from ESPN's public scoreboard API (with Top-25
  ranks), spreads/totals from the Covers NCAAF consensus pages.

Lands partitioned Parquet in Cloudflare R2 and appends to Basin Catalog
Iceberg tables (`nfl.raw_nfl_*` in bucket `nfl`, `ncaaf.raw_ncaaf_*` in
bucket `ncaaf`).

## Setup

```bash
source ../.venv/bin/activate
pip install -e ".[iceberg,dev]"
cp ../.env.example ../.env   # fill in R2 + Basin values
```

Without R2 credentials the storage backend falls back to `local`
(`data/raw/` with the same key layout), so the whole flow runs offline.

## Run

```bash
elt-ingest games    # incremental (watermark from run manifests)
elt-ingest spreads
elt-ingest totals
elt-ingest all --mode backfill --start-year 2015
elt-ingest --sport ncaaf all        # NCAAF (ESPN games + Covers markets)
```

`GAMES_SOURCE=covers` selects the Covers matchups fallback for NFL
games (default: `nflverse`).

Market jobs scrape game dates that are not yet covered, per the run
manifests. A date counts as covered only by a scrape written on or
after it — Covers pages bleed neighbouring dates, so an early partial
page must not mark a future slate as done.

## Layout

- `src/elt_ingest/nflverse.py` — NFL games source (single CSV download)
- `src/elt_ingest/cfb.py` — NCAAF games from ESPN (Eastern sports dates,
  Top-25 ranks; TBD placeholder fixtures are skipped)
- `src/elt_ingest/scrape.py` — Covers scrapers (consensus + matchups, retries)
- `src/elt_ingest/clean.py` — column mapping, date parsing, dedupe, content hash
- `src/elt_ingest/storage.py` — R2/local writers, manifests, `StateStore` watermarks
- `src/elt_ingest/iceberg.py` — Basin Catalog raw tables, retrying catalog writes
- `src/elt_ingest/publish_warehouse.py` — publish dbt silver/gold/semantic to
  Iceberg + `data_warehouse/` Parquet (requires the R2 backend; fails closed
  on local storage)
- `src/elt_ingest/jobs.py` / `jobs_cfb.py`, `cli.py` — jobs and entry point
- `tests/` — pytest (mocked sources, offline)

State note: spreads/totals jobs depend on games having run first.
