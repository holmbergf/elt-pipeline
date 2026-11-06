
{{ config(
    materialized='table'
) }}

with games as (
    select * from {{ ref('clean_ncaaf_games') }}
    where home_score is not null and away_score is not null
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

    -- Spread Data (Symmetric Mapping)
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
    t.consensus_total_favorite as market_total_preference,
    
    -- Outcome Math
    case 
        when g.total_points > t.total then 'Over'
        when g.total_points < t.total then 'Under'
        else 'Push'
    end as total_outcome,
    
    -- Spread Math (Covering)
    -- We use the mapped spreads from our case statements above
    case 
        when (g.away_score + (case when g.away_team = s.away_team then cast(s.away_spread as float) else cast(s.home_spread as float) end)) > g.home_score then 'Away'
        when (g.away_score + (case when g.away_team = s.away_team then cast(s.away_spread as float) else cast(s.home_spread as float) end)) < g.home_score then 'Home'
        else 'Push'
    end as spread_cover_winning_side,
    
    -- Behavioral Analysis
    case 
        when t.over_consensus > t.under_consensus and g.total_points > t.total then true
        when t.under_consensus > t.over_consensus and g.total_points < t.total then true
        else false
    end as was_consensus_total_winner,
    
    case 
        when s.consensus_spread_favorite = g.away_team and (g.away_score + (case when g.away_team = s.away_team then cast(s.away_spread as float) else cast(s.home_spread as float) end)) > g.home_score then true
        when s.consensus_spread_favorite = g.home_team and (g.home_score + (case when g.home_team = s.home_team then cast(s.home_spread as float) else cast(s.away_spread as float) end)) > g.away_score then true
        else false
    end as was_consensus_spread_winner

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
