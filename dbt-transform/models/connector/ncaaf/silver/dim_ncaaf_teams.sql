
{{ config(
    materialized='table'
) }}

-- One row per team_name: the seed carries several full_team_name aliases (and LA/LAR
-- codes) for the same team, so group before keying.
select
    md5(team_name) as team_id,
    min(team_code) as team_code,
    team_name
from {{ ref('ncaaf_team_mappings') }}
where team_name is not null and team_name != ''
group by team_name
