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
selected_real_team AS (
    SELECT team_id::text AS team_id, team_name
    FROM team, normalized_search
    WHERE LOWER(TRANSLATE(
        team_name,
        'áàâäãåéèêëíìîïóòôöõúùûüçñýÿÁÀÂÄÃÅÉÈÊËÍÌÎÏÓÒÔÖÕÚÙÛÜÇÑÝŸ',
        'aaaaaaeeeeiiiiooooouuuucnyyAAAAAAEEEEIIIIOOOOOUUUUCNYY'
    )) LIKE '%' || normalized_search.searched_name || '%'
    ORDER BY uefa_rank ASC NULLS LAST, overall DESC NULLS LAST, team_name
    LIMIT 1
),
selected_custom_team AS (
    SELECT custom_team_id AS team_id, team_name
    FROM custom_team, normalized_search
    WHERE LOWER(TRANSLATE(
        team_name,
        'áàâäãåéèêëíìîïóòôöõúùûüçñýÿÁÀÂÄÃÅÉÈÊËÍÌÎÏÓÒÔÖÕÚÙÛÜÇÑÝŸ',
        'aaaaaaeeeeiiiiooooouuuucnyyAAAAAAEEEEIIIIOOOOOUUUUCNYY'
    )) LIKE '%' || normalized_search.searched_name || '%'
    ORDER BY overall DESC NULLS LAST, team_name
    LIMIT 1
)
SELECT
    srt.team_name,
    'real' AS team_type,
    p.player_id,
    p.player_name,
    p.best_position,
    p.overall_rating,
    COALESCE(p.transfermarkt_market_value_eur, p.sofifa_value_eur) AS player_value_eur,
    COUNT(DISTINCT l.match_id) AS matches_found,
    SUM(COALESCE(l.minutes_played, 0)) AS minutes_found
FROM selected_real_team srt
JOIN lineup l ON l.team_id::text = srt.team_id
JOIN player p ON p.player_id = l.player_id
GROUP BY
    srt.team_name,
    p.player_id,
    p.player_name,
    p.best_position,
    p.overall_rating,
    COALESCE(p.transfermarkt_market_value_eur, p.sofifa_value_eur)

UNION ALL

SELECT
    sct.team_name,
    'custom' AS team_type,
    p.player_id,
    p.player_name,
    p.best_position,
    p.overall_rating,
    COALESCE(p.transfermarkt_market_value_eur, p.sofifa_value_eur) AS player_value_eur,
    NULL AS matches_found,
    NULL AS minutes_found
FROM selected_custom_team sct
JOIN custom_team_player ctp ON ctp.custom_team_id = sct.team_id
JOIN player p ON p.player_id = ctp.player_id
ORDER BY overall_rating DESC NULLS LAST, player_name
LIMIT 100
