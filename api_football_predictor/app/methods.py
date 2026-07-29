import unicodedata
import uuid

from fastapi import HTTPException
from sqlalchemy import text

from app.database import get_engine


# Note globale d'un joueur, telle que définie à l'entrainement
# ( explore_neon_tables_with_model_training.ipynb, cellules 14 et 15 ) :
# moyenne des 6 groupes de statistiques de CHAMP. Le groupe `gardien` est
# volontairement exclu, pour garder une note comparable entre joueurs de champ.
#
# Deux conséquences, toutes deux nécessaires pour rester fidèle au modèle :
#
# 1. ce n'est PAS player.overall_rating. Un gardien est noté sur ses seules
#    statistiques de champ et tombe vers 35, alors que son overall vaut 82 ;
# 2. chaque groupe est arrondi à 1 décimale AVANT la moyenne finale, elle-même
#    arrondie. Sans ce double arrondi les valeurs ne retombent pas juste.
#
# Vérifié en rejouant X_test_dataset.json : 416 valeurs distinctes sur 416.
STAT_GROUPS = {
    "vit": ["sprint_speed", "acceleration"],
    "tir": ["finishing", "attack_position", "shot_power", "long_shots", "penalties", "volleys"],
    "pas": ["vision", "crossing", "fk_accuracy", "long_passing", "short_passing", "curve"],
    "dri": ["agility", "balance", "reactions", "composure", "ball_control", "dribbling"],
    "defense": ["interceptions", "heading_accuracy", "defensive_awareness", "standing_tackle", "sliding_tackle"],
    "phy": ["jumping", "stamina", "strength", "aggression"],
}


def _average_sql(expressions: list[str]) -> str:
    # AVG sur un ARRAY ignore les NULL, comme le .mean() de pandas.
    return "ROUND((SELECT AVG(value) FROM unnest(ARRAY[{}]) AS value), 1)".format(
        ", ".join(expressions)
    )


GLOBAL_NOTE_SQL = _average_sql(
    [
        _average_sql([f"p.{column}::numeric" for column in columns])
        for columns in STAT_GROUPS.values()
    ]
)

# Les joueurs sans profil SoFIFA étaient écartés du dataset d'entrainement.
HAS_SOFIFA_PROFILE_SQL = "COALESCE(p.has_sofifa_profile, 0) = 1"

# Le modèle attend 11 notes par équipe. À l'entrainement les titulaires étaient
# numérotés par player_id croissant ( cumcount après un tri sur
# ["match_id", "team_number", "player_id"] ), pas par note ni par poste.
# On reproduit cet ordre, sinon les features arrivent permutées.
STARTERS_PER_TEAM = 11
DEFAULT_CUSTOM_TEAM_BUDGET_EUR = 500_000_000
ATTACK_POSITIONS = {"ST", "CF", "LW", "RW"}
MIDFIELD_POSITIONS = {"CDM", "CM", "CAM", "LM", "RM"}
DEFENCE_POSITIONS = {"CB", "LB", "RB", "LWB", "RWB", "GK"}


def normalize_text(value: str) -> str:
    value = unicodedata.normalize("NFKD", value)
    value = value.encode("ascii", "ignore").decode("ascii")
    return value.lower()


def search_teams(search: str):
    query = text(
        """
        SELECT team_id, team_name
        FROM "public"."team"
        ORDER BY team_name
        """
    )

    with get_engine().connect() as connection:
        rows = connection.execute(query).mappings().all()

    search_value = normalize_text(search)
    matching_teams = [
        row
        for row in rows
        if search_value in normalize_text(row["team_name"])
    ][:20]

    return {
        "teams": [
            {
                "team_id": row["team_id"],
                "team_name": row["team_name"],
            }
            for row in matching_teams
        ]
    }


def get_teams(payload):
    # Endpoint unifié pour alimenter les recherches : équipes réelles + custom.
    search_value = normalize_text(payload.search.strip())
    limit = min(max(payload.limit, 1), 500)

    real_query = text(
        """
        SELECT
            team_id,
            team_name,
            'real' AS team_type,
            NULL AS reference_formation,
            NULL AS budget_eur,
            overall,
            attack,
            midfield,
            defence,
            uefa_rank,
            club_league_name
        FROM "public"."team"
        ORDER BY team_name
        """
    )

    custom_query = text(
        """
        SELECT
            ct.custom_team_id AS team_id,
            ct.team_name,
            'custom' AS team_type,
            ct.reference_formation,
            ct.budget_eur,
            ct.overall,
            ct.attack,
            ct.midfield,
            ct.defence,
            NULL AS uefa_rank,
            NULL AS club_league_name
        FROM "public"."custom_team" ct
        ORDER BY ct.team_name
        """
    )

    with get_engine().connect() as connection:
        teams = [dict(row) for row in connection.execute(real_query).mappings().all()]

        if payload.custom:
            teams.extend(
                dict(row) for row in connection.execute(custom_query).mappings().all()
            )

    if search_value:
        teams = [
            team for team in teams
            if search_value in normalize_text(team["team_name"])
        ]

    return {"teams": teams[:limit]}


