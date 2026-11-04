"""Deprecated shim: elt-ingest spreads (incremental)."""
import asyncio
from elt_ingest import jobs

if __name__ == "__main__":
    print(asyncio.run(jobs.run_spreads(mode="incremental")))
