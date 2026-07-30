WITH search AS (
    SELECT 'tournoi' AS searched_name
),
normalized_search AS (
    SELECT LOWER(TRANSLATE(
        searched_name,
        'áàâäãåéèêëíìîïóòôöõúùûüçñýÿÁÀÂÄÃÅÉÈÊËÍÌÎÏÓÒÔÖÕÚÙÛÜÇÑÝŸ',
        'aaaaaaeeeeiiiiooooouuuucnyyAAAAAAEEEEIIIIOOOOOUUUUCNYY'
    )) AS searched_name
    FROM search
),
selected_tournament AS (
    SELECT t.tournament_id, t.tournament_name, t.nb_teams, t.winner_team_id
    FROM tournament t, normalized_search ns
    WHERE LOWER(TRANSLATE(
        t.tournament_name,
        'áàâäãåéèêëíìîïóòôöõúùûüçñýÿÁÀÂÄÃÅÉÈÊËÍÌÎÏÓÒÔÖÕÚÙÛÜÇÑÝŸ',
        'aaaaaaeeeeiiiiooooouuuucnyyAAAAAAEEEEIIIIOOOOOUUUUCNYY'
    )) LIKE '%' || ns.searched_name || '%'
    ORDER BY t.tournament_id DESC
    LIMIT 1
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
