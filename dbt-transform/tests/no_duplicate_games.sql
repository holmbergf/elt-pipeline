-- No duplicate games at the (season, date, home, away) grain.
select season, game_date, home_team, away_team, count(*) as n
from {{ ref('clean_nfl_games') }}
group by 1, 2, 3, 4
having count(*) > 1
