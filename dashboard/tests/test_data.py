"""Regression tests for the sport-aware warehouse loader.

Uses the local-mirror layout (LOCAL_WAREHOUSE_DIR) so no R2 credentials are
needed: <dir>/data_warehouse/... for NFL, <dir>/ncaaf/data_warehouse/... for
NCAAF. Guards the NCAAF-section change that broke the deployed Today page:
load(table, sport) must resolve each sport to its own location.
"""

import os
import sys

import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


@pytest.fixture()
def mirror(tmp_path, monkeypatch):
    import data

    data.load.clear()
    for sub in ("", "ncaaf/"):
        d = tmp_path / sub / "data_warehouse" / "semantic"
        d.mkdir(parents=True)
        pd.DataFrame({"team_name": ["X"], "season": [2026], "wins": [7], "losses": [1],
            "record_display": ["7-1-0"], "win_pct": [0.88], "season_rank": [1],
            "against_the_spread_win_pct": [0.5], "over_pct": [0.5], "avg_points_scored": [30.0],
            "consensus_spread_accuracy": [0.5], "consensus_total_accuracy": [0.5]}).to_parquet(
            d / "semantic_team_season_form.parquet", index=False
        )
    monkeypatch.setenv("LOCAL_WAREHOUSE_DIR", str(tmp_path))
    return data


def test_load_defaults_to_nfl_and_reads_mirror(mirror):
    df = mirror.load("form")
    assert df["team_name"].tolist() == ["X"]


def test_load_ncaaf_reads_ncaaf_subdir(mirror, tmp_path):
    # Distinct content under the ncaaf mirror proves the sport path is used.
    p = tmp_path / "ncaaf" / "data_warehouse" / "semantic" / "semantic_team_season_form.parquet"
    pd.DataFrame({"team_name": ["Y"], "season": [2026]}).to_parquet(p, index=False)
    mirror.load.clear()
    df = mirror.load("form", "ncaaf")
    assert df["team_name"].tolist() == ["Y"]


def test_load_failure_surfaces_sanitized_error(mirror, monkeypatch):
    monkeypatch.setenv("LOCAL_WAREHOUSE_DIR", "/nonexistent-dir")
    mirror.load.clear()
    with pytest.raises(RuntimeError, match="Failed to load form"):
        mirror.load("form", "ncaaf")


def test_games_for_day_never_shows_past_games():
    import data

    df = pd.DataFrame({"game_date": pd.to_datetime(["2026-11-05", "2026-11-07"]).date})
    out, shown, is_today = data.games_for_day(df, pd.Timestamp("2026-11-06").date())
    assert not is_today and str(shown) == "2026-11-07" and len(out) == 1


def test_games_for_day_today_and_empty():
    import data

    df = pd.DataFrame({"game_date": pd.to_datetime(["2026-11-06"]).date})
    out, shown, is_today = data.games_for_day(df, pd.Timestamp("2026-11-06").date())
    assert is_today and len(out) == 1
    past = pd.DataFrame({"game_date": pd.to_datetime(["2026-11-05"]).date})
    out, _, _ = data.games_for_day(past, pd.Timestamp("2026-11-06").date())
    assert out.empty


def test_load_today_joins_form(mirror, tmp_path):
    base = tmp_path / "data_warehouse"
    (base / "silver").mkdir(parents=True, exist_ok=True)
    pd.DataFrame([{
        "game_date": "2026-11-07", "season": 2026, "week": "11",
        "home_team": "X", "away_team": "X",
        "home_spread": -3.5, "away_spread": 3.5, "spread_line": 3.5,
        "spread_home_consensus_pct": 0.6, "spread_away_consensus_pct": 0.4,
        "market_favorite_team": "X", "over_under_line": 55.5,
        "over_consensus_pct": 0.5, "under_consensus_pct": 0.5,
    }]).to_parquet(base / "silver" / "fct_nfl_betting_upcoming.parquet", index=False)
    mirror.load_today.clear()
    df = mirror.load_today("nfl")
    assert df.iloc[0]["home_record_display"] == "7-1-0"
    assert df.iloc[0]["away_win_pct"] == 0.88
    assert "home_spread_points" in df.columns and "totals_line_points" in df.columns
