WITH search AS (
    SELECT 'mbappe' AS searched_name
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
    player_id,
    player_name,
    full_name,
    nationality,
    best_position,
    positions,
    current_club_name,
    overall_rating,
    potential,
    COALESCE(transfermarkt_market_value_eur, sofifa_value_eur) AS player_value_eur,
    preferred_foot,
    weak_foot,
    skill_moves,
    height_cm,
    weight_kg
FROM player, normalized_search
WHERE LOWER(TRANSLATE(
    COALESCE(player_name, '') || ' ' || COALESCE(full_name, ''),
    'áàâäãåéèêëíìîïóòôöõúùûüçñýÿÁÀÂÄÃÅÉÈÊËÍÌÎÏÓÒÔÖÕÚÙÛÜÇÑÝŸ',
    'aaaaaaeeeeiiiiooooouuuucnyyAAAAAAEEEEIIIIOOOOOUUUUCNYY'
)) LIKE '%' || normalized_search.searched_name || '%'
ORDER BY overall_rating DESC NULLS LAST, player_name
LIMIT 20
