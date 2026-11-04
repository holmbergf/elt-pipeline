"""Scrapers for Pro-Football-Reference (games) and Covers.com (spreads/totals).

Retries use tenacity; per-season/date failures are logged, not silently skipped.
The Playwright fallback stays because PFR intermittently blocks plain requests.
"""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime
from io import StringIO

import pandas as pd
import requests
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential

log = logging.getLogger(__name__)

PFR_GAMES_URL = "https://www.pro-football-reference.com/years/{year}/games.htm"
COVERS_SPREADS_URL = "https://contests.covers.com/consensus/topconsensus/nfl/overall/"
COVERS_TOTALS_URL = "https://contests.covers.com/consensus/topoverunderconsensus/nfl/overall/"
_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=2, max=30))
def _fetch_html(url: str) -> str:
    r = requests.get(url, headers={"User-Agent": _UA}, timeout=30)
    r.raise_for_status()
    return r.text


def _parse_games_table(html: str) -> pd.DataFrame | None:
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", {"id": "games"})
    if table is not None:
        return pd.read_html(StringIO(str(table)))[0]
    dfs = pd.read_html(StringIO(html))
    return dfs[0] if dfs else None


def _resolve_years(seasons, start_year, end_year) -> list[int]:
    current = datetime.now().year
    if seasons:
        return sorted(set(seasons))
    if start_year is not None or end_year is not None:
        sy = start_year if start_year is not None else current
        ey = end_year if end_year is not None else current
        return list(range(min(sy, ey), max(sy, ey) + 1))
    return [current]


async def scrape_nfl_games(seasons=None, start_year=None, end_year=None) -> pd.DataFrame:
    years = _resolve_years(seasons, start_year, end_year)
    timestamp = pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%d %H:%M:%S %Z")
    frames: list[pd.DataFrame] = []
    for i, yr in enumerate(years):
        if i > 0:
            time.sleep(2)
        try:
            df = _parse_games_table(_fetch_html(PFR_GAMES_URL.format(year=yr)))
            if df is not None:
                frames.append(df.assign(season=yr, timestamp_imported=timestamp))
        except Exception as exc:  # fall through to Playwright below
            log.warning("requests scrape failed for season %s: %s", yr, exc)
            frames = []
            break
    if not frames:
        frames = await _scrape_games_playwright(years, timestamp)
    if not frames:
        raise RuntimeError(
            f"No tables found for season(s) {years}. PFR may be rate-limiting; "
            "scrape fewer years or wait a few minutes."
        )
    result = pd.concat(frames, ignore_index=True)
    result.columns = [str(c).strip().lower().replace(" ", "_") for c in result.columns]
    return result


async def _scrape_games_playwright(years: list[int], timestamp: str) -> list[pd.DataFrame]:
    """Headless fallback. Headed/real-Chrome variant is archived in
    data-integration/legacy/headed_pfr.py (Cloudflare challenge loops there)."""
    from playwright.async_api import async_playwright

    frames: list[pd.DataFrame] = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        try:
            page = await browser.new_page(user_agent=_UA)
            for i, yr in enumerate(years):
                if i > 0:
                    await asyncio.sleep(3)
                try:
                    await page.goto(PFR_GAMES_URL.format(year=yr), timeout=30_000, wait_until="domcontentloaded")
                    df = _parse_games_table(await page.content())
                    if df is not None:
                        frames.append(df.assign(season=yr, timestamp_imported=timestamp))
                except Exception as exc:
                    log.warning("Playwright scrape failed for season %s: %s", yr, exc)
        finally:
            await browser.close()
    return frames


def _scrape_covers(base_url: str, dates: list[str]) -> pd.DataFrame:
    timestamp = pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%d %H:%M:%S %Z")
    frames: list[pd.DataFrame] = []
    for i, raw in enumerate(dates):
        date_str = str(raw).split(" ")[0]
        if i > 0:
            time.sleep(1)
        try:
            html = _fetch_html(f"{base_url}{date_str}")
            tables = BeautifulSoup(html, "lxml").find_all("table")
            if not tables:
                log.warning("no table at %s%s", base_url, date_str)
                continue
            frames.append(
                pd.read_html(StringIO(str(tables[0])))[0].assign(
                    event_date=date_str, timestamp_imported=timestamp
                )
            )
        except Exception as exc:
            log.warning("Covers scrape failed for %s: %s", date_str, exc)
    if not frames:
        return pd.DataFrame()
    df = pd.concat(frames, ignore_index=True)
    df.columns = [str(c).strip().lower().replace(" ", "_").replace(".", "") for c in df.columns]
    return df


async def scrape_nfl_spreads(dates: list[str]) -> pd.DataFrame:
    return _scrape_covers(COVERS_SPREADS_URL, dates)


async def scrape_nfl_over_unders(dates: list[str]) -> pd.DataFrame:
    return _scrape_covers(COVERS_TOTALS_URL, dates)