# Fetch des données suivantes :
# Pour une équipe donnée ( recherche par id )
# On renvoie le nom de l'équipe et son effectif de la saison en cours,
# trié de la meilleure note à la moins bonne.
#
# L'effectif est reconstruit à partir des compositions ( lineup ) de la saison,
# et non depuis player.club_name : cette colonne vient d'un export SoFIFA figé
# qui contient des joueurs retraités, rate des joueurs alignés récemment,
# et est vide pour 8 des 99 équipes.
#
# Début de saison = 1er juillet précédant le dernier match connu de l'équipe,
# ce qui évite de figer une date en dur dans le code.
SEASON_START = """
    SELECT make_date(
        CASE
            WHEN EXTRACT(MONTH FROM MAX(m.match_date)) < 7
            THEN EXTRACT(YEAR FROM MAX(m.match_date))::int - 1
            ELSE EXTRACT(YEAR FROM MAX(m.match_date))::int
        END,
        7,
        1
    ) AS season_start
    FROM "public"."lineup" l
    JOIN "public"."match" m ON m.match_id = l.match_id
    WHERE l.team_id = :team_id
"""


def fetch_team_name(connection, team_id: int) -> str:
    query = text(
        """
        SELECT team_name FROM "public"."team" WHERE team_id = :team_id
        """
    )

    row = connection.execute(query, {"team_id": team_id}).mappings().first()

    if not row:
        raise HTTPException(status_code=404, detail="Team not found")

    return row["team_name"]


PLAYER_DETAIL_COLUMNS = """
    player_id,
    player_name,
    full_name,
    date_of_birth,
    nationality,
    height_cm,
    weight_kg,
    best_position,
    positions,
    overall_rating,
    overall_rating AS global_note,
    potential,
    preferred_foot,
    weak_foot,
    skill_moves,
    current_sofifa_team_id,
    current_club_name,
    sofifa_value_eur,
    transfermarkt_market_value_eur AS market_value_eur,
    transfermarkt_market_value_eur,
    has_sofifa_profile,
    crossing,
    finishing,
    heading_accuracy,
    short_passing,
    volleys,
    dribbling,
    curve,
    fk_accuracy,
    long_passing,
    ball_control,
    acceleration,
    sprint_speed,
    agility,
    reactions,
    balance,
    shot_power,
    jumping,
    stamina,
    strength,
    long_shots,
    aggression,
    interceptions,
    attack_position,
    vision,
    penalties,
    composure,
    defensive_awareness,
    standing_tackle,
    sliding_tackle,
    gk_diving,
    gk_handling,
    gk_kicking,
    gk_positioning,
    gk_reflexes
"""


def fetch_players_by_ids(connection, player_ids: list[int]):
    # Une seule requête pour un ou plusieurs joueurs.
    player_ids = list(dict.fromkeys(player_ids))

    if not player_ids:
        return []

    query = text(
        f"""
        SELECT
            {PLAYER_DETAIL_COLUMNS}
        FROM "public"."player"
        WHERE player_id = ANY(:player_ids)
        """
    )

    rows = connection.execute(query, {"player_ids": player_ids}).mappings().all()
    rows_by_id = {row["player_id"]: row for row in rows}

    return [rows_by_id[player_id] for player_id in player_ids if player_id in rows_by_id]


def average_rating(players, positions=None):
    ratings = []

    for player in players:
        if player["overall_rating"] is None:
            continue

        if positions and player["best_position"] not in positions:
            continue

        ratings.append(float(player["overall_rating"]))

    if not ratings:
        return None

    return round(sum(ratings) / len(ratings), 1)


def calculate_custom_team_ratings(players):
    overall = average_rating(players) or 0

    return {
        "overall": overall,
        "attack": average_rating(players, ATTACK_POSITIONS) or overall,
        "midfield": average_rating(players, MIDFIELD_POSITIONS) or overall,
        "defence": average_rating(players, DEFENCE_POSITIONS) or overall,
    }


def get_match_result(score_team_1: int, score_team_2: int) -> str:
    if score_team_1 > score_team_2:
        return "team_1_win"

    if score_team_1 < score_team_2:
        return "team_2_win"

    return "draw"


