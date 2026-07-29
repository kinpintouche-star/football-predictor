WITH search AS (
    SELECT 'jedha' AS searched_name
),
normalized_search AS (
    SELECT LOWER(TRANSLATE(
        searched_name,
        'áàâäãåéèêëíìîïóòôöõúùûüçñýÿÁÀÂÄÃÅÉÈÊËÍÌÎÏÓÒÔÖÕÚÙÛÜÇÑÝŸ',
        'aaaaaaeeeeiiiiooooouuuucnyyAAAAAAEEEEIIIIOOOOOUUUUCNYY'
    )) AS searched_name
    FROM search
),
selected_custom_team AS (
    SELECT custom_team_id, team_name, reference_formation, budget_eur
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
    sct.team_name,
    sct.reference_formation,
    sct.budget_eur,
    p.player_id,
    p.player_name,
    p.best_position,
    p.overall_rating,
    COALESCE(p.transfermarkt_market_value_eur, p.sofifa_value_eur) AS player_value_eur
FROM selected_custom_team sct
JOIN custom_team_player ctp ON ctp.custom_team_id = sct.custom_team_id
JOIN player p ON p.player_id = ctp.player_id
ORDER BY p.overall_rating DESC NULLS LAST, p.player_name
