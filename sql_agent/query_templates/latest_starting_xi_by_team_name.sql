WITH search AS (
    SELECT 'barcelona' AS searched_name
),
normalized_search AS (
    SELECT LOWER(TRANSLATE(
        searched_name,
        'áàâäãåéèêëíìîïóòôöõúùûüçñýÿÁÀÂÄÃÅÉÈÊËÍÌÎÏÓÒÔÖÕÚÙÛÜÇÑÝŸ',
        'aaaaaaeeeeiiiiooooouuuucnyyAAAAAAEEEEIIIIOOOOOUUUUCNYY'
    )) AS searched_name
    FROM search
),
selected_team AS (
    SELECT team_id, team_name
    FROM team, normalized_search
    WHERE LOWER(TRANSLATE(
        team_name,
        'áàâäãåéèêëíìîïóòôöõúùûüçñýÿÁÀÂÄÃÅÉÈÊËÍÌÎÏÓÒÔÖÕÚÙÛÜÇÑÝŸ',
        'aaaaaaeeeeiiiiooooouuuucnyyAAAAAAEEEEIIIIOOOOOUUUUCNYY'
    )) LIKE '%' || normalized_search.searched_name || '%'
    ORDER BY uefa_rank ASC NULLS LAST, overall DESC NULLS LAST, team_name
    LIMIT 1
),
latest_match AS (
    SELECT l.match_id
    FROM lineup l
    JOIN match m ON m.match_id = l.match_id
    JOIN selected_team st ON st.team_id = l.team_id
    GROUP BY l.match_id, m.match_date
    ORDER BY m.match_date DESC
    LIMIT 1
)
SELECT
    st.team_name,
    m.match_date,
    p.player_id,
    p.player_name,
    l.position_player,
    l.minutes_played,
    p.overall_rating
FROM latest_match lm
JOIN match m ON m.match_id = lm.match_id
JOIN lineup l ON l.match_id = lm.match_id
JOIN selected_team st ON st.team_id = l.team_id
JOIN player p ON p.player_id = l.player_id
WHERE l.is_starting_match = 1
ORDER BY l.position_player, p.player_name
