"""Deprecated shim: elt-ingest games (incremental)."""
import asyncio
from elt_ingest import jobs

if __name__ == "__main__":
    print(asyncio.run(jobs.run_games(mode="incremental")))
