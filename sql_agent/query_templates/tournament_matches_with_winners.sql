SELECT
    t.tournament_name,
    cm.tournament_phase,
    COALESCE(home_ct.team_name, home_t.team_name) AS home_team_name,
    cm.home_score,
    cm.away_score,
    COALESCE(away_ct.team_name, away_t.team_name) AS away_team_name,
    COALESCE(winner_ct.team_name, winner_t.team_name) AS winner_team_name,
    cm.created_at
FROM custom_match cm
JOIN tournament t ON t.tournament_id = cm.tournament_id
LEFT JOIN custom_team home_ct ON home_ct.custom_team_id = cm.home_custom_team_id
LEFT JOIN team home_t ON home_t.team_id::text = cm.home_custom_team_id
LEFT JOIN custom_team away_ct ON away_ct.custom_team_id = cm.away_custom_team_id
LEFT JOIN team away_t ON away_t.team_id::text = cm.away_custom_team_id
LEFT JOIN custom_team winner_ct ON winner_ct.custom_team_id = cm.winner_team_id
LEFT JOIN team winner_t ON winner_t.team_id::text = cm.winner_team_id
WHERE LOWER(t.tournament_name) LIKE LOWER('%tournoi%')
ORDER BY cm.created_at, cm.custom_match_id
