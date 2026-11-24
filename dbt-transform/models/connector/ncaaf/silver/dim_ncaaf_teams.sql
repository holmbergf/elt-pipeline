
{{ config(
    materialized='table'
) }}

-- One row per team_name: the seed carries several full_team_name aliases (and LA/LAR
-- codes) for the same team, so group before keying. Union with teams observed
-- in the ESPN game feed so a real team missing from the Covers-driven seed
-- (a newcomer, an FCS opponent) can never orphan fct_ncaaf_games; such teams
-- get a null code and simply have no market joins. Seed codes win.
with seeded as (
    select
        team_name,
        min(team_code) as team_code
    from {{ ref('ncaaf_team_mappings') }}
    where team_name is not null and team_name != ''
    group by team_name
),

observed as (
    select home_team as team_name from {{ ref('clean_ncaaf_games') }}
    union
    select away_team from {{ ref('clean_ncaaf_games') }}
)

select
    md5(o.team_name) as team_id,
    s.team_code,
    o.team_name
from observed o
left join seeded s on s.team_name = o.team_name
where o.team_name is not null and o.team_name != ''
