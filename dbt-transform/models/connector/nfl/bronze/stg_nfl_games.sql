
{{ config(
    materialized='view'
) }}

with source as (
    select * from {{ raw_table('games') }}
)

select 
    week,
    day,
    cast(date as date) as game_date,
    time,
    winner,
    location,
    loser,
    boxscore,
    cast(points_winner as integer) as points_winner,
    cast(points_loser as integer) as points_loser,
    cast(yards_winner as integer) as yards_winner,
    cast(turnovers_winner as integer) as turnovers_winner,
    cast(yards_loser as integer) as yards_loser,
    cast(turnovers_loser as integer) as turnovers_loser,
    cast(season as integer) as season,
    timestamp_imported
from source
