"""Publish dbt silver/gold models to Basin Catalog Iceberg + data_warehouse/ Parquet.

Write-path decision (warehouse plan Step 3 spike, 2026-11-04):
- DuckDB can ATTACH to Basin Catalog and INSERT, but CREATE OR REPLACE TABLE
  (dbt's table materialization) is not supported by DuckDB-Iceberg.
- Basin Catalog rejects custom table locations outside its storage profile
  (s3://<bucket>/__r2_data_catalog), so silver/gold tables cannot physically
  live under data_warehouse/ as Iceberg tables.
Chosen path: dbt builds silver/gold in DuckDB; this publisher overwrites the
catalog tables (namespaces silver/gold, partitioned by season where present)
and also exports each model as Parquet under data_warehouse/{layer}/ in R2 —
the user-visible warehouse zone. Run after `dbt build`:
  python -m elt_ingest.publish_warehouse [path/to/warehouse.duckdb]
"""

from __future__ import annotations

import io
import logging
import sys
from pathlib import Path

import duckdb
import pandas as pd
import pyarrow as pa

from .config import Settings
from .storage import get_storage

log = logging.getLogger(__name__)

# dbt model name -> (namespace/layer, Iceberg table name)
MODELS: dict[str, tuple[str, str]] = {
    "clean_nfl_games": ("silver", "clean_nfl_games"),
    "clean_nfl_spreads": ("silver", "clean_nfl_spreads"),
    "clean_nfl_totals": ("silver", "clean_nfl_totals"),
    "dim_nfl_date": ("silver", "dim_nfl_date"),
    "dim_nfl_teams": ("silver", "dim_nfl_teams"),
    "fct_nfl_games": ("silver", "fct_nfl_games"),
    "fct_nfl_betting_settled": ("silver", "fct_nfl_betting_settled"),
    "fct_nfl_betting_upcoming": ("silver", "fct_nfl_betting_upcoming"),
    "fct_nfl_team_performance": ("silver", "fct_nfl_team_performance"),
    "fct_nfl_team_market_games": ("silver", "fct_nfl_team_market_games"),
    "analytics_nfl_team_betting_stats": ("gold", "analytics_nfl_team_betting_stats"),
    "analytics_nfl_team_rankings": ("gold", "analytics_nfl_team_rankings"),
    "analytics_nfl_upcoming_matchups": ("gold", "analytics_nfl_upcoming_matchups"),
    "semantic_team_season_form": ("semantic", "semantic_team_season_form"),
    "semantic_game_results": ("semantic", "semantic_game_results"),
    "semantic_upcoming_matchups": ("semantic", "semantic_upcoming_matchups"),
    "semantic_consensus_spread_bands": ("semantic", "semantic_consensus_spread_bands"),
    "semantic_consensus_total_bands": ("semantic", "semantic_consensus_total_bands"),
}


def publish(db_path: Path, settings: Settings | None = None) -> dict[str, int]:
    from .iceberg import connect

    s = settings or Settings.from_env()
    storage = get_storage(s)
    catalog = connect(s)
    con = duckdb.connect(str(db_path), read_only=True)
    counts: dict[str, int] = {}
    for model, (layer, table_name) in MODELS.items():
        df = con.execute(f'SELECT * FROM main."{model}"').fetchdf()
        # DuckDB/pyarrow type hygiene: timestamps -> string-safe, ints stay ints.
        arrow = pa.Table.from_pandas(df, preserve_index=False)
        ident = (layer, table_name)
        catalog.create_namespace_if_not_exists(layer)
        if catalog.table_exists(ident):
            existing = {f.name: str(f.field_type) for f in catalog.load_table(ident).schema().fields}
            new = {n: str(arrow.field(n).type) for n in arrow.column_names}
            if existing != new:
                # Publisher is a full overwrite; recreate on schema change.
                catalog.drop_table(ident)
        if not catalog.table_exists(ident):
            # Unpartitioned at this scale (~10k rows); Basin Catalog maintenance
            # (compaction) is enabled at the catalog level. Revisit if a fact
            # table passes ~1M rows.
            catalog.create_table(ident, schema=arrow.schema)
        table = catalog.load_table(ident)
        table.overwrite(arrow)
        counts[model] = table.scan().to_arrow().num_rows
        # Parquet export into the data_warehouse/ zone (same content, file form).
        buf = io.BytesIO()
        df.to_parquet(buf, index=False)
        storage.put_bytes(f"data_warehouse/{layer}/{table_name}.parquet", buf.getvalue())
        log.info("published %s.%s: %d rows", layer, table_name, counts[model])
    con.close()
    return counts


if __name__ == "__main__":
    logging.basicConfig(level="INFO")
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("dbt-transform/dev.duckdb")
    print(publish(path))
