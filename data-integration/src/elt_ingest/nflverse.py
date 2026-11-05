"""NFL games from nflverse (Lee Sharpe's schedule dataset).

One CSV (~2 MB, 1999-present, refreshed in-season) from the nflverse/nfldata
repo; no scraping. Output uses the canonical games columns
so clean.normalise_games and the dbt bronze model keep working unchanged.
Yards/turnovers are not in this dataset and stay null (bronze-only columns).
Team abbreviations are normalised to full team names (seed mapping in dbt).
"""

from __future__ import annotations

import logging
from io import StringIO

import pandas as pd
import requests

log = logging.getLogger(__name__)

NFLVERSE_GAMES_URL = "https://raw.githubusercontent.com/nflverse/nfldata/master/data/games.csv"

# nflverse abbreviation -> full team name (must match seeds/nfl_team_mappings.csv full_team_name).
# Historical relocations collapse to the name present in the seed for that code.
TEAM_NAMES = {
    "ARI": "Arizona Cardinals", "ATL": "Atlanta Falcons", "BAL": "Baltimore Ravens",
    "BUF": "Buffalo Bills", "CAR": "Carolina Panthers", "CHI": "Chicago Bears",
    "CIN": "Cincinnati Bengals", "CLE": "Cleveland Browns", "DAL": "Dallas Cowboys",
    "DEN": "Denver Broncos", "DET": "Detroit Lions", "GB": "Green Bay Packers",
    "HOU": "Houston Texans", "IND": "Indianapolis Colts", "JAC": "Jacksonville Jaguars",
    "JAX": "Jacksonville Jaguars", "KC": "Kansas City Chiefs",
    "LA": "Los Angeles Rams", "LAR": "Los Angeles Rams", "STL": "St. Louis Rams",
    "LAC": "Los Angeles Chargers", "SD": "San Diego Chargers",
    "LV": "Las Vegas Raiders", "OAK": "Oakland Raiders",
    "MIA": "Miami Dolphins", "MIN": "Minnesota Vikings", "NE": "New England Patriots",
    "NO": "New Orleans Saints", "NYG": "New York Giants", "NYJ": "New York Jets",
    "PHI": "Philadelphia Eagles", "PIT": "Pittsburgh Steelers", "SEA": "Seattle Seahawks",
    "SF": "San Francisco 49ers", "TB": "Tampa Bay Buccaneers", "TEN": "Tennessee Titans",
    "WAS": "Washington Commanders",
}


def parse_nflverse_games(csv_text: str, seasons: list[int], timestamp: str) -> pd.DataFrame:
    raw = pd.read_csv(StringIO(csv_text))
    raw = raw[raw["season"].isin(seasons)]
    rows = []
    for r in raw.itertuples():
        away, home = TEAM_NAMES.get(r.away_team, r.away_team), TEAM_NAMES.get(r.home_team, r.home_team)
        has_score = pd.notna(r.away_score) and pd.notna(r.home_score)
        away_pts = int(r.away_score) if has_score else None
        home_pts = int(r.home_score) if has_score else None
        winner_is_home = has_score and home_pts >= away_pts
        rows.append({
            "week": str(int(r.week)),
            "day": str(r.weekday)[:3],
            "date": str(r.gameday),
            "time": str(r.gametime) if pd.notna(r.gametime) else "",
            "winner": home if winner_is_home else away,
            "location": "" if winner_is_home else "@",
            "loser": away if winner_is_home else home,
            "boxscore": str(r.pfr) if pd.notna(getattr(r, "pfr", None)) else str(r.game_id),
            "points_winner": home_pts if winner_is_home else away_pts,
            "points_loser": away_pts if winner_is_home else home_pts,
            "yards_winner": None, "turnovers_winner": None,
            "yards_loser": None, "turnovers_loser": None,
            "season": int(r.season),
            "timestamp_imported": timestamp,
        })
    return pd.DataFrame(rows)


def fetch_nflverse_games(seasons: list[int]) -> pd.DataFrame:
    resp = requests.get(NFLVERSE_GAMES_URL, timeout=60)
    resp.raise_for_status()
    timestamp = pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%d %H:%M:%S %Z")
    df = parse_nflverse_games(resp.text, seasons, timestamp)
    log.info("nflverse games: %d rows for seasons %s", len(df), seasons)
    return df
