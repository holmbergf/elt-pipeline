-- Every future scoreless game in clean_nfl_games must appear in upcoming
-- (markets are left-joined; a fixture without lines is still upcoming).
with fixtures as (
    select count(*) as n from {{ ref('clean_nfl_games') }}
    where (home_score is null or away_score is null)
      and game_date >= cast(current_timestamp at time zone 'America/New_York' as date) - 1
),
up as (select count(*) as n from {{ ref('fct_nfl_betting_upcoming') }})
select f.n as fixtures, u.n as upcoming
from fixtures f, up u
where f.n != u.n
