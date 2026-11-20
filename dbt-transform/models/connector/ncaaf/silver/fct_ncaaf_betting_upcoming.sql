
{{ config(
    materialized='table'
) }}

with games as (
    select * from {{ ref('clean_ncaaf_games') }}
    -- Upcoming means future: a past-dated scoreless game is a stale preview
    -- row, not a fixture. (Regression: Feb 2026 Super Bowl preview leaked in.)
    -- Compare against the US Eastern sports date (with a day's grace for
    -- late finishes), never UTC current_date: CI builds run in UTC, where
    -- the date rolls over at 19:00 ET and tonight's game would be dropped
    -- as "past" before kickoff. The dashboard filters by Pacific date at
    -- read time, so keeping a just-finished game here is harmless.
    where (home_score is null or away_score is null)
      and game_date >= cast(current_timestamp at time zone 'America/New_York' as date) - 1
),

spreads as (
    select * from {{ ref('clean_ncaaf_spreads') }}
),

totals as (
    select * from {{ ref('clean_ncaaf_totals') }}
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
    g.home_rank,
    g.away_rank,
    g.is_top25_matchup,

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
left join spreads s on g.game_date = s.game_date 
    and (
        (g.home_team = s.home_team and g.away_team = s.away_team)
        or (g.home_team = s.away_team and g.away_team = s.home_team)
    )
left join totals t on g.game_date = t.game_date 
    and (
        (g.home_team = t.home_team and g.away_team = t.away_team)
        or (g.home_team = t.away_team and g.away_team = t.home_team)
    )