# ---------------------------------------------------------------------------
# Covers.com NFL matchups -> PFR-shaped games frame (replaces the PFR scrape,
# which is behind a Cloudflare challenge as of 2026-11; Covers returns 200).
# Output columns mirror the old PFR scrape so clean.normalise_games and the
# dbt bronze model keep working unchanged. Yards/turnovers come from each
# game's boxscore page when its stats table parses, else null (bronze-only
# columns; nothing downstream consumes them).
# ---------------------------------------------------------------------------

COVERS_MATCHUPS_URL = "https://www.covers.com/sports/nfl/matchups?selectedDate={date}"
COVERS_BOXSCORE_URL = "https://www.covers.com/sport/football/nfl/matchup/{game_id}"

# Covers team slug -> Pro-Football-Reference name (must match seeds/nfl_team_mappings.csv pfr_name)
COVERS_TEAM_NAMES = {
    "arizona-cardinals": "Arizona Cardinals", "atlanta-falcons": "Atlanta Falcons",
    "baltimore-ravens": "Baltimore Ravens", "buffalo-bills": "Buffalo Bills",
    "carolina-panthers": "Carolina Panthers", "chicago-bears": "Chicago Bears",
    "cincinnati-bengals": "Cincinnati Bengals", "cleveland-browns": "Cleveland Browns",
    "dallas-cowboys": "Dallas Cowboys", "denver-broncos": "Denver Broncos",
    "detroit-lions": "Detroit Lions", "green-bay-packers": "Green Bay Packers",
    "houston-texans": "Houston Texans", "indianapolis-colts": "Indianapolis Colts",
    "jacksonville-jaguars": "Jacksonville Jaguars", "kansas-city-chiefs": "Kansas City Chiefs",
    "las-vegas-raiders": "Las Vegas Raiders", "los-angeles-chargers": "Los Angeles Chargers",
    "los-angeles-rams": "Los Angeles Rams", "miami-dolphins": "Miami Dolphins",
    "minnesota-vikings": "Minnesota Vikings", "new-england-patriots": "New England Patriots",
    "new-orleans-saints": "New Orleans Saints", "new-york-giants": "New York Giants",
    "new-york-jets": "New York Jets", "philadelphia-eagles": "Philadelphia Eagles",
    "pittsburgh-steelers": "Pittsburgh Steelers", "san-francisco-49ers": "San Francisco 49ers",
    "seattle-seahawks": "Seattle Seahawks", "tampa-bay-buccaneers": "Tampa Bay Buccaneers",
    "tennessee-titans": "Tennessee Titans", "washington-commanders": "Washington Commanders",
}


def _season_anchor(season: int) -> pd.Timestamp:
    """Thursday of Week 1 (first Thursday of September)."""
    sep1 = pd.Timestamp(year=season, month=9, day=1)
    return sep1 + pd.Timedelta(days=(3 - sep1.dayofweek) % 7)


def _week_label(game_date: str, season: int) -> str:
    weeks = (pd.Timestamp(game_date) - _season_anchor(season)).days // 7 + 1
    return str(max(1, weeks))


def parse_covers_matchups(html: str, season: int, dates_by_id: dict[str, str], timestamp: str) -> pd.DataFrame:
    soup = BeautifulSoup(html, "lxml")
    rows = []
    for box in soup.select(".gamebox"):
        links = box.select('a[href*="/teams/main/"]')
        box_link = box.select_one('a[href*="/matchup/"]')
        scores = [s.get_text(strip=True) for s in box.select(".team-score")]
        if len(links) < 2 or box_link is None or len(scores) < 2:
            continue
        slugs = [a["href"].rstrip("/").split("/")[-1] for a in links[:2]]
        game_id = box_link["href"].rstrip("/").split("/")[-1]
        game_date = dates_by_id.get(game_id)
        if game_date is None:
            continue  # date comes from the boxscore page; unknown date = skip
        try:
            away_pts, home_pts = int(scores[0]), int(scores[-1])
        except ValueError:
            away_pts = home_pts = None  # scheduled / not yet final
        away, home = (COVERS_TEAM_NAMES.get(s, s) for s in slugs)
        winner_is_home = home_pts is not None and home_pts >= away_pts
        winner, loser = (home, away) if winner_is_home else (away, home)
        rows.append({
            "week": _week_label(game_date, season),
            "day": pd.Timestamp(game_date).strftime("%a"),
            "date": game_date,
            "time": "",
            "winner": winner,
            "location": "" if winner_is_home else "@",
            "loser": loser,
            "boxscore": game_id,
            "points_winner": home_pts if winner_is_home else away_pts,
            "points_loser": away_pts if winner_is_home else home_pts,
            "yards_winner": None, "turnovers_winner": None,
            "yards_loser": None, "turnovers_loser": None,
            "season": season,
            "timestamp_imported": timestamp,
            "_away": away, "_home": home,
            "_away_pts": away_pts, "_home_pts": home_pts,
        })
    return pd.DataFrame(rows)


