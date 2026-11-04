# data-integration

NFL ingestion: games from nflverse (one CSV, no scraping; `GAMES_SOURCE=covers|pfr` selects the scrapers in `scrape.py`), spreads/totals scraped from Covers, land partitioned
Parquet in Cloudflare R2, and append to Basin Catalog Iceberg tables.

## Setup

```bash
source ../.venv/bin/activate
pip install -e ".[browser,iceberg,dev]"
playwright install chromium
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
python -m elt_ingest.legacy_backfill ~/sports_analytics/elt_pipeline/raw_data
```

## Layout

- `src/elt_ingest/scrape.py` — PFR/Covers scrapers (requests, Playwright fallback, retries)
- `src/elt_ingest/clean.py` — column mapping, date parsing, dedupe, content hash
- `src/elt_ingest/storage.py` — R2/local writers, manifests, `StateStore` watermarks
- `src/elt_ingest/iceberg.py` — Basin Catalog tables `nfl.raw_nfl_*`
- `src/elt_ingest/jobs.py`, `cli.py` — incremental/backfill jobs and entry point
- `global/`, `nfl/` — deprecated shims for the old script paths
- `tests/` — pytest

State note: spreads/totals jobs depend on games having run first (same as legacy).
