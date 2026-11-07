"""NCAAF games from ESPN's public scoreboard API (no key required).

One JSON call per week. Output uses the canonical games columns plus
home/away orientation and Top-25 ranks (curatedRank 1-25; 99 = unranked):
  date, season, week, home_team, away_team, home_score, away_score,
  home_rank, away_rank, is_ranked_home, is_ranked_away, is_top25_matchup
Winner/loser/location are also derived so market joins can reuse NFL logic.
"""

from __future__ import annotations

import logging
import time

import pandas as pd
import requests

log = logging.getLogger(__name__)

ESPN_SCOREBOARD = "https://site.api.espn.com/apis/site/v2/sports/football/college-football/scoreboard"
GROUPS = 80  # FBS


def _get_json(url: str, params: dict) -> dict:
    r = requests.get(url, params=params, timeout=30, headers={"User-Agent": "elt-pipeline/0.1"})
    r.raise_for_status()
    return r.json()


def _rank(comp: dict) -> int | None:
    rk = (comp.get("curatedRank") or {}).get("current")
    return int(rk) if rk and 1 <= int(rk) <= 25 else None


def parse_espn_events(payload: dict, season: int) -> list[dict]:
    rows = []
    ts = pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%d %H:%M:%S %Z")
    for ev in payload.get("events", []):
        comp = (ev.get("competitions") or [{}])[0]
        by_side = {c.get("homeAway"): c for c in comp.get("competitors", [])}
        if "home" not in by_side or "away" not in by_side:
            continue
        home, away = by_side["home"], by_side["away"]
        completed = bool((ev.get("status", {}).get("type") or {}).get("completed"))
        def score(c):
            return int(c["score"]) if completed and str(c.get("score", "")).isdigit() else None
        hs, aws = score(home), score(away)
        hname, aname = home["team"]["displayName"], away["team"]["displayName"]
        winner = hname if (hs is not None and hs >= aws) else aname
        # Sports date = US Eastern calendar day of kickoff. ESPN timestamps
        # are UTC; slicing the UTC date puts evening kickoffs on the next
        # day and breaks the join to Covers (US-dated) market pages.
        kickoff_et = pd.Timestamp(ev["date"]).tz_convert("America/New_York")
        rows.append({
            "date": kickoff_et.strftime("%Y-%m-%d"),
            "time": kickoff_et.strftime("%H:%M"),
            "season": season,
            "week": str(ev.get("week", {}).get("number", "")) if isinstance(ev.get("week"), dict) else str(ev.get("week", "")),
            "day": kickoff_et.strftime("%a"),
            "home_team": hname,
            "away_team": aname,
            "home_score": hs,
            "away_score": aws,
            "home_rank": _rank(home),
            "away_rank": _rank(away),
            "is_ranked_home": _rank(home) is not None,
            "is_ranked_away": _rank(away) is not None,
            "is_top25_matchup": _rank(home) is not None and _rank(away) is not None,
            "winner": winner,
            "loser": aname if winner == hname else hname,
            "location": "" if winner == hname else "@",
            "points_winner": max(hs, aws) if hs is not None else None,
            "points_loser": min(hs, aws) if hs is not None else None,
            "boxscore": str(ev.get("id", "")),
            "timestamp_imported": ts,
            "espn_home_abbr": home["team"].get("abbreviation", ""),
            "espn_away_abbr": away["team"].get("abbreviation", ""),
        })
    return rows


def fetch_cfb_games(seasons: list[int]) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for season in seasons:
        rows: list[dict] = []
        seen: set[str] = set()
        for seasontype, weeks in ((2, range(1, 17)), (3, range(1, 6))):
            for week in weeks:
                try:
                    payload = _get_json(ESPN_SCOREBOARD, {
                        "groups": GROUPS, "dates": season, "seasontype": seasontype,
                        "week": week, "limit": 300,
                    })
                except Exception as exc:
                    log.warning("ESPN CFB fetch failed season=%s type=%s week=%s: %s", season, seasontype, week, exc)
                    continue
                for r in parse_espn_events(payload, season):
                    if r["boxscore"] not in seen:
                        seen.add(r["boxscore"])
                        rows.append(r)
                time.sleep(0.3)
        if rows:
            frames.append(pd.DataFrame(rows))
            log.info("ESPN CFB season %s: %d games", season, len(rows))
    if not frames:
        raise RuntimeError(f"No ESPN CFB games found for seasons {seasons}.")
    return pd.concat(frames, ignore_index=True)


def fetch_cfb_teams() -> pd.DataFrame:
    """Team reference (abbreviation + names) from the teams in fetched games is
    preferred; this endpoint is the fallback catalogue."""
    payload = _get_json(
        "https://site.api.espn.com/apis/site/v2/sports/football/college-football/teams",
        {"groups": GROUPS, "limit": 400},
    )
    teams = payload["sports"][0]["leagues"][0]["teams"]
    return pd.DataFrame([
        {
            "team_code": t["team"].get("abbreviation", ""),
            "team_name": t["team"].get("shortDisplayName", t["team"]["displayName"]),
            "full_team_name": t["team"]["displayName"],
        }
        for t in teams
    ])
