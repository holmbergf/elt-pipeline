{{ config(materialized='view') }}

-- Over/under hit rates by the size of the totals line itself (game grain;
-- is_home keeps one row per game for League, team grain keeps both teams).
with scopes as (
    select 'League' as scope, cast(null as varchar) as team_name, season,
           totals_line_bucket, totals_line_bucket_order, over_hit
    from {{ ref('fct_nfl_team_market_games') }} where is_home
    union all
    select 'League', null, 0, totals_line_bucket, totals_line_bucket_order, over_hit
    from {{ ref('fct_nfl_team_market_games') }} where is_home
    union all
    select 'Team', team_name, season, totals_line_bucket, totals_line_bucket_order, over_hit
    from {{ ref('fct_nfl_team_market_games') }}
    union all
    select 'Team', team_name, 0, totals_line_bucket, totals_line_bucket_order, over_hit
    from {{ ref('fct_nfl_team_market_games') }}
)

select
    scope, team_name, season, totals_line_bucket, totals_line_bucket_order,
    count(*) as games,
    sum(case when over_hit then 1 else 0 end) as overs,
    sum(case when over_hit is null then 1 else 0 end) as pushes,
    round(sum(case when over_hit then 1 else 0 end)
        / nullif(sum(case when over_hit is not null then 1 else 0 end), 0), 2) as over_pct,
    round(sum(case when over_hit is not null and not over_hit then 1 else 0 end)
        / nullif(sum(case when over_hit is not null then 1 else 0 end), 0), 2) as under_pct
from scopes
group by scope, team_name, season, totals_line_bucket, totals_line_bucket_order
