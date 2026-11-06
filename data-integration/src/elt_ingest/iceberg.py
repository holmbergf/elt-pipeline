"""Basin Catalog (Iceberg REST) tables: nfl.raw_nfl_games / raw_nfl_spreads / raw_nfl_totals.

Requires `pip install -e ".[iceberg]"` and BASIN_CATALOG_URI / BASIN_WAREHOUSE /
BASIN_TOKEN in the environment. Enable the catalog first:
  Catalog is provisioned by Terraform: cloudflare_r2_data_catalog.nfl (see infra/)
"""

from __future__ import annotations

import logging

import pandas as pd
import pyarrow as pa

from .config import Settings

log = logging.getLogger(__name__)

NAMESPACE_TABLES = {
    "games": "raw_nfl_games",
    "spreads": "raw_nfl_spreads",
    "totals": "raw_nfl_totals",
}

_STR, _INT = pa.string(), pa.int64()
SCHEMAS: dict[str, pa.Schema] = {
    "games": pa.schema([
        ("week", _STR), ("day", _STR), ("date", _STR), ("time", _STR),
        ("winner", _STR), ("location", _STR), ("loser", _STR), ("boxscore", _STR),
        ("points_winner", _STR), ("points_loser", _STR),
        ("yards_winner", _STR), ("turnovers_winner", _STR),
        ("yards_loser", _STR), ("turnovers_loser", _STR),
        ("season", _INT), ("timestamp_imported", _STR),
    ]),
    "spreads": pa.schema([
        ("matchup", _STR), ("date", _STR), ("consensus", _STR), ("sides", _STR),
        ("picks", _STR), ("indepth", _STR), ("event_date", _STR), ("timestamp_imported", _STR),
    ]),
    "totals": pa.schema([
        ("matchup", _STR), ("date", _STR), ("consensus", _STR), ("total", _STR),
        ("picks", _STR), ("indepth", _STR), ("event_date", _STR), ("timestamp_imported", _STR),
    ]),
}


def connect(settings: Settings):
    if not (settings.basin_catalog_uri and settings.basin_warehouse and settings.basin_token):
        raise RuntimeError("Set BASIN_CATALOG_URI, BASIN_WAREHOUSE and BASIN_TOKEN (see .env.example).")
    from pyiceberg.catalog.rest import RestCatalog

    return RestCatalog(
        name="basin",
        warehouse=settings.basin_warehouse,
        uri=settings.basin_catalog_uri,
        token=settings.basin_token,
    )


CFB_TABLES = {"games": "raw_ncaaf_games", "spreads": "raw_ncaaf_spreads", "totals": "raw_ncaaf_totals"}
CFB_SCHEMAS: dict[str, pa.Schema] = {
    "games": pa.schema([
        ("date", _STR), ("time", _STR), ("season", _INT), ("week", _STR), ("day", _STR),
        ("home_team", _STR), ("away_team", _STR), ("home_score", _INT), ("away_score", _INT),
        ("home_rank", _INT), ("away_rank", _INT), ("is_ranked_home", pa.bool_()),
        ("is_ranked_away", pa.bool_()), ("is_top25_matchup", pa.bool_()),
        ("winner", _STR), ("loser", _STR), ("location", _STR),
        ("points_winner", _INT), ("points_loser", _INT), ("boxscore", _STR),
        ("timestamp_imported", _STR), ("espn_home_abbr", _STR), ("espn_away_abbr", _STR),
    ]),
    "spreads": SCHEMAS["spreads"],
    "totals": SCHEMAS["totals"],
}


def _tables_for(settings: Settings, dataset: str):
    return CFB_TABLES if settings.basin_namespace == "ncaaf" else NAMESPACE_TABLES


def _schemas_for(settings: Settings):
    return CFB_SCHEMAS if settings.basin_namespace == "ncaaf" else SCHEMAS


def ensure_tables(settings: Settings) -> list[str]:
    catalog = connect(settings)
    catalog.create_namespace_if_not_exists(settings.basin_namespace)
    created = []
    for dataset, table in _tables_for(settings, "").items():
        ident = (settings.basin_namespace, table)
        if not catalog.table_exists(ident):
            catalog.create_table(ident, schema=_schemas_for(settings)[dataset])
            created.append(table)
            log.info("created Iceberg table %s.%s", *ident)
    return created


def append_dataframe(settings: Settings, dataset: str, df) -> None:
    """Append a pandas frame to its Iceberg table (schema-aligned, extra cols dropped)."""
    import pyarrow as pa

    schema = _schemas_for(settings)[dataset]
    aligned = df.reindex(columns=schema.names).copy()
    for field in schema:
        if pa.types.is_string(field.type):
            aligned[field.name] = aligned[field.name].map(lambda v: None if pd.isna(v) else str(v))
    for int_col in ("season", "home_score", "away_score", "home_rank", "away_rank", "points_winner", "points_loser"):
        if int_col in schema.names:
            aligned = aligned.assign(**{int_col: aligned[int_col].astype("Int64")})
    table = pa.Table.from_pandas(aligned, schema=schema, preserve_index=False)
    catalog = connect(settings)
    catalog.load_table((settings.basin_namespace, _tables_for(settings, dataset)[dataset])).append(table)


if __name__ == "__main__":
    logging.basicConfig(level="INFO")
    created = ensure_tables(Settings.from_env())
    print(f"namespace ready; created={created or 'none (already existed)'}")
