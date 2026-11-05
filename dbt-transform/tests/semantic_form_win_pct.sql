-- Semantic win_pct must equal (wins + 0.5*ties)/games_played at 2dp, and
-- every rate on the human surface must be a fraction within [0, 1].
select team_name, season, win_pct
from {{ ref('semantic_team_season_form') }}
where abs(win_pct - round((wins + 0.5 * ties) / games_played, 2)) > 0.001
   or win_pct < 0 or win_pct > 1
   or (against_the_spread_win_pct is not null and (against_the_spread_win_pct < 0 or against_the_spread_win_pct > 1))
