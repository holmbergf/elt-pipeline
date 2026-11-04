
{{ config(
    materialized='view'
) }}

with source as (
    select * from {{ raw_table('spreads') }}
)

select
    matchup,
    cast(event_date as date) as game_date,
    consensus,
    sides,
    picks,
    timestamp_imported
from source
