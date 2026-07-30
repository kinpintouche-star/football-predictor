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
)
SELECT
    ct.custom_team_id,
    ct.team_name,
    ct.reference_formation,
    ct.budget_eur,
    ct.overall,
    ct.attack,
    ct.midfield,
    ct.defence,
    COUNT(ctp.player_id) AS player_count,
    SUM(COALESCE(p.transfermarkt_market_value_eur, p.sofifa_value_eur)) AS total_player_value_eur
FROM custom_team ct
LEFT JOIN custom_team_player ctp ON ctp.custom_team_id = ct.custom_team_id
LEFT JOIN player p ON p.player_id = ctp.player_id
JOIN normalized_search ns ON LOWER(TRANSLATE(
    ct.team_name,
    'áàâäãåéèêëíìîïóòôöõúùûüçñýÿÁÀÂÄÃÅÉÈÊËÍÌÎÏÓÒÔÖÕÚÙÛÜÇÑÝŸ',
    'aaaaaaeeeeiiiiooooouuuucnyyAAAAAAEEEEIIIIOOOOOUUUUCNYY'
)) LIKE '%' || ns.searched_name || '%'
GROUP BY
    ct.custom_team_id,
    ct.team_name,
    ct.reference_formation,
    ct.budget_eur,
    ct.overall,
    ct.attack,
    ct.midfield,
    ct.defence
ORDER BY ct.overall DESC NULLS LAST, ct.team_name
LIMIT 20
