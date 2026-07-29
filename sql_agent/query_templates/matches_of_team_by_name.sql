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
)
SELECT
    m.match_id,
    m.match_date,
    home_team.team_name AS home_team_name,
    m.home_score,
    m.away_score,
    away_team.team_name AS away_team_name,
    selected_mt.side AS selected_team_side,
    selected_mt.formation AS selected_team_formation,
    selected_mt.coach_name AS selected_team_coach
FROM selected_team st
JOIN match_team selected_mt ON selected_mt.team_id = st.team_id
JOIN match m ON m.match_id = selected_mt.match_id
JOIN match_team home_mt ON home_mt.match_id = m.match_id AND home_mt.side = 'home'
JOIN team home_team ON home_team.team_id = home_mt.team_id
JOIN match_team away_mt ON away_mt.match_id = m.match_id AND away_mt.side = 'away'
JOIN team away_team ON away_team.team_id = away_mt.team_id
ORDER BY m.match_date DESC, m.match_id DESC
LIMIT 30
