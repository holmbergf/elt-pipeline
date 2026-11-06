
{{ config(
    materialized='table'
) }}

with source as (
    select * from {{ ref('stg_ncaaf_totals') }}
),

-- Create a unique mapping from code to team name to prevent fan-out
team_lookup as (
    select distinct team_code, team_name
    from {{ ref('ncaaf_team_mappings') }}
),

parsed as (
    select
        *,
        -- Matchup clean: "NCAAF LV  KC" -> "LV @ KC"
        upper(replace(trim(substring(matchup from 7)), '  ', ' @ ')) as raw_game_string,
        -- Extract consensus percentages using regex
        cast(regexp_extract(consensus, '(\d+) % Over', 1) as float) / 100.0 as over_consensus,
        cast(regexp_extract(consensus, '(\d+) % Under', 1) as float) / 100.0 as under_consensus
    from source
),

split_teams as (
    select
        *,
        trim(split_part(raw_game_string, '@', 1)) as away_team_code,
        trim(split_part(raw_game_string, '@', 2)) as home_team_code
    from parsed
),

mapped as (
    select
        s.*,
        a.team_name as away_team_name,
        h.team_name as home_team_name
    from split_teams s
    left join team_lookup a on s.away_team_code = a.team_code
    left join team_lookup h on s.home_team_code = h.team_code
)

select
    game_date,
    away_team_name as away_team,
    home_team_name as home_team,
    away_team_name || ' @ ' || home_team_name as game,
    cast(over_under_line as double) as total,
    round(over_consensus, 3) as over_consensus,
    round(under_consensus, 3) as under_consensus,
    case 
        when over_consensus > under_consensus then 'Over'
        else 'Under'
    end as consensus_total_favorite,
    case 
        when over_consensus < under_consensus then 'Over'
        else 'Under'
    end as consensus_total_underdog,
    timestamp_imported
from mapped
where over_under_line != 0