def set_tournament_match(
    connection,
    tournament_id: str,
    team_id_1: str,
    team_id_2: str,
    score_team_1: int,
    score_team_2: int,
    phase: str,
):
    # Règle métier complète : match + lineups + compteurs du tournoi.
    if team_id_1 == team_id_2:
        raise HTTPException(status_code=422, detail="Les deux equipes doivent etre differentes")

    if not team_id_1.startswith("c") or not team_id_2.startswith("c"):
        raise HTTPException(status_code=422, detail="Les ids des equipes doivent commencer par c")

    if score_team_1 < 0 or score_team_2 < 0:
        raise HTTPException(status_code=422, detail="Le score ne peut pas etre negatif")

    if not phase.strip():
        raise HTTPException(status_code=422, detail="phase est obligatoire")

    tournament = connection.execute(
        text(
            """
            SELECT tournament_id, tournament_name, nb_teams
            FROM "public"."tournament"
            WHERE tournament_id = :tournament_id
            """
        ),
        {"tournament_id": tournament_id},
    ).mappings().first()

    if not tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")

    team_ids = [team_id_1, team_id_2]
    teams = connection.execute(
        text(
            """
            SELECT tt.custom_team_id, ct.team_name, tt.nb_wins, tt.nb_loss, tt.nb_equal
            FROM "public"."tournament_team" tt
            JOIN "public"."custom_team" ct ON ct.custom_team_id = tt.custom_team_id
            WHERE tt.tournament_id = :tournament_id
              AND tt.custom_team_id = ANY(:team_ids)
            """
        ),
        {"tournament_id": tournament_id, "team_ids": team_ids},
    ).mappings().all()

    found_team_ids = {row["custom_team_id"] for row in teams}
    missing_team_ids = [team_id for team_id in team_ids if team_id not in found_team_ids]

    if missing_team_ids:
        raise HTTPException(
            status_code=404,
            detail={
                "message": "Certaines equipes ne sont pas dans ce tournoi",
                "team_ids": missing_team_ids,
            },
        )

    lineup_counts = connection.execute(
        text(
            """
            SELECT custom_team_id, COUNT(*) AS nb_players
            FROM "public"."custom_team_player"
            WHERE custom_team_id = ANY(:team_ids)
            GROUP BY custom_team_id
            """
        ),
        {"team_ids": team_ids},
    ).mappings().all()

    lineup_counts_by_team = {
        row["custom_team_id"]: row["nb_players"]
        for row in lineup_counts
    }
    teams_without_players = [
        team_id for team_id in team_ids if lineup_counts_by_team.get(team_id, 0) == 0
    ]

    if teams_without_players:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "Certaines equipes n'ont aucun joueur",
                "team_ids": teams_without_players,
            },
        )

    result = get_match_result(score_team_1, score_team_2)
    custom_match_id = f"c{uuid.uuid4().hex[:12]}"

    connection.execute(
        text(
            """
            INSERT INTO "public"."custom_match" (
                custom_match_id,
                home_custom_team_id,
                away_custom_team_id,
                home_score,
                away_score,
                result,
                tournament_phase,
                tournament_id
            )
            VALUES (
                :custom_match_id,
                :team_id_1,
                :team_id_2,
                :score_team_1,
                :score_team_2,
                :result,
                :phase,
                :tournament_id
            )
            """
        ),
        {
            "custom_match_id": custom_match_id,
            "team_id_1": team_id_1,
            "team_id_2": team_id_2,
            "score_team_1": score_team_1,
            "score_team_2": score_team_2,
            "result": result,
            "phase": phase.strip(),
            "tournament_id": tournament_id,
        },
    )

    connection.execute(
        text(
            """
            INSERT INTO "public"."custom_lineup" (
                custom_match_id,
                custom_team_id,
                player_id,
                is_starting_match
            )
            SELECT
                :custom_match_id,
                custom_team_id,
                player_id,
                1
            FROM "public"."custom_team_player"
            WHERE custom_team_id = ANY(:team_ids)
            """
        ),
        {"custom_match_id": custom_match_id, "team_ids": team_ids},
    )

    if result == "draw":
        connection.execute(
            text(
                """
                UPDATE "public"."tournament_team"
                SET nb_equal = nb_equal + 1
                WHERE tournament_id = :tournament_id
                  AND custom_team_id = ANY(:team_ids)
                """
            ),
            {"tournament_id": tournament_id, "team_ids": team_ids},
        )
    else:
        winner_id = team_id_1 if result == "team_1_win" else team_id_2
        loser_id = team_id_2 if result == "team_1_win" else team_id_1

        connection.execute(
            text(
                """
                UPDATE "public"."tournament_team"
                SET nb_wins = nb_wins + 1
                WHERE tournament_id = :tournament_id
                  AND custom_team_id = :winner_id
                """
            ),
            {"tournament_id": tournament_id, "winner_id": winner_id},
        )

        connection.execute(
            text(
                """
                UPDATE "public"."tournament_team"
                SET nb_loss = nb_loss + 1
                WHERE tournament_id = :tournament_id
                  AND custom_team_id = :loser_id
                """
            ),
            {"tournament_id": tournament_id, "loser_id": loser_id},
        )

    updated_teams = connection.execute(
        text(
            """
            SELECT tt.custom_team_id, ct.team_name, tt.nb_wins, tt.nb_loss, tt.nb_equal
            FROM "public"."tournament_team" tt
            JOIN "public"."custom_team" ct ON ct.custom_team_id = tt.custom_team_id
            WHERE tt.tournament_id = :tournament_id
              AND tt.custom_team_id = ANY(:team_ids)
            ORDER BY tt.custom_team_id
            """
        ),
        {"tournament_id": tournament_id, "team_ids": team_ids},
    ).mappings().all()

    return {
        "match": {
            "custom_match_id": custom_match_id,
            "tournament_id": tournament_id,
            "phase": phase.strip(),
            "team_id_1": team_id_1,
            "team_id_2": team_id_2,
            "score_team_1": score_team_1,
            "score_team_2": score_team_2,
            "result": result,
        },
        "lineup": {
            "team_id_1_players": lineup_counts_by_team[team_id_1],
            "team_id_2_players": lineup_counts_by_team[team_id_2],
        },
        "teams": [dict(row) for row in updated_teams],
    }


