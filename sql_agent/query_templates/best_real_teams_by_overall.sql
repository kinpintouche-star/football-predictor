SELECT
    team_name,
    overall,
    attack,
    midfield,
    defence,
    uefa_rank
FROM team
WHERE overall IS NOT NULL
ORDER BY overall DESC NULLS LAST, uefa_rank ASC NULLS LAST, team_name
LIMIT 10
