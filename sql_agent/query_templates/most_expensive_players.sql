SELECT
    player_name,
    best_position,
    COALESCE(transfermarkt_market_value_eur, sofifa_value_eur) AS player_value_eur,
    overall_rating
FROM player
WHERE COALESCE(transfermarkt_market_value_eur, sofifa_value_eur) IS NOT NULL
ORDER BY player_value_eur DESC NULLS LAST, overall_rating DESC NULLS LAST, player_name
LIMIT 10
