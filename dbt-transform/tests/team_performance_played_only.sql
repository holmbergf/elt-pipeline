-- Team performance is a played-games model: unplayed fixtures (null scores)
-- must not appear, or every running denominator is diluted by the schedule.
select team_game_id, team_name, game_date
from {{ ref('fct_nfl_team_performance') }}
where points_scored is null or points_allowed is null
