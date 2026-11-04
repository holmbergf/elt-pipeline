{{ config(severity='warn') }}
-- Settled games with no matching spreads row: coverage gaps should be visible, not silent.
select g.game_date, g.home_team, g.away_team
from {{ ref('clean_nfl_games') }} g
left join {{ ref('clean_nfl_spreads') }} s
  on s.game_date = g.game_date and s.home_team = g.home_team and s.away_team = g.away_team
where g.home_score is not null and s.game_date is null
