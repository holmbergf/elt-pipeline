import pandas as pd

from elt_ingest.scrape import parse_covers_matchups

FIXTURE = """
<article class="gamebox postgamebox" data-away-team-shortname="car" data-home-team-shortname="gb">
  <p class="gamebox-header"><strong>Carolina @ Green Bay</strong></p>
  <a class="gamebox-team-anchor" href="/sport/football/nfl/teams/main/carolina-panthers"><span>CAR</span></a>
  <strong class="team-score away">19</strong>
  <strong class="covers-badge post-game-status">Final</strong>
  <strong class="team-score winner">27</strong>
  <a class="gamebox-team-anchor" href="/sport/football/nfl/teams/main/green-bay-packers"><span>GB</span></a>
  <a href="/sport/football/nfl/matchup/380025">Boxscore</a>
</article>
<article class="gamebox postgamebox" data-away-team-shortname="nyj" data-home-team-shortname="ne">
  <p class="gamebox-header"><strong>N.Y. Jets @ New England</strong></p>
  <a class="gamebox-team-anchor" href="/sport/football/nfl/teams/main/new-york-jets"><span>NYJ</span></a>
  <strong class="team-score away">30</strong>
  <strong class="covers-badge post-game-status">Final</strong>
  <strong class="team-score">24</strong>
  <a class="gamebox-team-anchor" href="/sport/football/nfl/teams/main/new-england-patriots"><span>NE</span></a>
  <a href="/sport/football/nfl/matchup/380099">Boxscore</a>
</article>
"""


def test_parse_covers_matchups_to_pfr_shape():
    df = parse_covers_matchups(
        FIXTURE,
        season=2026,
        dates_by_id={"380025": "2026-10-29", "380099": "2026-11-01"},
        timestamp="2026-11-04 00:00:00 UTC",
    )
    assert len(df) == 2
    home_win = df.iloc[0]
    assert home_win["winner"] == "Green Bay Packers"  # PFR name, matches seed mapping
    assert home_win["loser"] == "Carolina Panthers"
    assert home_win["location"] == ""  # winner at home
    assert (home_win["points_winner"], home_win["points_loser"]) == (27, 19)
    assert home_win["date"] == "2026-10-29" and home_win["season"] == 2026
    away_win = df.iloc[1]
    assert away_win["winner"] == "New York Jets" and away_win["location"] == "@"
    assert (away_win["points_winner"], away_win["points_loser"]) == (30, 24)
