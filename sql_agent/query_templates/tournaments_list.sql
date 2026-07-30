SELECT
    t.tournament_id,
    t.tournament_name,
    t.nb_teams,
    t.winner_team_id,
    COALESCE(winner_ct.team_name, winner_t.team_name) AS winner_team_name,
    CASE
        WHEN t.winner_team_id IS NULL THEN 'en_cours'
        ELSE 'termine'
    END AS tournament_status,
    COUNT(DISTINCT tt.custom_team_id) AS registered_team_count,
    COUNT(DISTINCT cm.custom_match_id) AS played_match_count
FROM tournament t
LEFT JOIN tournament_team tt ON tt.tournament_id = t.tournament_id
LEFT JOIN custom_match cm ON cm.tournament_id = t.tournament_id
LEFT JOIN custom_team winner_ct ON winner_ct.custom_team_id = t.winner_team_id
LEFT JOIN team winner_t ON winner_t.team_id::text = t.winner_team_id
GROUP BY
    t.tournament_id,
    t.tournament_name,
    t.nb_teams,
    t.winner_team_id,
    COALESCE(winner_ct.team_name, winner_t.team_name)
ORDER BY t.tournament_id DESC
LIMIT 50
