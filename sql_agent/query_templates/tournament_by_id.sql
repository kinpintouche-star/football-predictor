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
    tt.slot_index,
    tt.custom_team_id AS team_id,
    COALESCE(ct.team_name, real_t.team_name) AS team_name,
    CASE
        WHEN ct.custom_team_id IS NOT NULL THEN 'custom'
        ELSE 'real'
    END AS team_type,
    tt.nb_wins,
    tt.nb_loss,
    tt.nb_equal
FROM selected_tournament st
LEFT JOIN custom_team winner_ct ON winner_ct.custom_team_id = st.winner_team_id
LEFT JOIN team winner_t ON winner_t.team_id::text = st.winner_team_id
LEFT JOIN tournament_team tt ON tt.tournament_id = st.tournament_id
LEFT JOIN custom_team ct ON ct.custom_team_id = tt.custom_team_id
LEFT JOIN team real_t ON real_t.team_id::text = tt.custom_team_id
ORDER BY tt.slot_index NULLS LAST, team_name