def create_custom_team(payload):
    player_ids = list(dict.fromkeys(payload.players))
    budget_eur = payload.budget or DEFAULT_CUSTOM_TEAM_BUDGET_EUR

    if not payload.team_name.strip():
        raise HTTPException(status_code=422, detail="team_name est obligatoire")

    if not payload.reference_formation.strip():
        raise HTTPException(status_code=422, detail="reference_formation est obligatoire")

    if budget_eur <= 0:
        raise HTTPException(status_code=422, detail="budget doit etre positif")

    if not player_ids:
        raise HTTPException(status_code=422, detail="players doit contenir au moins un joueur")

    with get_engine().begin() as connection:
        players = fetch_players_by_ids(connection, player_ids)

        found_player_ids = {row["player_id"] for row in players}
        missing_player_ids = [
            player_id for player_id in player_ids if player_id not in found_player_ids
        ]

        if missing_player_ids:
            raise HTTPException(
                status_code=404,
                detail={
                    "message": "Certains joueurs sont introuvables",
                    "player_ids": missing_player_ids,
                },
            )

        players_without_value = [
            row["player_id"] for row in players if row["market_value_eur"] is None
        ]

        if payload.isBudget and players_without_value:
            raise HTTPException(
                status_code=422,
                detail={
                    "message": "Impossible de calculer le budget pour certains joueurs",
                    "player_ids": players_without_value,
                },
            )

        total_cost_eur = int(sum(row["market_value_eur"] or 0 for row in players))
        team_ratings = calculate_custom_team_ratings(players)

        if payload.isBudget and total_cost_eur > budget_eur:
            raise HTTPException(
                status_code=422,
                detail={
                    "message": "Budget depasse",
                    "total_cost_eur": total_cost_eur,
                    "budget_eur": budget_eur,
                },
            )

        custom_team_id = f"c{uuid.uuid4().hex[:12]}"

        connection.execute(
            text(
                """
                INSERT INTO "public"."custom_team" (
                    custom_team_id,
                    team_name,
                    reference_formation,
                    budget_eur,
                    overall,
                    attack,
                    midfield,
                    defence
                )
                VALUES (
                    :custom_team_id,
                    :team_name,
                    :reference_formation,
                    :budget_eur,
                    :overall,
                    :attack,
                    :midfield,
                    :defence
                )
                """
            ),
            {
                "custom_team_id": custom_team_id,
                "team_name": payload.team_name.strip(),
                "reference_formation": payload.reference_formation.strip(),
                "budget_eur": budget_eur,
                **team_ratings,
            },
        )

        connection.execute(
            text(
                """
                INSERT INTO "public"."custom_team_player" (
                    custom_team_id,
                    player_id
                )
                VALUES (:custom_team_id, :player_id)
                """
            ),
            [
                {"custom_team_id": custom_team_id, "player_id": player_id}
                for player_id in player_ids
            ],
        )

    return {
        "team": {
            "custom_team_id": custom_team_id,
            "team_name": payload.team_name.strip(),
            "reference_formation": payload.reference_formation.strip(),
            "isBudget": payload.isBudget,
            "budget_eur": budget_eur,
            "total_cost_eur": total_cost_eur,
            "remaining_budget_eur": budget_eur - total_cost_eur,
            **team_ratings,
        },
        "players": [
            {
                "player_id": row["player_id"],
                "player_name": row["player_name"],
                "position": row["best_position"],
                "overall_rating": row["overall_rating"],
                "market_value_eur": row["market_value_eur"],
            }
            for row in players
        ],
    }


