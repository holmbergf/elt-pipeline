{{ config(materialized='view') }}

-- One row per played game with result + market outcome, human names.
select
    g.game_date,
    g.season,
    g.week,
    g.home_rank,
    g.away_rank,
    g.is_top25_matchup,
    ht.team_name as home_team,
    awt.team_name as away_team,
    g.home_score,
    g.away_score,
    g.total_points,
    g.win_margin as margin_points,
    g.winning_team_name as winner,
    g.is_close_game,
    b.home_spread as home_spread_points,
    b.away_spread as away_spread_points,
    b.spread_line as spread_line_points,
    b.market_favorite_team as spread_favorite,
    b.over_under_line as totals_line_points,
    b.total_outcome as totals_result,
    b.spread_cover_winning_side as spread_cover_side
from {{ ref('fct_ncaaf_games') }} g
join {{ ref('dim_ncaaf_teams') }} ht on ht.team_id = g.home_team_id
join {{ ref('dim_ncaaf_teams') }} awt on awt.team_id = g.away_team_id
left join {{ ref('fct_ncaaf_betting_settled') }} b on b.game_id = g.game_id
where g.is_game_finished
