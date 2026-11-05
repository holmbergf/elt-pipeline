-- Team-market grain must be exactly 2 rows per settled game.
with per_game as (
    select game_id, count(*) as n from {{ ref('fct_nfl_team_market_games') }} group by 1
),
settled as (select count(*) as n from {{ ref('fct_nfl_betting_settled') }})
select p.game_id, p.n
from per_game p, settled s
where p.n != 2
   or (select count(*) from per_game) != s.n