def create_tournament(payload):
    team_ids = list(dict.fromkeys(payload.teams))

    if not payload.tournament_name.strip():
        raise HTTPException(status_code=422, detail="tournament_name est obligatoire")

    if payload.nb_teams < 2:
        raise HTTPException(status_code=422, detail="nb_teams doit etre au moins egal a 2")

    if payload.nb_teams != len(team_ids):
        raise HTTPException(
            status_code=422,
            detail="nb_teams doit correspondre au nombre d'equipes envoyees",
        )

    invalid_team_ids = [team_id for team_id in team_ids if not team_id.startswith("c")]
    if invalid_team_ids:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "Les ids des equipes custom doivent commencer par c",
                "team_ids": invalid_team_ids,
            },
        )

    teams_query = text(
        """
        SELECT custom_team_id, team_name
        FROM "public"."custom_team"
        WHERE custom_team_id = ANY(:team_ids)
        """
    )

    tournament_id = f"t{uuid.uuid4().hex[:12]}"

    with get_engine().begin() as connection:
        teams = connection.execute(teams_query, {"team_ids": team_ids}).mappings().all()
        found_team_ids = {row["custom_team_id"] for row in teams}
        missing_team_ids = [
            team_id for team_id in team_ids if team_id not in found_team_ids
        ]

        if missing_team_ids:
            raise HTTPException(
                status_code=404,
                detail={
                    "message": "Certaines equipes custom sont introuvables",
                    "team_ids": missing_team_ids,
                },
            )

        connection.execute(
            text(
                """
                INSERT INTO "public"."tournament" (
                    tournament_id,
                    tournament_name,
                    nb_teams
                )
                VALUES (
                    :tournament_id,
                    :tournament_name,
                    :nb_teams
                )
                """
            ),
            {
                "tournament_id": tournament_id,
                "tournament_name": payload.tournament_name.strip(),
                "nb_teams": payload.nb_teams,
            },
        )

        connection.execute(
            text(
                """
                INSERT INTO "public"."tournament_team" (
                    tournament_id,
                    custom_team_id,
                    nb_wins,
                    nb_loss,
                    nb_equal
                )
                VALUES (
                    :tournament_id,
                    :custom_team_id,
                    0,
                    0,
                    0
                )
                """
            ),
            [
                {"tournament_id": tournament_id, "custom_team_id": team_id}
                for team_id in team_ids
            ],
        )

    teams_by_id = {row["custom_team_id"]: row for row in teams}

    return {
        "tournament": {
            "tournament_id": tournament_id,
            "tournament_name": payload.tournament_name.strip(),
            "nb_teams": payload.nb_teams,
        },
        "teams": [
            {
                "custom_team_id": team_id,
                "team_name": teams_by_id[team_id]["team_name"],
                "nb_wins": 0,
                "nb_loss": 0,
                "nb_equal": 0,
            }
            for team_id in team_ids
        ],
    }


def set_tournament(payload):
    with get_engine().begin() as connection:
        return set_tournament_match(
            connection=connection,
            tournament_id=payload.tournament_id,
            team_id_1=payload.team_id_1,
            team_id_2=payload.team_id_2,
            score_team_1=payload.score_team_1,
            score_team_2=payload.score_team_2,
            phase=payload.phase,
        )


def get_custom_team(custom_team_id: str):
    query = text(
        """
        SELECT
            ct.custom_team_id,
            ct.team_name,
            ct.reference_formation,
            ct.budget_eur,
            ct.overall,
            ct.attack,
            ct.midfield,
            ct.defence,
            p.player_id,
            p.player_name,
            p.best_position,
            p.overall_rating AS global_note,
            p.transfermarkt_market_value_eur AS market_value_eur
        FROM "public"."custom_team" ct
        LEFT JOIN "public"."custom_team_player" ctp
            ON ctp.custom_team_id = ct.custom_team_id
        LEFT JOIN "public"."player" p
            ON p.player_id = ctp.player_id
        WHERE ct.custom_team_id = :custom_team_id
        ORDER BY p.overall_rating DESC NULLS LAST, p.player_name
        """
    )

    with get_engine().connect() as connection:
        rows = connection.execute(
            query, {"custom_team_id": custom_team_id}
        ).mappings().all()

    if not rows:
        raise HTTPException(status_code=404, detail="Custom team not found")

    first_row = rows[0]

    return {
        "team": {
            "team_id": first_row["custom_team_id"],
            "custom_team_id": first_row["custom_team_id"],
            "team_type": "custom",
            "team_name": first_row["team_name"],
            "reference_formation": first_row["reference_formation"],
            "budget_eur": first_row["budget_eur"],
            "overall": first_row["overall"],
            "attack": first_row["attack"],
            "midfield": first_row["midfield"],
            "defence": first_row["defence"],
        },
        "players": [
            {
                "player_id": row["player_id"],
                "player_name": row["player_name"],
                "global_note": row["global_note"],
                "position": row["best_position"],
                "appearances": None,
                "is_new_this_season": None,
                "market_value_eur": row["market_value_eur"],
            }
            for row in rows
            if row["player_id"] is not None
        ],
    }


