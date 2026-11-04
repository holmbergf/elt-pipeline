"""Cleaning / schema normalisation shared by backfill and incremental jobs."""

from __future__ import annotations

import hashlib
import json

import pandas as pd

GAMES_COLUMN_MAPPING = {
    "week": "week",
    "day": "day",
    "game_date": "date",
    "game_time_of_day_est": "time",
    "time": "time",
    "winner/tie": "winner",
    "unnamed:_5": "location",
    "loser/tie": "loser",
    "unnamed:_7": "boxscore",
    "ptsw": "points_winner",
    "ptsl": "points_loser",
    "ydsw": "yards_winner",
    "tow": "turnovers_winner",
    "ydsl": "yards_loser",
    "tol": "turnovers_loser",
}

GAMES_NATURAL_KEY = ["season", "date", "winner", "loser"]
MARKET_NATURAL_KEY = ["event_date", "matchup"]


def apply_games_mapping(df: pd.DataFrame) -> pd.DataFrame:
    df = df.rename(columns={k: v for k, v in GAMES_COLUMN_MAPPING.items() if k in df.columns})
    # Scraped PFR tables carry a stray duplicate header column ("date.1" = "boxscore").
    df = df.drop(columns=[c for c in df.columns if str(c).endswith(".1")], errors="ignore")
    if "date" in df.columns:
        df = df[~df["date"].astype(str).str.lower().isin(["date", "playoffs"])]
    return df


def parse_game_date(date_str: object, season: int) -> pd.Timestamp:
    """Parse PFR game_date (e.g. 'Thu Sep 5') using the season for the year."""
    if pd.isna(date_str) or str(date_str).strip() == "":
        return pd.NaT
    s = str(date_str).strip()
    if s.lower() in ("week", "wild card", "divisional", "conference", "super bowl", "playoffs", "date"):
        return pd.NaT
    try:
        dt = pd.to_datetime(s)
        if dt.year >= 2000:  # bare "Thu Sep 5" parses to year 1/1900 — treat as year-less
            return dt
    except Exception:
        pass
    for fmt in ("%a %b %d", "%A %B %d"):
        try:
            dt = pd.to_datetime(s, format=fmt)
            year = int(season) if dt.month >= 9 else int(season) + 1
            return pd.Timestamp(year=year, month=dt.month, day=dt.day)
        except Exception:
            continue
    return pd.NaT


def normalise_games(df: pd.DataFrame) -> pd.DataFrame:
    """ISO dates (YYYY-MM-DD), header rows dropped, duplicates removed."""
    df = apply_games_mapping(df.copy())
    if "season" not in df.columns:
        raise ValueError("games frame has no 'season' column")
    parsed = df.apply(lambda r: parse_game_date(r.get("date", ""), r["season"]), axis=1)
    df = df.assign(date=parsed).dropna(subset=["date"])
    df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
    return dedupe(df, GAMES_NATURAL_KEY)


def dedupe(df: pd.DataFrame, natural_key: list[str]) -> pd.DataFrame:
    key = [c for c in natural_key if c in df.columns]
    if key:
        df = df.drop_duplicates(subset=key, keep="last")
    return df.drop_duplicates().reset_index(drop=True)


def content_hash(df: pd.DataFrame) -> str:
    """Stable hash of frame content; identical re-runs produce identical keys."""
    if df.empty:
        return hashlib.sha256(b"empty").hexdigest()[:16]
    hashed = pd.util.hash_pandas_object(df.sort_index(axis=1), index=False)
    return hashlib.sha256(hashed.values.tobytes() + json.dumps(list(df.columns)).encode()).hexdigest()[:16]
