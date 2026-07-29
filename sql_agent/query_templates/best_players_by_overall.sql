SELECT
    player_name,
    best_position,
    overall_rating,
    COALESCE(transfermarkt_market_value_eur, sofifa_value_eur) AS player_value_eur
FROM player
WHERE overall_rating IS NOT NULL
ORDER BY overall_rating DESC NULLS LAST, player_name
LIMIT 10
