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
    CASE
        WHEN st.winner_team_id IS NULL THEN 'en_cours'
        ELSE 'termine'
    END AS tournament_status
FROM selected_tournament st
LEFT JOIN custom_team winner_ct ON winner_ct.custom_team_id = st.winner_team_id
LEFT JOIN team winner_t ON winner_t.team_id::text = st.winner_team_id
