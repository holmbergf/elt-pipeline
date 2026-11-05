{{ config(materialized='view') }}

-- One row per future fixture with market lines (null until posted) and each
-- team's season-to-date form. Fractions are 0-1 rounded to 2 decimals.
-- Spread convention: negative = favored (e.g. away_spread_points -9.5 means
-- the away team is favored by 9.5).
select
    u.game_date,
    u.season,
    u.week,
    u.home_team,
    u.away_team,
    u.home_spread as home_spread_points,
    u.away_spread as away_spread_points,
    u.spread_line as spread_line_points,
    u.market_favorite_team as spread_favorite,
    round(u.spread_home_consensus_pct, 2) as home_consensus_pct,
    round(u.spread_away_consensus_pct, 2) as away_consensus_pct,
    u.over_under_line as totals_line_points,
    round(u.over_consensus_pct, 2) as over_consensus_pct,
    round(u.under_consensus_pct, 2) as under_consensus_pct,

    h.wins as home_wins,
    h.losses as home_losses,
    h.record_display as home_record_display,
    h.win_pct as home_win_pct,
    h.season_rank as home_season_rank,
    h.against_the_spread_win_pct as home_against_the_spread_win_pct,
    h.over_pct as home_over_pct,
    h.avg_points_scored as home_avg_points_scored,
    h.consensus_spread_accuracy as home_consensus_spread_accuracy,
    h.consensus_total_accuracy as home_consensus_total_accuracy,

    a.wins as away_wins,
    a.losses as away_losses,
    a.record_display as away_record_display,
    a.win_pct as away_win_pct,
    a.season_rank as away_season_rank,
    a.against_the_spread_win_pct as away_against_the_spread_win_pct,
    a.over_pct as away_over_pct,
    a.avg_points_scored as away_avg_points_scored,
    a.consensus_spread_accuracy as away_consensus_spread_accuracy,
    a.consensus_total_accuracy as away_consensus_total_accuracy
from {{ ref('fct_nfl_betting_upcoming') }} u
left join {{ ref('semantic_team_season_form') }} h
    on h.team_name = u.home_team and h.season = u.season
left join {{ ref('semantic_team_season_form') }} a
    on a.team_name = u.away_team and a.season = u.season
