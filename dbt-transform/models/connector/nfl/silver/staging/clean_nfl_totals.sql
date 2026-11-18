
{{ config(
    materialized='table'
) }}

with source as (
    select * from {{ ref('stg_nfl_totals') }}
),

-- Create a unique mapping from code to team name to prevent fan-out
team_lookup as (
    select distinct team_code, team_name
    from {{ ref('nfl_team_mappings') }}
),

parsed as (
    select
        *,
        -- Matchup clean: "NFL LV  KC" -> "LV @ KC"
        upper(replace(trim(substring(matchup from 5)), '  ', ' @ ')) as raw_game_string,
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
),

-- Raw is append-only: a re-scrape of a date appends an updated version of
-- each matchup. Keep the latest version per game (mirrors NCAAF staging).
deduped as (
    select *, row_number() over (
        partition by game_date, least(home_team_name, away_team_name), greatest(home_team_name, away_team_name)
        order by timestamp_imported desc) as rn
    from mapped
)

select
    game_date,
    away_team_name as away_team,
    home_team_name as home_team,
    away_team_name || ' @ ' || home_team_name as game,
    over_under_line as total,
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
from deduped
where rn = 1 and over_under_line != 0
