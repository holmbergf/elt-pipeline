"""Regression: NFL games append crashed in CI with
ArrowInvalid: Failed to parse string: '35.0' as int64.

nflverse scores arrive as floats when unplayed games (null scores) are in
the batch; the NFL raw schema keeps points_winner/points_loser as strings,
but the aligner force-cast every column NAMED like an int column to Int64.
Alignment must be driven by the schema field types, not column names.
"""

import pandas as pd
import pyarrow as pa

from elt_ingest.iceberg import SCHEMAS, CFB_SCHEMAS, align_to_schema


def test_nfl_games_float_scores_stay_strings():
    df = pd.DataFrame([{
        "week": "11", "day": "Sun", "date": "2026-11-15", "time": "1:00PM",
        "winner": "A", "location": "", "loser": "B", "boxscore": "x",
        "points_winner": 35.0, "points_loser": 24.0,  # floats (NaN elsewhere in batch)
        "yards_winner": None, "turnovers_winner": None,
        "yards_loser": None, "turnovers_loser": None,
        "season": 2026, "timestamp_imported": "2026-11-15 00:00:00 UTC",
    }])
    table = align_to_schema(df, SCHEMAS["games"])
    assert table.column("points_winner").to_pylist() == ["35.0"]
    assert table.column("season").type == pa.int64()
    assert table.column("season").to_pylist() == [2026]


def test_cfb_games_scores_become_ints():
    df = pd.DataFrame([{
        "date": "2026-11-07", "season": 2026.0, "home_score": 31.0, "away_score": None,
        "home_rank": 5.0, "away_rank": None, "points_winner": 31.0, "points_loser": None,
    }])
    table = align_to_schema(df, CFB_SCHEMAS["games"])
    assert table.column("home_score").to_pylist() == [31]
    assert table.column("away_score").to_pylist() == [None]
    assert table.column("home_rank").to_pylist() == [5]
