
{{ config(
    materialized='table'
) }}

with base_games as (
    -- Played games only: unplayed fixtures would dilute every running
    -- denominator with scheduled-but-unplayed rows.
    select * from {{ ref('clean_ncaaf_games') }}
    where home_score is not null and away_score is not null
),

betting as (
    select * from {{ ref('fct_ncaaf_betting_settled') }}
),

game_performance as (
    -- Home Team Grain
    select
        md5(g.game_date || g.home_team || g.away_team) as game_id,
        g.game_date,
        g.season,
        g.home_team as team_name,
        'Home' as team_location,
        g.home_score as points_scored,
        g.away_score as points_allowed,
        case when g.home_score > g.away_score then 1 else 0 end as is_win,
        case when g.home_score < g.away_score then 1 else 0 end as is_loss,
        case when g.home_score = g.away_score then 1 else 0 end as is_tie,
        -- Betting Flags (Home)
        case when b.spread_cover_winning_side = 'Home' then 1 else 0 end as is_ats_win,
        case when b.spread_cover_winning_side = 'Away' then 1 else 0 end as is_ats_loss,
        case when b.spread_cover_winning_side = 'Push' then 1 else 0 end as is_ats_push,
        case when b.total_outcome = 'Over' then 1 else 0 end as is_over,
        case when b.total_outcome = 'Under' then 1 else 0 end as is_under,
        case when b.total_outcome = 'Push' then 1 else 0 end as is_total_push,
        case when b.was_consensus_spread_winner then 1 else 0 end as was_consensus_spread_correct,
        case when b.was_consensus_total_winner then 1 else 0 end as was_consensus_total_correct,
        case when b.game_id is not null then 1 else 0 end as is_market_game
    from base_games g
    left join betting b on g.game_date = b.game_date and g.home_team = b.home_team and g.away_team = b.away_team
    
    union all
    
    -- Away Team Grain
    select
        md5(g.game_date || g.home_team || g.away_team) as game_id,
        g.game_date,
        g.season,
        g.away_team as team_name,
        'Away' as team_location,
        g.away_score as points_scored,
        g.home_score as points_allowed,
        case when g.away_score > g.home_score then 1 else 0 end as is_win,
        case when g.away_score < g.home_score then 1 else 0 end as is_loss,
        case when g.away_score = g.home_score then 1 else 0 end as is_tie,
        -- Betting Flags (Away)
        case when b.spread_cover_winning_side = 'Away' then 1 else 0 end as is_ats_win,
        case when b.spread_cover_winning_side = 'Home' then 1 else 0 end as is_ats_loss,
        case when b.spread_cover_winning_side = 'Push' then 1 else 0 end as is_ats_push,
        case when b.total_outcome = 'Over' then 1 else 0 end as is_over,
        case when b.total_outcome = 'Under' then 1 else 0 end as is_under,
        case when b.total_outcome = 'Push' then 1 else 0 end as is_total_push,
        case when b.was_consensus_spread_winner then 1 else 0 end as was_consensus_spread_correct,
        case when b.was_consensus_total_winner then 1 else 0 end as was_consensus_total_correct,
        case when b.game_id is not null then 1 else 0 end as is_market_game
    from base_games g
    left join betting b on g.game_date = b.game_date and g.home_team = b.home_team and g.away_team = b.away_team
),

running_totals as (
    select
        *,
        -- Standard Records
        sum(is_win) over (partition by team_name, season order by game_date rows between unbounded preceding and current row) as running_wins,
        sum(is_loss) over (partition by team_name, season order by game_date rows between unbounded preceding and current row) as running_losses,
        sum(is_tie) over (partition by team_name, season order by game_date rows between unbounded preceding and current row) as running_ties,
        count(*) over (partition by team_name, season order by game_date rows between unbounded preceding and current row) as running_games_played,
        
        -- ATS Records
        sum(is_ats_win) over (partition by team_name, season order by game_date rows between unbounded preceding and current row) as running_ats_wins,
        sum(is_ats_loss) over (partition by team_name, season order by game_date rows between unbounded preceding and current row) as running_ats_losses,
        sum(is_ats_push) over (partition by team_name, season order by game_date rows between unbounded preceding and current row) as running_ats_pushes,
        
        -- Over/Under Records
        sum(is_over) over (partition by team_name, season order by game_date rows between unbounded preceding and current row) as running_overs,
        sum(is_under) over (partition by team_name, season order by game_date rows between unbounded preceding and current row) as running_unders,
        sum(is_total_push) over (partition by team_name, season order by game_date rows between unbounded preceding and current row) as running_total_pushes,
        
        -- Consensus Performance (How often consensus was right in games involving this team)
        sum(was_consensus_spread_correct) over (partition by team_name, season order by game_date rows between unbounded preceding and current row) as running_consensus_spread_wins,
        sum(was_consensus_total_correct) over (partition by team_name, season order by game_date rows between unbounded preceding and current row) as running_consensus_total_wins,
        sum(is_market_game) over (partition by team_name, season order by game_date rows between unbounded preceding and current row) as running_market_games,
        
        -- Rolling Average Total Points
        avg(points_scored + points_allowed) over (partition by team_name, season order by game_date rows between unbounded preceding and current row) as running_avg_total_points
    from game_performance
)

select
    md5(game_date || team_name) as team_game_id,
    game_id,
    md5(cast(game_date as varchar)) as date_id,
    md5(team_name) as team_id,
    team_name,
    season,
    game_date,
    team_location,
    points_scored,
    points_allowed,
    points_scored - points_allowed as point_differential,
    is_win,
    is_loss,
    is_tie,
    is_ats_win,
    is_ats_loss,
    is_ats_push,
    is_over,
    is_under,
    is_total_push,
    was_consensus_spread_correct,
    was_consensus_total_correct,
    
    -- Win/Loss Running
    round((running_wins + 0.5 * running_ties) / running_games_played, 3) as running_win_percentage,
    cast(running_wins as varchar) || '-' || cast(running_losses as varchar) || '-' || cast(running_ties as varchar) as running_record,
    
    -- ATS Running
    round((running_ats_wins + 0.5 * running_ats_pushes) / nullif(running_ats_wins + running_ats_losses + running_ats_pushes, 0), 3) as running_ats_win_percentage,
    cast(running_ats_wins as varchar) || '-' || cast(running_ats_losses as varchar) || '-' || cast(running_ats_pushes as varchar) as running_ats_record,
    
    -- Over/Under Running
    round((running_overs + 0.5 * running_total_pushes) / nullif(running_overs + running_unders + running_total_pushes, 0), 3) as running_over_percentage,
    cast(running_overs as varchar) || '-' || cast(running_unders as varchar) || '-' || cast(running_total_pushes as varchar) as running_over_under_record,
    
    -- Consensus Market Performance Running
    round(running_consensus_spread_wins / nullif(running_market_games, 0), 3) as running_consensus_spread_win_percentage,
    round(running_consensus_total_wins / nullif(running_market_games, 0), 3) as running_consensus_total_win_percentage,
    running_market_games as games_with_market,

    -- Rolling Point Totals
    round(running_avg_total_points, 2) as running_avg_total_points

from running_totals
