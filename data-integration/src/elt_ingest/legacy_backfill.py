"""One-off: upload legacy elt_pipeline/raw_data/*.parquet into the new layout.

Files whose schema does not match their filename dataset (the legacy totals
backfill wrote games data into totals files) are quarantined, not loaded.
Run: python -m elt_ingest.legacy_backfill [legacy_raw_data_dir]
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

from .clean import MARKET_NATURAL_KEY, dedupe, normalise_games
from .config import Settings
from .storage import get_storage, write_dataset

_MARKET_COLS = {"matchup", "event_date"}


def dataset_of(path: Path) -> str | None:
    name = path.name
    for ds in ("games", "spreads", "totals"):
        if f"raw_nfl_{ds}_" in name:
            return ds
    return None


def load_legacy(raw_dir: Path, settings: Settings | None = None) -> dict:
    s = settings or Settings.from_env()
    storage = get_storage(s)
    report: dict[str, list] = {"loaded": [], "quarantined": [], "skipped_empty": []}
    frames: dict[str, list[pd.DataFrame]] = {"games": [], "spreads": [], "totals": []}
    for path in sorted(raw_dir.glob("*.parquet")):
        ds = dataset_of(path)
        if ds is None:
            continue
        df = pd.read_parquet(path)
        if ds == "games" and "winner" not in df.columns:
            report["quarantined"].append((path.name, "games file without winner column"))
            continue
        if ds in ("spreads", "totals") and not _MARKET_COLS.issubset(df.columns):
            report["quarantined"].append((path.name, f"{ds} file without matchup/event_date columns"))
            continue
        frames[ds].append(df)
    for ds, parts in frames.items():
        if not parts:
            continue
        df = pd.concat(parts, ignore_index=True)
        df = normalise_games(df) if ds == "games" else dedupe(df, MARKET_NATURAL_KEY)
        if df.empty:
            report["skipped_empty"].append(ds)
            continue
        r = write_dataset(storage, df, ds, source="legacy:elt_pipeline/raw_data")
        report["loaded"].append((ds, r.rows, len(r.keys)))
    return report


if __name__ == "__main__":
    legacy = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.home() / "sports_analytics/elt_pipeline/raw_data"
    print(load_legacy(legacy))
