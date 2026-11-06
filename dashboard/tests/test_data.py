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
        pd.DataFrame({"team_name": ["X"], "season": [2026]}).to_parquet(
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
