{{ config(materialized='view') }}

-- How often the consensus-favored totals side (Over or Under) actually hits,
-- banded by that side's consensus share. season=0 means all seasons.
with banded as (
    select * exclude (consensus_band, consensus_band_order),
        case
            when totals_consensus_pct >= 0.8 then '80% +'
            when totals_consensus_pct >= 0.7 then '70-80%'
            when totals_consensus_pct >= 0.6 then '60-70%'
            else '50-60%'
        end as consensus_band,
        case
            when totals_consensus_pct >= 0.8 then 1 when totals_consensus_pct >= 0.7 then 2
            when totals_consensus_pct >= 0.6 then 3 else 4
        end as consensus_band_order
    from {{ ref('fct_nfl_team_market_games') }}
    -- one row per game for league grain would double-count; team grain keeps both teams
    where is_home
)

select
    'League' as scope, cast(null as varchar) as team_name, season,
    totals_consensus_side, consensus_band, consensus_band_order,
    count(*) as games,
    sum(case when totals_consensus_hit then 1 else 0 end) as hits,
    sum(case when totals_consensus_hit is null then 1 else 0 end) as pushes,
    round(sum(case when totals_consensus_hit then 1 else 0 end) / nullif(sum(case when totals_consensus_hit is not null then 1 else 0 end), 0), 2) as hit_pct
from banded group by season, totals_consensus_side, consensus_band, consensus_band_order
union all
select 'League', null, 0, totals_consensus_side, consensus_band, consensus_band_order,
    count(*), sum(case when totals_consensus_hit then 1 else 0 end),
    sum(case when totals_consensus_hit is null then 1 else 0 end),
    round(sum(case when totals_consensus_hit then 1 else 0 end) / nullif(sum(case when totals_consensus_hit is not null then 1 else 0 end), 0), 2)
from banded group by totals_consensus_side, consensus_band, consensus_band_order
union all
-- Team grain: a game's total belongs to both teams, so no is_home filter here.
select
    'Team', team_name, season,
    totals_consensus_side, consensus_band, consensus_band_order,
    count(*) as games,
    sum(case when totals_consensus_hit then 1 else 0 end) as hits,
    sum(case when totals_consensus_hit is null then 1 else 0 end) as pushes,
    round(sum(case when totals_consensus_hit then 1 else 0 end) / nullif(sum(case when totals_consensus_hit is not null then 1 else 0 end), 0), 2) as hit_pct
from (
    select * exclude (consensus_band, consensus_band_order),
        case
            when totals_consensus_pct >= 0.8 then '80% +' when totals_consensus_pct >= 0.7 then '70-80%'
            when totals_consensus_pct >= 0.6 then '60-70%' else '50-60%'
        end as consensus_band,
        case
            when totals_consensus_pct >= 0.8 then 1 when totals_consensus_pct >= 0.7 then 2
            when totals_consensus_pct >= 0.6 then 3 else 4
        end as consensus_band_order
    from {{ ref('fct_nfl_team_market_games') }}
) team_banded
group by team_name, season, totals_consensus_side, consensus_band, consensus_band_order
union all
select
    'Team', team_name, 0,
    totals_consensus_side, consensus_band, consensus_band_order,
    count(*), sum(case when totals_consensus_hit then 1 else 0 end),
    sum(case when totals_consensus_hit is null then 1 else 0 end),
    round(sum(case when totals_consensus_hit then 1 else 0 end) / nullif(sum(case when totals_consensus_hit is not null then 1 else 0 end), 0), 2)
from (
    select * exclude (consensus_band, consensus_band_order),
        case
            when totals_consensus_pct >= 0.8 then '80% +' when totals_consensus_pct >= 0.7 then '70-80%'
            when totals_consensus_pct >= 0.6 then '60-70%' else '50-60%'
        end as consensus_band,
        case
            when totals_consensus_pct >= 0.8 then 1 when totals_consensus_pct >= 0.7 then 2
            when totals_consensus_pct >= 0.6 then 3 else 4
        end as consensus_band_order
    from {{ ref('fct_nfl_team_market_games') }}
) team_banded_all
group by team_name, totals_consensus_side, consensus_band, consensus_band_order
