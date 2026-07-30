WITH selected_tournament AS (
    SELECT tournament_id, tournament_name, nb_teams, winner_team_id
    FROM tournament
    WHERE tournament_id = 't123456789abc'
)
SELECT
    st.tournament_id,
    st.tournament_name,
    st.nb_teams,
    st.winner_team_id,
    COALESCE(winner_ct.team_name, winner_t.team_name) AS winner_team_name,
    CASE
        WHEN st.winner_team_id IS NULL THEN 'en_cours'
        ELSE 'termine'
    END AS tournament_status
FROM selected_tournament st
LEFT JOIN custom_team winner_ct ON winner_ct.custom_team_id = st.winner_team_id
LEFT JOIN team winner_t ON winner_t.team_id::text = st.winner_team_id
