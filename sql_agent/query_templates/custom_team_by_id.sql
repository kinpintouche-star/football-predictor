WITH search AS (
    SELECT 'c123456789abc' AS searched_custom_team_id
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
JOIN search ON search.searched_custom_team_id = ct.custom_team_id
GROUP BY
    ct.custom_team_id,
    ct.team_name,
    ct.reference_formation,
    ct.budget_eur,
    ct.overall,
    ct.attack,
    ct.midfield,
    ct.defence