def get_real_team(team_id: int):

    query = text(
        f"""
        WITH season AS ({SEASON_START}),
        bounds AS (
            SELECT season_start, (season_start - INTERVAL '1 year')::date AS previous_start
            FROM season
        )
        SELECT
            p.player_id,
            p.player_name,
            p.best_position,
            p.overall_rating AS global_note,
            p.transfermarkt_market_value_eur AS market_value_eur,
            COUNT(*) FILTER (WHERE m.match_date >= bounds.season_start) AS appearances,
            NOT BOOL_OR(
                m.match_date >= bounds.previous_start
                AND m.match_date < bounds.season_start
            ) AS is_new_this_season
        FROM "public"."lineup" l
        JOIN "public"."match" m ON m.match_id = l.match_id
        JOIN "public"."player" p ON p.player_id = l.player_id
        CROSS JOIN bounds
        WHERE l.team_id = :team_id
          AND m.match_date >= bounds.previous_start
        GROUP BY p.player_id, p.player_name, p.best_position, p.overall_rating,
                 p.transfermarkt_market_value_eur
        HAVING COUNT(*) FILTER (WHERE m.match_date >= bounds.season_start) > 0
        ORDER BY global_note DESC NULLS LAST, p.player_name
        """
    )

    with get_engine().connect() as connection:
        team_name = fetch_team_name(connection, team_id)
        rows = connection.execute(query, {"team_id": team_id}).mappings().all()

    return {
        "team": {
            "team_id": team_id,
            "team_type": "real",
            "team_name": team_name,
        },
        "players": [
            {
                "player_id": row["player_id"],
                "player_name": row["player_name"],
                "global_note": row["global_note"],
                "position": row["best_position"],
                "appearances": row["appearances"],
                "is_new_this_season": row["is_new_this_season"],
                # Valeur Transfermarkt en euros. Absente pour une partie des
                # joueurs : l'interface affiche alors un tiret.
                "market_value_eur": row["market_value_eur"],
            }
            for row in rows
        ],
    }


def get_team(team_id: str):
    if team_id.startswith("c"):
        return get_custom_team(team_id)

    try:
        real_team_id = int(team_id)
    except ValueError as error:
        raise HTTPException(status_code=422, detail="team_id invalide") from error

    return get_real_team(real_team_id)


# Mouvements d'effectif entre la saison précédente et la saison en cours.
#
# Aucune source de transferts exploitable n'existe pour nos 99 équipes :
# football-data.org ne couvre que 65 d'entre elles sur son offre gratuite, et le
# dump Transfermarkt ne contient qu'une poignée de mouvements par grand club
# ( 8 lignes pour Marseille sur toute la saison 2023-24 ).
#
# On déduit donc les mouvements des feuilles de match, seule source complète :
#   arrivée = aligné cette saison, jamais la saison précédente
#   départ  = aligné la saison précédente, jamais cette saison
#
# Ce n'est pas un registre de transferts : une arrivée peut être un jeune promu
# ou un retour de prêt, un départ peut être une blessure longue ou une mise à
# l'écart. Le nombre d'apparitions est renvoyé pour que l'interface puisse
# nuancer ( un « départ » à 1 apparition ne veut pas dire grand-chose ).
def get_team_movements(team_id: int):

    query = text(
        f"""
        WITH season AS ({SEASON_START}),
        bounds AS (
            SELECT season_start, (season_start - INTERVAL '1 year')::date AS previous_start
            FROM season
        ),
        appearances AS (
            SELECT
                l.player_id,
                COUNT(*) FILTER (WHERE m.match_date >= bounds.season_start) AS current_apps,
                COUNT(*) FILTER (
                    WHERE m.match_date >= bounds.previous_start
                      AND m.match_date < bounds.season_start
                ) AS previous_apps,
                MIN(m.match_date) FILTER (WHERE m.match_date >= bounds.season_start) AS first_match,
                MAX(m.match_date) FILTER (
                    WHERE m.match_date >= bounds.previous_start
                      AND m.match_date < bounds.season_start
                ) AS last_match
            FROM "public"."lineup" l
            JOIN "public"."match" m ON m.match_id = l.match_id
            CROSS JOIN bounds
            WHERE l.team_id = :team_id
              AND m.match_date >= bounds.previous_start
            GROUP BY l.player_id
        )
        SELECT
            a.player_id,
            p.player_name,
            p.best_position,
            p.overall_rating AS global_note,
            a.current_apps,
            a.previous_apps,
            a.first_match,
            a.last_match,
            (SELECT COALESCE(SUM(previous_apps), 0) FROM appearances) AS total_previous_apps
        FROM appearances a
        JOIN "public"."player" p ON p.player_id = a.player_id
        WHERE a.current_apps = 0 OR a.previous_apps = 0
        ORDER BY p.overall_rating DESC NULLS LAST, p.player_name
        """
    )

    with get_engine().connect() as connection:
        team_name = fetch_team_name(connection, team_id)
        rows = connection.execute(query, {"team_id": team_id}).mappings().all()

    # Paris FC et Djurgardens n'ont aucun match la saison précédente dans Neon :
    # tout leur effectif ressortirait en « arrivée ». On le signale pour que
    # l'interface masque la section plutôt que d'afficher un effectif complet.
    has_previous_season = bool(rows) and rows[0]["total_previous_apps"] > 0

    def as_player(row, apps_column, date_column):
        return {
            "player_id": row["player_id"],
            "player_name": row["player_name"],
            "position": row["best_position"],
            "global_note": row["global_note"],
            "appearances": row[apps_column],
            "date": row[date_column],
        }

    return {
        "team": {
            "team_id": team_id,
            "team_name": team_name,
            "has_previous_season": has_previous_season,
        },
        "arrivals": [
            as_player(row, "current_apps", "first_match")
            for row in rows
            if row["previous_apps"] == 0
        ],
        "departures": [
            as_player(row, "previous_apps", "last_match")
            for row in rows
            if row["current_apps"] == 0
        ],
    }


