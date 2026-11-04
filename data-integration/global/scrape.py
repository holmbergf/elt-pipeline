"""Deprecated shim — use elt_ingest.scrape. Kept so old imports keep working."""
from elt_ingest.scrape import *  # noqa: F401,F403
from elt_ingest.scrape import scrape_nfl_games, scrape_nfl_over_unders, scrape_nfl_spreads  # noqa: F401
