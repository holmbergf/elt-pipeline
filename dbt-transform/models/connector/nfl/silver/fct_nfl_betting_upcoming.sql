
{{ config(
    materialized='table'
) }}

with games as (
    select * from {{ ref('clean_nfl_games') }}
    -- Upcoming means future: a past-dated scoreless game is a stale preview
    -- row, not a fixture. (Regression: Feb 2026 Super Bowl preview leaked in.)
    where (home_score is null or away_score is null)
      and game_date >= current_date
),

spreads as (
    select * from {{ ref('clean_nfl_spreads') }}
),

totals as (
    select * from {{ ref('clean_nfl_totals') }}
)

select
    -- ID
    md5(g.game_date || g.home_team || g.away_team) as game_id,
    md5(cast(g.game_date as varchar)) as date_id,
    
    -- Descriptive
    g.game_date,
    g.home_team,
    g.away_team,
    g.season,
    g.week,

    -- Spread Data
    -- We join on game_date and match teams regardless of order.
    -- Then we use case statements to ensure the spread is matched to the correct team.
    case 
        when g.away_team = s.away_team then cast(s.away_spread as float)
        else cast(s.home_spread as float)
    end as away_spread,
    case 
        when g.home_team = s.home_team then cast(s.home_spread as float)
        else cast(s.away_spread as float)
    end as home_spread,
    cast(s.line as float) as spread_line,
    
    case 
        when g.away_team = s.away_team then s.away_consensus
        else s.home_consensus
    end as spread_away_consensus_pct,
    case 
        when g.home_team = s.home_team then s.home_consensus
        else s.away_consensus
    end as spread_home_consensus_pct,
    
    s.consensus_spread_favorite as market_favorite_team,
    
    -- Totals Data
    t.total as over_under_line,
    t.over_consensus as over_consensus_pct,
    t.under_consensus as under_consensus_pct,
    t.consensus_total_favorite as market_total_preference

from games g
inner join spreads s on g.game_date = s.game_date 
    and (
        (g.home_team = s.home_team and g.away_team = s.away_team)
        or (g.home_team = s.away_team and g.away_team = s.home_team)
    )
inner join totals t on g.game_date = t.game_date 
    and (
        (g.home_team = t.home_team and g.away_team = t.away_team)
        or (g.home_team = t.away_team and g.away_team = t.home_team)
    )
