"""One-off migration: nfl-ingestion bucket -> nfl bucket under ingestion/.

Copies raw Parquet + run manifests (never __r2_data_catalog, which the new
bucket's catalog manages itself), then recreates the raw Iceberg tables in
the new catalog and reloads them from the copied Parquet.

Run (after `terraform apply` for bucket `nfl` + its catalog):
  OLD_BUCKET=nfl-ingestion NEW_BUCKET=nfl python -m elt_ingest.migrate_bucket
Idempotent: objects are content-addressed, tables reload only when empty.
"""

from __future__ import annotations

import io
import logging
import os

import pandas as pd

from .clean import MARKET_NATURAL_KEY, dedupe
from .config import Settings
from .storage import R2Storage

log = logging.getLogger(__name__)


def _storage(bucket: str, settings: Settings) -> R2Storage:
    from dataclasses import replace

    return R2Storage(replace(settings, r2_bucket=bucket))


def copy_objects(old: R2Storage, new: R2Storage) -> dict[str, int]:
    counts: dict[str, int] = {}
    for src_prefix, dst_prefix in (("raw/", "ingestion/raw/"), ("_manifests/", "ingestion/_manifests/")):
        n = 0
        for key in old.list_keys(src_prefix):
            dst = dst_prefix + key[len(src_prefix):]
            if not new.exists(dst):
                new.put_bytes(dst, old.get_bytes(key))
                n += 1
        counts[src_prefix] = n
        log.info("copied %d objects %s -> %s", n, src_prefix, dst_prefix)
    return counts


def reload_iceberg(new: R2Storage, settings: Settings) -> dict[str, int]:
    from .iceberg import NAMESPACE_TABLES, append_dataframe, connect, ensure_tables

    ensure_tables(settings)
    catalog = connect(settings)
    counts = {}
    for dataset, table in NAMESPACE_TABLES.items():
        ident = (settings.basin_namespace, table)
        existing = catalog.load_table(ident).scan().to_arrow().num_rows
        if existing:
            counts[dataset] = existing
            continue
        frames = [
            pd.read_parquet(io.BytesIO(new.get_bytes(k)))
            for k in new.list_keys(f"ingestion/raw/nfl/{dataset}/")
            if k.endswith(".parquet")
        ]
        df = pd.concat(frames, ignore_index=True)
        df = dedupe(df, ["season", "date", "winner", "loser"] if dataset == "games" else MARKET_NATURAL_KEY)
        append_dataframe(settings, dataset, df)
        counts[dataset] = catalog.load_table(ident).scan().to_arrow().num_rows
    return counts


if __name__ == "__main__":
    logging.basicConfig(level="INFO")
    base = Settings.from_env()
    old = _storage(os.getenv("OLD_BUCKET", "nfl-ingestion"), base)
    new_settings = Settings.from_env()  # R2_BUCKET / BASIN_* must point at the new bucket
    new = _storage(os.getenv("NEW_BUCKET", "nfl"), new_settings)
    print("copied:", copy_objects(old, new))
    print("iceberg rows:", reload_iceberg(new, new_settings))
