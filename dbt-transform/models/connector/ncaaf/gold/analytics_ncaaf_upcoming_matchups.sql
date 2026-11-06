
{{ config(
    materialized='table'
) }}

with upcoming as (
    select * from {{ ref('fct_ncaaf_betting_upcoming') }}
),

team_rankings as (
    select * from {{ ref('analytics_ncaaf_team_rankings') }}
),

betting_stats as (
    select * from {{ ref('analytics_ncaaf_team_betting_stats') }}
)

select
    u.game_id,
    u.game_date,
    u.season,
    u.week,
    u.home_team,
    u.away_team,
    
    -- Betting Lines
    u.home_spread,
    u.away_spread,
    u.spread_line,
    u.spread_home_consensus_pct,
    u.spread_away_consensus_pct,
    u.market_favorite_team,
    u.over_under_line,
    u.over_consensus_pct,
    u.under_consensus_pct,

    -- Home Team Analytics
    hr.final_record as home_record,
    hr.final_win_percentage as home_win_pct,
    hr.season_rank as home_season_rank,
    hb.ats_record as home_ats_record,
    hb.ats_win_percentage as home_ats_win_pct,
    hb.avg_total_points as home_avg_total_points,
    hb.over_under_record as home_over_under_record,
    hb.over_percentage as home_over_pct,
    hb.market_spread_accuracy as home_market_spread_predictability,
    hb.market_total_accuracy as home_market_total_predictability,

    -- Away Team Analytics
    ar.final_record as away_record,
    ar.final_win_percentage as away_win_pct,
    ar.season_rank as away_season_rank,
    ab.ats_record as away_ats_record,
    ab.ats_win_percentage as away_ats_win_pct,
    ab.avg_total_points as away_avg_total_points,
    ab.over_under_record as away_over_under_record,
    ab.over_percentage as away_over_pct,
    ab.market_spread_accuracy as away_market_spread_predictability,
    ab.market_total_accuracy as away_market_total_predictability,

from upcoming u
left join team_rankings hr on u.home_team = hr.team_name and u.season = hr.season
left join betting_stats hb on u.home_team = hb.team_name and u.season = hb.season
left join team_rankings ar on u.away_team = ar.team_name and u.season = ar.season
left join betting_stats ab on u.away_team = ab.team_name and u.season = ab.season
