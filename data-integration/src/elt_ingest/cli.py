"""CLI: elt-ingest {games,spreads,totals,all} [--mode incremental|backfill] ..."""

from __future__ import annotations

import argparse
import asyncio
import logging

from . import jobs
from .config import Settings


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="elt-ingest")
    p.add_argument("dataset", choices=["games", "spreads", "totals", "all"])
    p.add_argument("--mode", choices=["incremental", "backfill"], default="incremental")
    p.add_argument("--start-year", type=int, default=2015)
    p.add_argument("--season", type=int, default=None, help="backfill only: restrict market jobs to one season (Sep-Feb window)")
    p.add_argument("--log-level", default="INFO")
    args = p.parse_args(argv)
    logging.basicConfig(level=args.log_level, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    settings = Settings.from_env()
    print(f"storage_backend={settings.storage_backend} bucket={settings.r2_bucket}")

    async def _run():
        results = []
        if args.dataset in ("games", "all"):
            results.append(await jobs.run_games(settings, mode=args.mode, start_year=args.start_year))
        if args.dataset in ("spreads", "all"):
            results.append(await jobs.run_spreads(settings, mode=args.mode, season=args.season))
        if args.dataset in ("totals", "all"):
            results.append(await jobs.run_totals(settings, mode=args.mode, season=args.season))
        return results

    for r in asyncio.run(_run()):
        print(f"{r.dataset}: rows={r.rows} new_objects={len(r.keys)} skipped={len(r.skipped_keys)} max_date={r.max_date}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
