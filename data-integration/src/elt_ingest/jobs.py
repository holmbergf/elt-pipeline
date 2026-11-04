"""Ingestion jobs. Each returns a WriteResult; all state comes from manifests."""

from __future__ import annotations

import logging
from datetime import datetime

import pandas as pd

from .clean import MARKET_NATURAL_KEY, dedupe, normalise_games
from .config import Settings
from .scrape import scrape_nfl_games, scrape_nfl_games_covers, scrape_nfl_over_unders, scrape_nfl_spreads
from .storage import StateStore, WriteResult, get_storage, write_dataset

log = logging.getLogger(__name__)


def _settings_and_storage(settings: Settings | None):
    s = settings or Settings.from_env()
    return s, get_storage(s)


def _maybe_iceberg(settings: Settings, dataset: str, df: pd.DataFrame, result: WriteResult) -> None:
    if result.keys and settings.basin_catalog_uri:
        from .iceberg import append_dataframe

        append_dataframe(settings, dataset, df)



def _scrape_games(years):
    """Games source: nflverse by default (one CSV, no scraping). GAMES_SOURCE=covers|pfr selects the scrapers."""
    import asyncio
    import os

    source = os.getenv("GAMES_SOURCE", "nflverse").lower()
    if source == "pfr":
        return scrape_nfl_games(seasons=years)
    if source == "covers":
        return scrape_nfl_games_covers(seasons=years)
    from .nflverse import fetch_nflverse_games

    return asyncio.to_thread(fetch_nflverse_games, years)

async def run_games(
    settings: Settings | None = None,
    mode: str = "incremental",
    start_year: int = 2015,
    seasons: list[int] | None = None,
) -> WriteResult:
    s, storage = _settings_and_storage(settings)
    state = StateStore(storage)
    if mode == "backfill":
        years = seasons or list(range(start_year, datetime.now().year + 1))
        df = normalise_games(await _scrape_games(years))
        result = write_dataset(storage, df, "games", source="backfill:nflverse")
    else:
        max_date = state.max_game_date()
        current_season = datetime.now().year if datetime.now().month >= 9 else datetime.now().year - 1
        years = seasons or ([current_season] if max_date is None else sorted({current_season - 1, current_season}))
        df = normalise_games(await _scrape_games(years))
        if max_date is not None:
            df = df[df["date"] > max_date].reset_index(drop=True)
        result = write_dataset(storage, df, "games", source="incremental:nflverse")
    _maybe_iceberg(s, "games", df, result)
    return result


async def _run_market(dataset: str, scrape_fn, settings, mode: str, batch_size: int = 50) -> WriteResult:
    s, storage = _settings_and_storage(settings)
    state = StateStore(storage)
    if mode == "backfill":
        dates = sorted(state.game_dates(), reverse=True)
    else:
        dates = state.missing_dates(dataset, since_days=14)
    if not dates:
        log.info("no %s dates to fetch (run games first?)", dataset)
        return WriteResult(dataset=dataset)
    combined = WriteResult(dataset=dataset)
    for i in range(0, len(dates), batch_size):
        batch = dates[i : i + batch_size]
        df = await scrape_fn(batch)
        if df.empty:
            continue
        df = dedupe(df, MARKET_NATURAL_KEY)
        r = write_dataset(storage, df, dataset, source=f"{mode}:covers")
        combined.keys += r.keys
        combined.skipped_keys += r.skipped_keys
        combined.rows += r.rows
        combined.covered_dates = sorted(set(combined.covered_dates) | set(r.covered_dates))
        _maybe_iceberg(s, dataset, df, r)
    return combined


async def run_spreads(settings=None, mode: str = "incremental") -> WriteResult:
    return await _run_market("spreads", scrape_nfl_spreads, settings, mode)


async def run_totals(settings=None, mode: str = "incremental") -> WriteResult:
    return await _run_market("totals", scrape_nfl_over_unders, settings, mode)
