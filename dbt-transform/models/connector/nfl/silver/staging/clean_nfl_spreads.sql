
{{ config(
    materialized='table'
) }}

with source as (
    select * from {{ ref('stg_nfl_spreads') }}
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
        -- Split sides (e.g. "-7 +7")
        string_to_array(trim(sides), ' ') as sides_array,
        -- Split consensus (e.g. "45% 55%")
        string_to_array(trim(consensus), ' ') as consensus_array
    from source
),

split_teams as (
    select
        *,
        trim(split_part(raw_game_string, '@', 1)) as away_team_code,
        trim(split_part(raw_game_string, '@', 2)) as home_team_code,
        sides_array[1] as away_spread_raw,
        sides_array[2] as home_spread_raw,
        cast(replace(consensus_array[1], '%', '') as float) / 100.0 as away_consensus,
        cast(replace(consensus_array[2], '%', '') as float) / 100.0 as home_consensus
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
    away_spread_raw as away_spread,
    home_spread_raw as home_spread,
    round(away_consensus, 3) as away_consensus,
    round(home_consensus, 3) as home_consensus,
    case 
        when away_consensus > home_consensus then away_team_name 
        else home_team_name 
    end as consensus_spread_favorite,
    case 
        when away_consensus < home_consensus then away_team_name 
        else home_team_name 
    end as consensus_spread_underdog,
    -- Line clean: remove + and -
    replace(replace(away_spread_raw, '+', ''), '-', '') as line,
    timestamp_imported
from deduped
where rn = 1 and away_spread_raw != '0'
