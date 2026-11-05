from elt_ingest.nflverse import parse_nflverse_games

CSV = """game_id,season,game_type,week,gameday,weekday,gametime,away_team,away_score,home_team,home_score,pfr
2026_01_NE_SEA,2026,REG,1,2026-09-09,Wednesday,20:20,NE,10,SEA,13,202609090sea
2026_01_SF_LA,2026,REG,1,2026-09-10,Thursday,20:35,SF,27,LA,7,202609100ram
2025_01_KC_BUF,2025,REG,1,2025-09-07,Sunday,13:00,KC,20,BUF,23,202509070buf
"""


def test_parse_nflverse_to_games_schema():
    df = parse_nflverse_games(CSV, seasons=[2026], timestamp="2026-11-04 00:00:00 UTC")
    assert len(df) == 2  # 2025 filtered out
    home_win = df.iloc[0]
    assert home_win["winner"] == "Seattle Seahawks"  # full name, matches seed mapping
    assert home_win["loser"] == "New England Patriots"
    assert home_win["location"] == ""
    assert (home_win["points_winner"], home_win["points_loser"]) == (13, 10)
    assert home_win["date"] == "2026-09-09" and home_win["week"] == "1"
    away_win = df.iloc[1]
    assert away_win["winner"] == "San Francisco 49ers" and away_win["location"] == "@"
    assert away_win["loser"] == "Los Angeles Rams"  # LA abbreviation normalised
