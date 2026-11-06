{{ config(materialized='view') }}

-- Cover/win rates by a team's own consensus share (mirrored bands).
-- scope='League' rows aggregate all teams; season=0 means all seasons.
-- Rates are over decided games only (pushes counted separately).
select
    'League' as scope, cast(null as varchar) as team_name, season,
    consensus_band, consensus_band_order, consensus_role,
    count(*) as games, sum(case when covered_spread then 1 else 0 end) as covers,
    sum(case when covered_spread is null then 1 else 0 end) as pushes,
    round(sum(case when covered_spread then 1 else 0 end) / nullif(sum(case when covered_spread is not null then 1 else 0 end), 0), 2) as cover_pct,
    sum(case when won_game then 1 else 0 end) as game_wins,
    round(sum(case when won_game then 1 else 0 end) / count(*), 2) as win_pct
from {{ ref('fct_ncaaf_team_market_games') }}
group by season, consensus_band, consensus_band_order, consensus_role
union all
select
    'Team', team_name, season,
    consensus_band, consensus_band_order, consensus_role,
    count(*), sum(case when covered_spread then 1 else 0 end),
    sum(case when covered_spread is null then 1 else 0 end),
    round(sum(case when covered_spread then 1 else 0 end) / nullif(sum(case when covered_spread is not null then 1 else 0 end), 0), 2),
    sum(case when won_game then 1 else 0 end),
    round(sum(case when won_game then 1 else 0 end) / count(*), 2)
from {{ ref('fct_ncaaf_team_market_games') }}
group by team_name, season, consensus_band, consensus_band_order, consensus_role
union all
select
    'League', null, 0,
    consensus_band, consensus_band_order, consensus_role,
    count(*), sum(case when covered_spread then 1 else 0 end),
    sum(case when covered_spread is null then 1 else 0 end),
    round(sum(case when covered_spread then 1 else 0 end) / nullif(sum(case when covered_spread is not null then 1 else 0 end), 0), 2),
    sum(case when won_game then 1 else 0 end),
    round(sum(case when won_game then 1 else 0 end) / count(*), 2)
from {{ ref('fct_ncaaf_team_market_games') }}
group by consensus_band, consensus_band_order, consensus_role
union all
select
    'Team', team_name, 0,
    consensus_band, consensus_band_order, consensus_role,
    count(*), sum(case when covered_spread then 1 else 0 end),
    sum(case when covered_spread is null then 1 else 0 end),
    round(sum(case when covered_spread then 1 else 0 end) / nullif(sum(case when covered_spread is not null then 1 else 0 end), 0), 2),
    sum(case when won_game then 1 else 0 end),
    round(sum(case when won_game then 1 else 0 end) / count(*), 2)
from {{ ref('fct_ncaaf_team_market_games') }}
group by team_name, consensus_band, consensus_band_order, consensus_role
