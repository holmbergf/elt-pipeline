{{ config(materialized='view') }}

-- Cover/win rates by spread size, split by role. A -9.5 favorite and a +9.5
-- underdog in the same game land in the same bucket with opposite roles.
-- season=0 means all seasons; pushes excluded from cover % (counted apart).
with scopes as (
    select 'League' as scope, cast(null as varchar) as team_name, season,
           spread_role, spread_line_bucket, spread_line_bucket_order,
           covered_spread, won_game
    from {{ ref('fct_ncaaf_team_market_games') }}
    union all
    select 'League', null, 0, spread_role, spread_line_bucket, spread_line_bucket_order, covered_spread, won_game
    from {{ ref('fct_ncaaf_team_market_games') }}
    union all
    select 'Team', team_name, season, spread_role, spread_line_bucket, spread_line_bucket_order, covered_spread, won_game
    from {{ ref('fct_ncaaf_team_market_games') }}
    union all
    select 'Team', team_name, 0, spread_role, spread_line_bucket, spread_line_bucket_order, covered_spread, won_game
    from {{ ref('fct_ncaaf_team_market_games') }}
)

select
    scope, team_name, season, spread_role, spread_line_bucket, spread_line_bucket_order,
    count(*) as games,
    sum(case when covered_spread then 1 else 0 end) as covers,
    sum(case when covered_spread is null then 1 else 0 end) as pushes,
    round(sum(case when covered_spread then 1 else 0 end)
        / nullif(sum(case when covered_spread is not null then 1 else 0 end), 0), 2) as cover_pct,
    round(sum(case when won_game then 1 else 0 end) / count(*), 2) as win_pct
from scopes
group by scope, team_name, season, spread_role, spread_line_bucket, spread_line_bucket_order
