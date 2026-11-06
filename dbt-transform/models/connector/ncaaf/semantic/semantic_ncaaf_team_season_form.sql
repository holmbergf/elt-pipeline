{{ config(materialized='view') }}

-- One row per team-season, season-to-date form. This is the human surface:
-- fractions are 0-1 rounded to 2 decimals, records are integer W/L/T columns,
-- and market rates are over decided market games only (see games_with_market).
with agg as (
    select
        team_name,
        season,
        count(*) as games_played,
        cast(sum(is_win) as integer) as wins,
        cast(sum(is_loss) as integer) as losses,
        cast(sum(is_tie) as integer) as ties,
        round(avg(points_scored), 2) as avg_points_scored,
        round(avg(points_allowed), 2) as avg_points_allowed,
        cast(sum(is_ats_win) as integer) as against_the_spread_wins,
        cast(sum(is_ats_loss) as integer) as against_the_spread_losses,
        cast(sum(is_ats_push) as integer) as against_the_spread_pushes,
        cast(sum(is_over) as integer) as overs,
        cast(sum(is_under) as integer) as unders,
        cast(sum(is_total_push) as integer) as total_pushes,
        cast(max(games_with_market) as integer) as games_with_market,
        cast(sum(was_consensus_spread_correct) as integer) as consensus_spread_correct,
        cast(sum(was_consensus_total_correct) as integer) as consensus_total_correct
    from {{ ref('fct_ncaaf_team_performance') }}
    group by 1, 2
)

select
    team_name,
    season,
    games_played,
    wins,
    losses,
    ties,
    cast(wins as varchar) || '-' || cast(losses as varchar) || '-' || cast(ties as varchar) as record_display,
    round((wins + 0.5 * ties) / games_played, 2) as win_pct,
    avg_points_scored,
    avg_points_allowed,
    games_with_market,
    against_the_spread_wins,
    against_the_spread_losses,
    against_the_spread_pushes,
    round(
        (against_the_spread_wins + 0.5 * against_the_spread_pushes)
        / nullif(against_the_spread_wins + against_the_spread_losses + against_the_spread_pushes, 0),
        2
    ) as against_the_spread_win_pct,
    overs,
    unders,
    total_pushes,
    round(
        (overs + 0.5 * total_pushes) / nullif(overs + unders + total_pushes, 0), 2
    ) as over_pct,
    round(consensus_spread_correct / nullif(games_with_market, 0), 2) as consensus_spread_accuracy,
    round(consensus_total_correct / nullif(games_with_market, 0), 2) as consensus_total_accuracy,
    rank() over (
        partition by season
        order by (wins + 0.5 * ties) / games_played desc, (avg_points_scored - avg_points_allowed) desc
    ) as season_rank
from agg
