"""Deprecated shim — MotherDuck/disk writer replaced by elt_ingest.storage.

PROJECT_ROOT now resolves to the repo root (the old 4x .parent overshot to
~/Documents after the move into data-integration/).
"""
from pathlib import Path

from elt_ingest.config import REPO_ROOT as PROJECT_ROOT  # noqa: F401
from elt_ingest.storage import get_storage, write_dataset  # noqa: F401


def get_timestamped_path(base_name: str = "raw_nfl_games") -> Path:
    from datetime import datetime

    return PROJECT_ROOT / "data" / "raw" / f"{base_name}_{datetime.now():%Y%m%d_%H%M%S}.parquet"


def write_to_disk(df, path=None, format: str = "parquet", **_kw) -> Path:
    """Compatibility wrapper: writes through the configured storage backend."""
    from elt_ingest.config import Settings

    dataset = "games" if "games" in str(path or "") else "spreads" if "spreads" in str(path or "") else "totals"
    settings = Settings.from_env()
    result = write_dataset(get_storage(settings), df, dataset, source="shim:write_to_disk")
    out = Path(path) if path else get_timestamped_path()
    print(f"write_to_disk shim -> {result.keys or result.skipped_keys}")
    return out
