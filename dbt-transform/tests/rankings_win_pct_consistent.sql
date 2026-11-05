-- Gold final_win_percentage must equal (wins + 0.5*ties) / played games,
-- recomputed from team performance. Catches denominator dilution.
with agg as (
    select
        team_name, season,
        sum(is_win) as w, sum(is_loss) as l, sum(is_tie) as t, count(*) as gp
    from {{ ref('fct_nfl_team_performance') }}
    group by 1, 2
)
select r.team_name, r.season, r.final_win_percentage, (a.w + 0.5 * a.t) / a.gp as expected
from {{ ref('analytics_nfl_team_rankings') }} r
join agg a on a.team_name = r.team_name and a.season = r.season
where abs(r.final_win_percentage - (a.w + 0.5 * a.t) / a.gp) > 0.001
   or r.total_games_played != a.gp