# Composition du dernier match joué : la formation ( 4-4-2... ), les titulaires
# et les remplaçants.
def get_team_lineup(team_id: int):

    query = text(
        """
        WITH latest_match AS (
            SELECT
                t.team_id,
                t.team_name,
                m.match_id,
                m.match_date,
                mt.formation
            FROM "public"."team" t
            JOIN "public"."match_team" mt ON mt.team_id = t.team_id
            JOIN "public"."match" m ON m.match_id = mt.match_id
            WHERE t.team_id = :team_id
            ORDER BY m.match_date DESC, m.match_id DESC
            LIMIT 1
        )
        SELECT
            latest_match.team_id,
            latest_match.team_name,
            latest_match.match_id,
            latest_match.match_date,
            latest_match.formation,
            l.player_id,
            p.player_name,
            p.overall_rating AS global_note,
            l.position_player,
            l.is_starting_match
        FROM latest_match
        JOIN "public"."lineup" l
            ON l.match_id = latest_match.match_id
            AND l.team_id = latest_match.team_id
        JOIN "public"."player" p ON p.player_id = l.player_id
        ORDER BY l.is_starting_match DESC, l.position_player, p.player_name
        """
    )

    with get_engine().connect() as connection:
        rows = connection.execute(query, {"team_id": team_id}).mappings().all()

    if not rows:
        raise HTTPException(status_code=404, detail="Lineup not found")

    first_row = rows[0]

    return {
        "team": {
            "team_id": first_row["team_id"],
            "team_name": first_row["team_name"],
            "match_id": first_row["match_id"],
            "match_date": first_row["match_date"],
            "formation": first_row["formation"],
        },
        "players": [
            {
                "player_id": row["player_id"],
                "player_name": row["player_name"],
                "global_note": row["global_note"],
                "position": row["position_player"],
                "is_starting_match": row["is_starting_match"],
            }
            for row in rows
        ],
    }


# Fetch des données suivantes :
# Pour un joueur donné ( recherche par id )
# On renvoie ses infos principales et ses statistiques Sofifa détaillées
def get_player(player_id: int):
    with get_engine().connect() as connection:
        players = fetch_players_by_ids(connection, [player_id])

    if not players:
        raise HTTPException(status_code=404, detail="Player not found")

    return {"player": dict(players[0])}


# Fetch des données suivantes :
# Pour plusieurs joueurs donnés ( recherche par liste d'ids )
# On renvoie la même structure que get player, mais en une seule requête SQL.
def get_players(payload):
    player_ids = list(dict.fromkeys(payload.player_ids))

    if not player_ids:
        raise HTTPException(status_code=422, detail="player_ids doit contenir au moins un joueur")

    with get_engine().connect() as connection:
        players = fetch_players_by_ids(connection, player_ids)

    found_player_ids = {row["player_id"] for row in players}
    missing_player_ids = [
        player_id for player_id in player_ids if player_id not in found_player_ids
    ]

    if missing_player_ids:
        raise HTTPException(
            status_code=404,
            detail={
                "message": "Certains joueurs sont introuvables",
                "player_ids": missing_player_ids,
            },
        )

    return {"players": [dict(row) for row in players]}


# Les 11 notes à envoyer au modèle de prédiction pour une équipe.
#
# Le modèle a été entrainé sur les titulaires réels de chaque match : on part
# donc du onze du dernier match connu, la composition la plus proche de ce que
# le modèle a vu.
#
# Ce onze ne suffit pas toujours. 21 équipes sur 99 alignent au moins un joueur
# sans profil SoFIFA ( 1659 joueurs sur 6705 ), donc sans note calculable, et
# Naples, Séville ou West Ham n'en ratent qu'un seul. Plutôt que de refuser la
# prédiction, on complète avec les joueurs les mieux notés de la saison.
LAST_MATCH_STARTERS_SQL = f"""
    WITH latest_match AS (
        SELECT m.match_id, m.match_date
        FROM "public"."match_team" mt
        JOIN "public"."match" m ON m.match_id = mt.match_id
        WHERE mt.team_id = :team_id
        ORDER BY m.match_date DESC, m.match_id DESC
        LIMIT 1
    )
    SELECT
        l.player_id,
        p.player_name,
        p.best_position,
        latest_match.match_date,
        {GLOBAL_NOTE_SQL} AS global_note
    FROM latest_match
    JOIN "public"."lineup" l
        ON l.match_id = latest_match.match_id
        AND l.team_id = :team_id
    JOIN "public"."player" p ON p.player_id = l.player_id
    WHERE l.is_starting_match = 1
      AND {HAS_SOFIFA_PROFILE_SQL}
    ORDER BY l.player_id
"""

