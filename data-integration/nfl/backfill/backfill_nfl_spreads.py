"""Deprecated shim: elt-ingest spreads --mode backfill."""
import asyncio
from elt_ingest import jobs

if __name__ == "__main__":
    print(asyncio.run(jobs.run_spreads(mode="backfill")))
