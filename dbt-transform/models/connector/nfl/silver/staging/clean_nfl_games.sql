
{{ config(
    materialized='table'
) }}

with base as (
    select 
        *,
        case when nullif(location, '') is null then winner else loser end as home_team_raw,
        case when nullif(location, '') is null then loser else winner end as away_team_raw,
        case when nullif(location, '') is null then points_winner else points_loser end as home_score,
        case when nullif(location, '') is null then points_loser else points_winner end as away_score
    from {{ ref('stg_nfl_games') }}
),

mapped as (
    select
        b.*,
        h.team_name as home_team,
        a.team_name as away_team
    from base b
    left join {{ ref('nfl_team_mappings') }} h on b.home_team_raw = h.full_team_name
    left join {{ ref('nfl_team_mappings') }} a on b.away_team_raw = a.full_team_name
),

-- Raw is append-only: a game first seen as a scoreless preview can later
-- arrive again with the result. Keep one row per game, preferring the
-- scored (latest corrected) version.
deduped as (
    select
        *,
        row_number() over (
            -- Unordered team pair: a preview row and its corrected version
            -- can disagree on home/away (neutral-site games).
            partition by game_date, least(home_team, away_team), greatest(home_team, away_team)
            order by (home_score is not null) desc, timestamp_imported desc
        ) as rn
    from mapped
    where home_team is not null and away_team is not null
)

select
    week,
    day,
    game_date,
    time,
    season,
    home_team,
    away_team,
    home_score,
    away_score,
    away_team || ' @ ' || home_team as game,
    cast(away_score as varchar) || '-' || cast(home_score as varchar) as final_score,
    home_score + away_score as total_points,
    abs(home_score - away_score) as win_marginal,
    case 
        when abs(home_score - away_score) = 0 then 'Tie'
        when nullif(location, '') is null then 'Home'
        else 'Away'
    end as winning_team_loc,
    timestamp_imported
from deduped
where rn = 1
