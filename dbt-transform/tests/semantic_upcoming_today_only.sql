-- The semantic upcoming surface is a today-only display: exactly the games
-- being played today, not the whole future schedule (that stays available
-- in silver fct_nfl_betting_upcoming).
select game_date, home_team, away_team
from {{ ref('semantic_upcoming_matchups') }}
where game_date != current_date
