"""Regression tests for the sport-aware warehouse loader.

Uses the local-mirror layout (LOCAL_WAREHOUSE_DIR) so no R2 credentials are
needed: <dir>/data_warehouse/... for NFL, <dir>/ncaaf/data_warehouse/... for
NCAAF. Guards the NCAAF-section change that broke the deployed Upcoming page:
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

    data.clear_caches()
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
    mirror.clear_caches()
    df = mirror.load("form", "ncaaf")
    assert df["team_name"].tolist() == ["Y"]


def test_load_busts_cache_when_warehouse_version_changes(mirror, tmp_path):
    # A publish rewrites the semantic tables; the version stamp (row counts)
    # must key the hour-long cache so pre-publish records never linger.
    base = tmp_path / "data_warehouse" / "semantic"
    pd.DataFrame({"x": [1]}).to_parquet(base / "semantic_game_results.parquet", index=False)
    mirror.clear_caches()
    assert len(mirror.load("form")) == 1
    form = pd.read_parquet(base / "semantic_team_season_form.parquet")
    pd.concat([form, form.assign(team_name="Z")]).to_parquet(
        base / "semantic_team_season_form.parquet", index=False)
    mirror._warehouse_version.clear()  # simulate the 60s probe expiring
    assert len(mirror.load("form")) == 2


def test_load_busts_cache_when_only_lines_land(mirror, tmp_path):
    # A lines-only publish (spreads arrive for an already-listed fixture)
    # changes neither form nor results row counts; the stamp must still
    # move via upcoming line coverage or the board serves "no consensus"
    # for up to an hour after the lines published.
    base = tmp_path / "data_warehouse"
    pd.DataFrame({"x": [1]}).to_parquet(base / "semantic" / "semantic_game_results.parquet", index=False)
    (base / "silver").mkdir(parents=True, exist_ok=True)
    up = base / "silver" / "fct_nfl_betting_upcoming.parquet"
    pd.DataFrame({"game_date": ["2026-11-25"], "home_spread": [float("nan")],
                  "over_under_line": [float("nan")]}).to_parquet(up, index=False)
    mirror.clear_caches()
    assert mirror.load("upcoming_all")["home_spread"].isna().all()
    pd.DataFrame({"game_date": ["2026-11-25"], "home_spread": [-2.5], "over_under_line": [47.5]}).to_parquet(up, index=False)
    mirror._warehouse_version.clear()  # simulate the 60s probe expiring
    refreshed = mirror.load("upcoming_all")
    assert refreshed.iloc[0]["home_spread"] == -2.5


def test_load_failure_surfaces_sanitized_error(mirror, monkeypatch):
    monkeypatch.setenv("LOCAL_WAREHOUSE_DIR", "/nonexistent-dir")
    mirror.clear_caches()
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


def test_all_season_pickers_use_all_seasons_label():
    # Every season control on the board (Upcoming/Historical, Team Form,
    # Trends, Consensus) must route through season_option_label so a
    # season 0 can only ever render as "All seasons".
    src = open(os.path.join(os.path.dirname(__file__), "..", "streamlit_app.py")).read()
    season_controls = [ln for ln in src.splitlines()
                       if ("segmented_control(\"Season" in ln or "selectbox(\"Season\"" in ln)]
    assert len(season_controls) == 4
    assert all("format_func=season_option_label" in ln for ln in season_controls)
    assert "(0 = all seasons)" not in src


def test_season_option_label():
    import data

    assert data.season_option_label(0) == "All seasons"
    assert data.season_option_label(2026) == "2026"


def test_load_upcoming_joins_form(mirror, tmp_path):
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
    mirror.clear_caches()
    df = mirror.load_upcoming("nfl")
    assert df.iloc[0]["home_record_display"] == "7-1-0"
    assert df.iloc[0]["away_win_pct"] == 0.88
    assert "home_spread_points" in df.columns and "totals_line_points" in df.columns


def test_load_history_merges_scores_and_market(mirror, tmp_path):
    base = tmp_path / "data_warehouse"
    pd.DataFrame([{
        "game_date": "2026-10-03", "season": 2026, "week": "6",
        "home_team": "X", "away_team": "X", "home_score": 31, "away_score": 17,
        "winner": "X", "totals_result": "Over", "spread_cover_side": "Home",
    }]).to_parquet(base / "semantic" / "semantic_game_results.parquet", index=False)
    (base / "silver").mkdir(parents=True, exist_ok=True)
    pd.DataFrame([{
        "game_date": "2026-10-03", "season": 2026, "home_team": "X", "away_team": "X",
        "home_spread": -3.5, "away_spread": 3.5, "spread_line": 3.5,
        "spread_home_consensus_pct": 0.6, "spread_away_consensus_pct": 0.4,
        "market_favorite_team": "X", "over_under_line": 55.5,
        "over_consensus_pct": 0.5, "under_consensus_pct": 0.5,
    }]).to_parquet(base / "silver" / "fct_nfl_betting_settled.parquet", index=False)
    mirror.clear_caches()
    df = mirror.load_history("nfl")
    assert df.iloc[0]["home_score"] == 31
    assert df.iloc[0]["home_consensus_pct"] == 0.6


def test_game_axis_uses_integer_ticks():
    # Exec only the axis helper from the app (importing the app runs Streamlit).
    src = open(os.path.join(os.path.dirname(__file__), "..", "streamlit_app.py")).read()
    ns: dict = {}
    exec("import altair as alt\n" + src[src.index("def game_x") : src.index("def cpct")], ns)
    axis = ns["game_x"]().to_dict()
    assert axis["type"] == "ordinal" and axis["field"] == "game"


def test_queries_use_per_call_cursors():
    # The cached DuckDB connection is shared across sessions/reruns; a
    # second query while one is in flight raises ResourceInUseException
    # ("connection is busy ... use a separate connection from cursor()").
    src = open(os.path.join(os.path.dirname(__file__), "..", "data.py")).read()
    assert "_con().execute" not in src
    assert src.count("_con().cursor().execute") >= 3


def test_require_password_optional_for_public_board():
    # Exec only require_password (importing the app runs Streamlit). With no
    # app_password secret the board is public read-only; with one set, an
    # already-authenticated session passes the gate.
    src = open(os.path.join(os.path.dirname(__file__), "..", "streamlit_app.py")).read()

    class FakeSt:
        def __init__(self, secrets, session):
            self.secrets, self.session_state, self.errors = secrets, session, []

        def error(self, msg):
            self.errors.append(msg)

    def gate(secrets, session):
        ns = {"st": FakeSt(secrets, session)}
        exec(src[src.index("def require_password") : src.index("def pct")], ns)
        return ns["require_password"](), ns["st"].errors

    ok, errors = gate({}, {})
    assert ok is True and errors == []
    ok, _ = gate({"app_password": "pw"}, {"authed": True})
    assert ok is True


def test_pair_colors_distinguishes_similar_blues():
    # Exec only the pure color helpers from the app (importing the app runs Streamlit).
    src = open(os.path.join(os.path.dirname(__file__), "..", "streamlit_app.py")).read()
    ns: dict = {}
    exec(src[src.index("TEAM_COLORS = {") : src.index("def compare_row")], ns)
    ca, ch = ns["pair_colors"]("Cowboys", "Colts")

    def rgb(h):
        h = h.lstrip("#")
        return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))

    dist = sum((a - b) ** 2 for a, b in zip(rgb(ca), rgb(ch))) ** 0.5
    assert dist >= 85
