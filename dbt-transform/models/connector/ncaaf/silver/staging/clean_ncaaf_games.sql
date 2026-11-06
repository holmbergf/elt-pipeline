
{{ config(
    materialized='table'
) }}

-- ESPN names are canonical (no mapping needed). Raw is append-only, so
-- dedupe to one row per game, preferring the scored version.
with deduped as (
    select
        *,
        row_number() over (
            partition by game_date, least(home_team, away_team), greatest(home_team, away_team)
            order by (home_score is not null) desc, timestamp_imported desc
        ) as rn
    from {{ ref('stg_ncaaf_games') }}
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
    home_rank,
    away_rank,
    is_ranked_home,
    is_ranked_away,
    is_top25_matchup,
    away_team || ' @ ' || home_team as game,
    cast(away_score as varchar) || '-' || cast(home_score as varchar) as final_score,
    home_score + away_score as total_points,
    abs(home_score - away_score) as win_marginal,
    case
        when home_score is null or away_score is null then null
        when home_score = away_score then 'Tie'
        when home_score > away_score then 'Home'
        else 'Away'
    end as winning_team_loc,
    timestamp_imported
from deduped
where rn = 1
