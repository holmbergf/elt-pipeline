{{ config(materialized='table') }}

-- Team-game grain for market analysis: one row per team per settled game,
-- with that team's consensus share, role, band, and outcomes. This is the
-- fix for consensus accuracy being game-level (credited to both teams):
-- here every rate is conditional on THIS team's consensus position.
with settled as (
    select s.*, g.winning_team_name
    from {{ ref('fct_nfl_betting_settled') }} s
    join {{ ref('fct_nfl_games') }} g on g.game_id = s.game_id
),

team_games as (
    select
        game_id, game_date, season, week,
        home_team as team_name, away_team as opponent, true as is_home,
        home_spread as team_spread_points,
        spread_home_consensus_pct as team_consensus_pct,
        case
            when spread_cover_winning_side = 'Home' then true
            when spread_cover_winning_side = 'Away' then false
        end as covered_spread,
        home_team = winning_team_name as won_game,
        over_consensus_pct, over_under_line,
        case when total_outcome = 'Over' then true when total_outcome = 'Under' then false end as over_hit
    from settled
    union all
    select
        game_id, game_date, season, week,
        away_team, home_team, false,
        away_spread,
        spread_away_consensus_pct,
        case
            when spread_cover_winning_side = 'Away' then true
            when spread_cover_winning_side = 'Home' then false
        end,
        away_team = winning_team_name,
        over_consensus_pct, over_under_line,
        case when total_outcome = 'Over' then true when total_outcome = 'Under' then false end
    from settled
)

select
    *,
    case
        when team_consensus_pct > 0.5 then 'Favorite'
        when team_consensus_pct < 0.5 then 'Underdog'
        else 'Even'
    end as consensus_role,
    case
        when team_consensus_pct >= 0.8 then '80% +'
        when team_consensus_pct >= 0.7 then '70-80%'
        when team_consensus_pct >= 0.6 then '60-70%'
        when team_consensus_pct >= 0.5 then '50-60%'
        when team_consensus_pct >= 0.4 then '40-50%'
        when team_consensus_pct >= 0.3 then '30-40%'
        when team_consensus_pct >= 0.2 then '20-30%'
        else 'Under 20%'
    end as consensus_band,
    case
        when team_consensus_pct >= 0.8 then 1 when team_consensus_pct >= 0.7 then 2
        when team_consensus_pct >= 0.6 then 3 when team_consensus_pct >= 0.5 then 4
        when team_consensus_pct >= 0.4 then 5 when team_consensus_pct >= 0.3 then 6
        when team_consensus_pct >= 0.2 then 7 else 8
    end as consensus_band_order,
    -- Totals are a game-level market: the consensus-favored side and its share.
    case when over_consensus_pct >= 0.5 then 'Over' else 'Under' end as totals_consensus_side,
    case when over_consensus_pct >= 0.5 then over_consensus_pct else 1 - over_consensus_pct end as totals_consensus_pct,
    case
        when over_consensus_pct >= 0.5 then over_hit
        else case when over_hit is null then null else not over_hit end
    end as totals_consensus_hit,
    case
        when team_spread_points < 0 then 'Favorite'
        when team_spread_points > 0 then 'Underdog'
        else 'Even'
    end as spread_role,
    case
        when abs(team_spread_points) = 0 then 'Pick''em (0)'
        when abs(team_spread_points) <= 2.5 then '0.5-2.5 pts'
        when abs(team_spread_points) <= 6.5 then '3-6.5 pts'
        when abs(team_spread_points) <= 9.5 then '7-9.5 pts'
        when abs(team_spread_points) <= 13.5 then '10-13.5 pts'
        else '14+ pts'
    end as spread_line_bucket,
    case
        when abs(team_spread_points) = 0 then 0
        when abs(team_spread_points) <= 2.5 then 1
        when abs(team_spread_points) <= 6.5 then 2
        when abs(team_spread_points) <= 9.5 then 3
        when abs(team_spread_points) <= 13.5 then 4
        else 5
    end as spread_line_bucket_order,
    case
        when over_under_line < 40 then 'Under 40'
        when over_under_line <= 43.5 then '40-43.5'
        when over_under_line <= 47.5 then '44-47.5'
        when over_under_line <= 51.5 then '48-51.5'
        when over_under_line <= 55.5 then '52-55.5'
        else '56+'
    end as totals_line_bucket,
    case
        when over_under_line < 40 then 0
        when over_under_line <= 43.5 then 1
        when over_under_line <= 47.5 then 2
        when over_under_line <= 51.5 then 3
        when over_under_line <= 55.5 then 4
        else 5
    end as totals_line_bucket_order
from team_games
