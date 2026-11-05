# data-integration

NFL ingestion: games from nflverse (one CSV, no scraping), spreads/totals
scraped from Covers. Lands partitioned Parquet in Cloudflare R2 and appends
to Basin Catalog Iceberg tables.

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
```

`GAMES_SOURCE=covers` selects the Covers matchups fallback for games
(default: `nflverse`).

## Layout

- `src/elt_ingest/nflverse.py` — games source (single CSV download)
- `src/elt_ingest/scrape.py` — Covers scrapers (consensus + matchups, retries)
- `src/elt_ingest/clean.py` — column mapping, date parsing, dedupe, content hash
- `src/elt_ingest/storage.py` — R2/local writers, manifests, `StateStore` watermarks
- `src/elt_ingest/iceberg.py` — Basin Catalog tables `nfl.raw_nfl_*`
- `src/elt_ingest/publish_warehouse.py` — publish dbt silver/gold to Iceberg
- `src/elt_ingest/jobs.py`, `cli.py` — incremental/backfill jobs and entry point
- `tests/` — pytest

State note: spreads/totals jobs depend on games having run first.
