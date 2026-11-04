
{{ config(
    materialized='table'
) }}

select
    -- ID
    md5(game_date || home_team || away_team) as game_id,
    md5(cast(game_date as varchar)) as date_id,
    md5(home_team) as home_team_id,
    md5(away_team) as away_team_id,
    
    -- Context
    game_date,
    season,
    week,
    day,
    
    -- Scores
    home_score,
    away_score,
    total_points,
    win_marginal as win_margin,
    
    -- Winning Info
    case when winning_team_loc = 'Home' then home_team else away_team end as winning_team_name,
    winning_team_loc,
    
    case when winning_team_loc = 'Home' then home_score else away_score end as winning_score,
    case when winning_team_loc = 'Home' then away_score else home_score end as losing_score,

    -- Analytical Flags
    case when home_score is not null and away_score is not null then true else false end as is_game_finished,
    case when total_points > 50 then true else false end as is_high_scoring,
    case when win_marginal <= 3 then true else false end as is_close_game,
    
    timestamp_imported
from {{ ref('clean_nfl_games') }}