SEASON_SQUAD_BY_NOTE_SQL = f"""
    WITH season AS ({SEASON_START})
    SELECT DISTINCT
        l.player_id,
        p.player_name,
        p.best_position,
        {GLOBAL_NOTE_SQL} AS global_note
    FROM "public"."lineup" l
    JOIN "public"."match" m ON m.match_id = l.match_id
    JOIN "public"."player" p ON p.player_id = l.player_id
    CROSS JOIN season
    WHERE l.team_id = :team_id
      AND m.match_date >= season.season_start
      AND {HAS_SOFIFA_PROFILE_SQL}
    ORDER BY global_note DESC
"""


CUSTOM_TEAM_PLAYERS_BY_NOTE_SQL = f"""
    SELECT
        ct.custom_team_id,
        ct.team_name,
        ct.reference_formation,
        ctp.player_id,
        p.player_name,
        p.best_position,
        {GLOBAL_NOTE_SQL} AS global_note
    FROM "public"."custom_team" ct
    JOIN "public"."custom_team_player" ctp
        ON ctp.custom_team_id = ct.custom_team_id
    JOIN "public"."player" p
        ON p.player_id = ctp.player_id
    WHERE ct.custom_team_id = :custom_team_id
      AND {HAS_SOFIFA_PROFILE_SQL}
    ORDER BY ctp.player_id
"""


def get_real_team_prediction_features(team_id: int):

    with get_engine().connect() as connection:
        team_name = fetch_team_name(connection, team_id)
        starters = connection.execute(
            text(LAST_MATCH_STARTERS_SQL), {"team_id": team_id}
        ).mappings().all()
        squad = connection.execute(
            text(SEASON_SQUAD_BY_NOTE_SQL), {"team_id": team_id}
        ).mappings().all()

    selected = list(starters[:STARTERS_PER_TEAM])
    selected_ids = {row["player_id"] for row in selected}
    substituted = 0

    for row in squad:
        if len(selected) >= STARTERS_PER_TEAM:
            break
        if row["player_id"] not in selected_ids:
            selected.append(row)
            selected_ids.add(row["player_id"])
            substituted += 1

    if len(selected) < STARTERS_PER_TEAM:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Seulement {len(selected)} joueurs notés pour cette équipe, "
                f"{STARTERS_PER_TEAM} sont nécessaires"
            ),
        )

    # Le modèle a numéroté les titulaires par player_id croissant : même tri ici.
    selected.sort(key=lambda row: row["player_id"])

    return {
        "team": {
            "team_id": team_id,
            "team_name": team_name,
            "match_date": starters[0]["match_date"] if starters else None,
            "substituted_players": substituted,
        },
        "players": [
            {
                "player_id": row["player_id"],
                "player_name": row["player_name"],
                "position": row["best_position"],
                "global_note": float(row["global_note"]),
            }
            for row in selected
        ],
        "notes": [float(row["global_note"]) for row in selected],
    }


def get_custom_team_prediction_features(custom_team_id: str):
    with get_engine().connect() as connection:
        rows = connection.execute(
            text(CUSTOM_TEAM_PLAYERS_BY_NOTE_SQL), {"custom_team_id": custom_team_id}
        ).mappings().all()

    if not rows:
        raise HTTPException(status_code=404, detail="Custom team not found")

    if len(rows) != STARTERS_PER_TEAM:
        raise HTTPException(
            status_code=422,
            detail=(
                f"{len(rows)} joueurs notés pour cette équipe custom, "
                f"{STARTERS_PER_TEAM} sont nécessaires"
            ),
        )

    return {
        "team": {
            "team_id": rows[0]["custom_team_id"],
            "team_name": rows[0]["team_name"],
            "match_date": None,
            "formation": rows[0]["reference_formation"],
            "substituted_players": 0,
        },
        "players": [
            {
                "player_id": row["player_id"],
                "player_name": row["player_name"],
                "position": row["best_position"],
                "global_note": float(row["global_note"]),
            }
            for row in rows
        ],
        "notes": [float(row["global_note"]) for row in rows],
    }


def get_team_prediction_features(team_id: str):
    if team_id.startswith("c"):
        return get_custom_team_prediction_features(team_id)

    try:
        real_team_id = int(team_id)
    except ValueError as error:
        raise HTTPException(status_code=422, detail="team_id invalide") from error

    return get_real_team_prediction_features(real_team_id)
