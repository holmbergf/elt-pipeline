
{{ config(
    materialized='table'
) }}

with team_stats as (
    select
        team_name,
        season,
        count(*) as total_games_played,
        sum(points_scored) as season_points_scored,
        sum(points_allowed) as season_points_allowed,
        avg(points_scored) as avg_points_scored,
        avg(points_allowed) as avg_points_allowed,
        -- Final seasonal stats
        max_by(running_win_percentage, game_date) as final_win_percentage,
        max_by(running_record, game_date) as final_record
    from {{ ref('fct_ncaaf_team_performance') }}
    group by 1, 2
)

select
    *,
    rank() over (partition by season order by final_win_percentage desc, (season_points_scored - season_points_allowed) desc) as season_rank
from team_stats
