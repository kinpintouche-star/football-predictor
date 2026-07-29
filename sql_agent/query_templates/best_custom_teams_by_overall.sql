SELECT
    team_name,
    overall,
    attack,
    midfield,
    defence,
    budget_eur
FROM custom_team
WHERE overall IS NOT NULL
ORDER BY overall DESC NULLS LAST, team_name
LIMIT 10
