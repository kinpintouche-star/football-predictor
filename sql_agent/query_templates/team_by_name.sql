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
)
SELECT
    team_id::text AS team_id,
    team_name,
    'real' AS team_type,
    uefa_rank,
    overall,
    attack,
    midfield,
    defence
FROM team, normalized_search
WHERE LOWER(TRANSLATE(
    team_name,
    'áàâäãåéèêëíìîïóòôöõúùûüçñýÿÁÀÂÄÃÅÉÈÊËÍÌÎÏÓÒÔÖÕÚÙÛÜÇÑÝŸ',
    'aaaaaaeeeeiiiiooooouuuucnyyAAAAAAEEEEIIIIOOOOOUUUUCNYY'
)) LIKE '%' || normalized_search.searched_name || '%'

UNION ALL

SELECT
    custom_team_id AS team_id,
    team_name,
    'custom' AS team_type,
    NULL AS uefa_rank,
    overall,
    attack,
    midfield,
    defence
FROM custom_team, normalized_search
WHERE LOWER(TRANSLATE(
    team_name,
    'áàâäãåéèêëíìîïóòôöõúùûüçñýÿÁÀÂÄÃÅÉÈÊËÍÌÎÏÓÒÔÖÕÚÙÛÜÇÑÝŸ',
    'aaaaaaeeeeiiiiooooouuuucnyyAAAAAAEEEEIIIIOOOOOUUUUCNYY'
)) LIKE '%' || normalized_search.searched_name || '%'
ORDER BY team_type, uefa_rank ASC NULLS LAST, overall DESC NULLS LAST, team_name
LIMIT 20
