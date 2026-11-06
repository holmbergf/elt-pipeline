
{{ config(
    materialized='view'
) }}

with source as (
    select * from {{ raw_table('games', 'ncaaf') }}
)

select
    cast(date as date) as game_date,
    time,
    cast(season as integer) as season,
    week,
    day,
    home_team,
    away_team,
    cast(home_score as integer) as home_score,
    cast(away_score as integer) as away_score,
    cast(home_rank as integer) as home_rank,
    cast(away_rank as integer) as away_rank,
    cast(is_ranked_home as boolean) as is_ranked_home,
    cast(is_ranked_away as boolean) as is_ranked_away,
    cast(is_top25_matchup as boolean) as is_top25_matchup,
    winner,
    loser,
    cast(points_winner as integer) as points_winner,
    cast(points_loser as integer) as points_loser,
    boxscore,
    espn_home_abbr,
    espn_away_abbr,
    timestamp_imported
from source
