import pandas as pd
import pytest

from elt_ingest.clean import normalise_games, parse_game_date
from elt_ingest.config import Settings
from elt_ingest.storage import LocalStorage, StateStore, write_dataset


def games_df():
    return pd.DataFrame(
        [
            {"week": "1", "day": "Thu", "date": "Thu Sep 5", "winner/tie": "A", "loser/tie": "B", "season": 2024},
            {"week": "1", "day": "Thu", "date": "Thu Sep 5", "winner/tie": "A", "loser/tie": "B", "season": 2024},
            {"week": "Week", "day": "", "date": "Week", "winner/tie": "", "loser/tie": "", "season": 2024},
            {"week": "18", "day": "Sun", "date": "Sun Jan 5", "winner/tie": "C", "loser/tie": "D", "season": 2024},
        ]
    )


def test_parse_game_date_playoff_year_rolls_forward():
    assert parse_game_date("Sun Jan 5", 2024).strftime("%Y-%m-%d") == "2025-01-05"
    assert pd.isna(parse_game_date("Playoffs", 2024))


def test_normalise_games_dedupes_and_iso_dates():
    df = normalise_games(games_df())
    assert len(df) == 2
    assert sorted(df["date"]) == ["2024-09-05", "2025-01-05"]


def test_write_is_partitioned_idempotent_and_stateful(tmp_path):
    storage = LocalStorage(tmp_path)
    df = normalise_games(games_df())
    r1 = write_dataset(storage, df, "games", source="test")
    r2 = write_dataset(storage, df, "games", source="test")
    assert r1.keys and all("/season=2024/" in k for k in r1.keys)
    assert r2.keys == [] and len(r2.skipped_keys) == len(r1.keys)  # no duplicates on re-run

    state = StateStore(storage)
    assert state.max_game_date() == "2025-01-05"
    assert state.game_dates() == ["2024-09-05", "2025-01-05"]
    assert state.missing_dates("spreads") == ["2025-01-05", "2024-09-05"]

    spreads = pd.DataFrame([{"matchup": "NFL A B", "event_date": "2024-09-05"}])
    write_dataset(storage, spreads, "spreads", source="test")
    assert state.missing_dates("spreads") == ["2025-01-05"]


def test_local_settings_backend(tmp_path, monkeypatch):
    monkeypatch.setenv("STORAGE_BACKEND", "local")
    monkeypatch.setenv("LOCAL_DATA_DIR", str(tmp_path))
    assert Settings.from_env().storage_backend == "local"
