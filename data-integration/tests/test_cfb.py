import pandas as pd

from elt_ingest.cfb import parse_espn_events
from elt_ingest.jobs_cfb import _cfb_settings
from elt_ingest.config import Settings


def _event(home_rank=99, away_rank=5, completed=True, hs="31", aws="17"):
    def comp(side, name, abbr, rank, score):
        return {
            "homeAway": side,
            "score": score,
            "curatedRank": {"current": rank},
            "team": {"displayName": name, "abbreviation": abbr},
        }

    return {
        "id": "401",
        "date": "2026-09-05T19:00Z",
        "week": {"number": 2},
        "status": {"type": {"completed": completed}},
        "competitions": [
            {
                "competitors": [
                    comp("home", "Home U", "HMU", home_rank, hs),
                    comp("away", "Away State", "AWS", away_rank, aws),
                ]
            }
        ],
    }


def test_parse_ranks_and_scores():
    rows = parse_espn_events({"events": [_event()]}, 2026)
    assert len(rows) == 1
    r = rows[0]
    assert r["home_rank"] is None  # 99 = unranked
    assert r["away_rank"] == 5
    assert r["is_ranked_away"] and not r["is_ranked_home"]
    assert not r["is_top25_matchup"]
    assert r["home_score"] == 31 and r["winner"] == "Home U"


def test_parse_unplayed_has_no_scores():
    rows = parse_espn_events({"events": [_event(completed=False)]}, 2026)
    assert rows[0]["home_score"] is None and rows[0]["points_winner"] is None


def test_cfb_settings_point_at_ncaaf_catalog():
    s = Settings(
        basin_catalog_uri="https://catalog.example/acct/nfl",
        basin_warehouse="acct_nfl",
        basin_namespace="nfl",
    )
    c = _cfb_settings(s)
    assert c.basin_namespace == "ncaaf"
    assert c.basin_catalog_uri.endswith("/ncaaf")
    assert c.basin_warehouse == "acct_ncaaf"


def test_evening_kickoff_uses_eastern_date():
    ev = _event()
    ev["date"] = "2026-11-08T00:30Z"  # Sat 7:30pm ET kickoff
    rows = parse_espn_events({"events": [ev]}, 2026)
    assert rows[0]["date"] == "2026-11-07"
    assert rows[0]["day"] == "Sat"
