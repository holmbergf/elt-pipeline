# Mock raw fixtures (dbt CI)

Ten real rows per dataset, sampled from production raw (pre-transformation)
in R2 `ingestion/raw/nfl/`, stored in the same partitioned layout the
bronze `read_parquet` glob expects:

```
raw/ingestion/raw/nfl/games/season=<season>/part-fixture.parquet
raw/ingestion/raw/nfl/spreads/event_date=<date>/part-fixture.parquet
raw/ingestion/raw/nfl/totals/event_date=<date>/part-fixture.parquet
```

`ci/dbt` points `RAW_BASE_PATH` at `tests/fixtures/raw/ingestion` and runs
`dbt build` (models + data tests) fully offline. Regenerate by sampling
`elt_ingest.storage` reads of production raw and writing 10 rows per dataset.