def parse_boxscore_date(html: str) -> str | None:
    import re

    m = re.search(r"NFL Game on ([A-Z][a-z]+ \d{1,2}, \d{4})", BeautifulSoup(html, "lxml").get_text(" "))
    return pd.Timestamp(m.group(1)).strftime("%Y-%m-%d") if m else None


def parse_boxscore_stats(html: str) -> dict[str, dict[str, int]]:
    """Total yards (rush+pass) and turnovers (INT thrown + fumbles lost) per team name."""
    soup = BeautifulSoup(html, "lxml")
    for table in soup.select("table"):
        text = table.get_text(" ")
        if "Rushes-Yards" not in text or "Passing" not in text:
            continue
        rows = {}
        for tr in table.select("tr"):
            cells = [c.get_text(strip=True) for c in tr.select("td, th")]
            if len(cells) >= 3:
                rows[cells[0]] = cells[1:]
        if "Rushes-Yards" not in rows:
            continue
        out = {}
        for i in (0, 1):
            rush = int(rows["Rushes-Yards"][i].split("-")[-1])
            passing = int(rows["Passing Yards"][i])
            interceptions = int(rows["Passing"][i].split("-")[-1])
            fumbles_lost = int(rows["Fumbles-Lost"][i].split("-")[-1])
            out[i] = {"yards": rush + passing, "turnovers": interceptions + fumbles_lost}
        return out
    return {}


def _season_selected_dates(season: int) -> list[str]:
    """One selectedDate per NFL week (Week 1 Thursday + weekly through the Super Bowl)."""
    anchor = _season_anchor(season)
    return [(anchor + pd.Timedelta(days=7 * w)).strftime("%Y-%m-%d") for w in range(23)]


async def scrape_nfl_games_covers(seasons=None, start_year=None, end_year=None) -> pd.DataFrame:
    years = _resolve_years(seasons, start_year, end_year)
    timestamp = pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%d %H:%M:%S %Z")
    frames = []
    for yr in years:
        seen_ids: set[str] = set()
        raw_boxes: list[tuple[str, str]] = []  # (page_html, game_id)
        for sel_date in _season_selected_dates(yr):
            if sel_date > pd.Timestamp.now().strftime("%Y-%m-%d"):
                break
            html = _fetch_html(COVERS_MATCHUPS_URL.format(date=sel_date))
            soup = BeautifulSoup(html, "lxml")
            for box in soup.select(".gamebox"):
                link = box.select_one('a[href*="/matchup/"]')
                if link is None:
                    continue
                gid = link["href"].rstrip("/").split("/")[-1]
                if gid not in seen_ids:
                    seen_ids.add(gid)
                    raw_boxes.append((html, gid))
            time.sleep(1)
        # Boxscore pass: exact date + yards/turnovers per game.
        dates_by_id, stats_by_id = {}, {}
        page_by_id: dict[str, str] = {}
        for html, gid in raw_boxes:
            page_by_id.setdefault(gid, html)
        for gid in seen_ids:
            try:
                box_html = _fetch_html(COVERS_BOXSCORE_URL.format(game_id=gid))
                d = parse_boxscore_date(box_html)
                if d:
                    dates_by_id[gid] = d
                stats_by_id[gid] = parse_boxscore_stats(box_html)
            except Exception as exc:
                log.warning("Covers boxscore failed for game %s: %s", gid, exc)
            time.sleep(0.5)
        # Parse each weekly page once, keep only games whose id it contains.
        season_frames = []
        parsed_ids: set[str] = set()
        for html in {id(h): h for h, _ in raw_boxes}.values():
            df_page = parse_covers_matchups(html, yr, dates_by_id, timestamp)
            df_page = df_page[~df_page["boxscore"].isin(parsed_ids)]
            parsed_ids.update(df_page["boxscore"].astype(str))
            season_frames.append(df_page)
        if not season_frames:
            continue
        df = pd.concat(season_frames, ignore_index=True)
        for _, r in df.iterrows():
            st = stats_by_id.get(str(r["boxscore"]), {})
            if not st:
                continue
            away_st, home_st = st.get(0), st.get(1)
            win_st, lose_st = (home_st, away_st) if r["location"] == "" else (away_st, home_st)
            if win_st and lose_st:
                df.loc[r.name, "yards_winner"], df.loc[r.name, "turnovers_winner"] = win_st["yards"], win_st["turnovers"]
                df.loc[r.name, "yards_loser"], df.loc[r.name, "turnovers_loser"] = lose_st["yards"], lose_st["turnovers"]
        frames.append(df.drop(columns=["_away", "_home", "_away_pts", "_home_pts"]))
    if not frames:
        raise RuntimeError(f"No Covers matchups found for season(s) {years}.")
    return pd.concat(frames, ignore_index=True)
