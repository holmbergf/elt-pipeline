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
        over_consensus_pct,
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
        over_consensus_pct,
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
    end as totals_consensus_hit
from team_games
