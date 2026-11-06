
{{ config(
    materialized='table'
) }}

with market_stats as (
    select
        team_name,
        season,
        count(*) as total_games_played,
        max_by(games_with_market, game_date) as games_with_market,
        -- Market Spread Performance
        max_by(running_ats_win_percentage, game_date) as ats_win_percentage,
        max_by(running_ats_record, game_date) as ats_record,
        max_by(running_consensus_spread_win_percentage, game_date) as market_spread_accuracy,
        
        -- Market Total Performance
        max_by(running_over_percentage, game_date) as over_percentage,
        max_by(running_over_under_record, game_date) as over_under_record,
        max_by(running_consensus_total_win_percentage, game_date) as market_total_accuracy,
        max_by(running_avg_total_points, game_date) as avg_total_points
    from {{ ref('fct_ncaaf_team_performance') }}
    group by 1, 2
)

select
    *,
    -- Rank teams by how much they "beat" the spread (ATS percentage)
    rank() over (partition by season order by ats_win_percentage desc) as best_ats_rank,
    rank() over (partition by season order by over_percentage desc) as best_over_rank,
    -- Rank teams by how "predictable" they are for the public (Market accuracy)
    rank() over (partition by season order by market_spread_accuracy desc) as most_predictable_spread_rank,
    rank() over (partition by season order by market_total_accuracy desc) as most_predictable_total_rank
from market_stats
