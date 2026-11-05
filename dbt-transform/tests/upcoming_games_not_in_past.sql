-- Upcoming matchups must be in the future. A past-dated, scoreless game is a
-- stale preview row (e.g. scraped before kickoff and never updated with the
-- result), not an upcoming game.
select game_id, game_date, home_team, away_team
from {{ ref('analytics_nfl_upcoming_matchups') }}
where game_date < current_date
