"""NCAAF jobs: ESPN games (with ranks) + Covers markets, mirroring NFL jobs."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime

import pandas as pd

from .cfb import fetch_cfb_games
from .clean import MARKET_NATURAL_KEY, dedupe
from .config import Settings
from .scrape import scrape_ncaaf_over_unders, scrape_ncaaf_spreads
from .storage import StateStore, WriteResult, get_storage, write_dataset

log = logging.getLogger(__name__)


def _storage(settings: Settings | None):
    s = settings or Settings.from_env()
    return s, get_storage(s, sport="ncaaf", bucket=s.ncaaf_bucket)


def _maybe_iceberg(settings: Settings, dataset: str, df: pd.DataFrame, result: WriteResult) -> None:
    if result.keys and settings.basin_catalog_uri:
        from .iceberg import append_dataframe

        append_dataframe(settings, dataset, df)


def _cfb_settings(settings: Settings) -> Settings:
    """Catalog env for the ncaaf bucket (env suffix NCAAF_*, fallback to NFL's)."""
    import os
    from dataclasses import replace

    uri = os.getenv("NCAAF_BASIN_CATALOG_URI") or (
        settings.basin_catalog_uri.replace("/nfl", "/ncaaf") if settings.basin_catalog_uri else "")
    wh = os.getenv("NCAAF_BASIN_WAREHOUSE") or (
        settings.basin_warehouse.replace("_nfl", "_ncaaf") if settings.basin_warehouse else "")
    return replace(settings, basin_catalog_uri=uri, basin_warehouse=wh, basin_namespace="ncaaf")


async def run_cfb_games(settings=None, mode: str = "incremental", start_year: int = 2015,
                        seasons: list[int] | None = None) -> WriteResult:
    s, storage = _storage(settings)
    if mode == "backfill":
        years = seasons or list(range(start_year, datetime.now().year + 1))
    else:
        current = datetime.now().year if datetime.now().month >= 8 else datetime.now().year - 1
        years = seasons or sorted({current - 1, current})
    df = await asyncio.to_thread(fetch_cfb_games, years)
    result = write_dataset(storage, df, "games", source=f"{mode}:espn")
    _maybe_iceberg(_cfb_settings(s), "games", df, result)
    return result


async def _run_market(dataset: str, scrape_fn, settings, mode: str, batch_size: int = 40) -> WriteResult:
    s, storage = _storage(settings)
    state = StateStore(storage)
    if mode == "backfill":
        dates = state.missing_dates(dataset)
    else:
        dates = state.missing_dates(dataset, since_days=21)
    if not dates:
        log.info("no ncaaf %s dates to fetch (run games first?)", dataset)
        return WriteResult(dataset=dataset)
    combined = WriteResult(dataset=dataset)
    for i in range(0, len(dates), batch_size):
        batch = dates[i : i + batch_size]
        df = await scrape_fn(batch)
        if df.empty:
            continue
        df = dedupe(df, MARKET_NATURAL_KEY)
        r = write_dataset(storage, df, dataset, source=f"{mode}:covers-ncaaf")
        combined.keys += r.keys
        combined.skipped_keys += r.skipped_keys
        combined.rows += r.rows
        _maybe_iceberg(_cfb_settings(s), dataset, df, r)
    return combined


async def run_cfb_spreads(settings=None, mode: str = "incremental") -> WriteResult:
    return await _run_market("spreads", scrape_ncaaf_spreads, settings, mode)


async def run_cfb_totals(settings=None, mode: str = "incremental") -> WriteResult:
    return await _run_market("totals", scrape_ncaaf_over_unders, settings, mode)
