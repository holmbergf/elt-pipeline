# Basin Catalog

The R2 bucket (`../main.tf`) is the raw Parquet landing zone. Basin Catalog
adds managed Apache Iceberg tables on the same bucket, queried by dbt
(DuckDB Iceberg extension) or Basin SQL.

One-time setup:

```bash
# Catalog is provisioned by Terraform (cloudflare_r2_data_catalog.nfl).
# enable_catalog.sh remains only as a manual fallback for non-Terraform buckets:
# set BASIN_CATALOG_URI / BASIN_WAREHOUSE / BASIN_TOKEN in ../../.env
python -m elt_ingest.iceberg        # creates nfl.raw_nfl_games/spreads/totals
```

Ingestion appends to these tables automatically when `BASIN_CATALOG_URI` is
set (see `elt_ingest/jobs.py`); the raw Parquet objects remain the replayable
source of truth if a table ever needs rebuilding.
