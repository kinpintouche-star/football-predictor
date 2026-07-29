SELECT
    team_name,
    uefa_rank,
    overall,
    attack,
    midfield,
    defence
FROM team
WHERE uefa_rank IS NOT NULL
ORDER BY uefa_rank ASC NULLS LAST, overall DESC NULLS LAST, team_name
LIMIT 10
