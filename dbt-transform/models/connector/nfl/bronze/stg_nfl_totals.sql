
{{ config(
    materialized='view'
) }}

with source as (
    select * from {{ raw_table('totals') }}
)

select
    matchup,
    cast(event_date as date) as game_date,
    consensus,
    total as over_under_line,
    picks,
    timestamp_imported
from source
