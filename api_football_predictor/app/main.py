import unicodedata

from fastapi import FastAPI, HTTPException
from sqlalchemy import text

from app.database import get_engine

app = FastAPI()


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


def normalize_text(value: str) -> str:
    value = unicodedata.normalize("NFKD", value)
    value = value.encode("ascii", "ignore").decode("ascii")
    return value.lower()


@app.get("/teams/{search}")
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


@app.get("/team/{team_id}")
def get_team(team_id: int):

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
@app.get("/team/{team_id}/movements")
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
@app.get("/team/{team_id}/lineup")
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
@app.get("/player/{player_id}")
def get_player(player_id: int):

    query = text(
        """
        SELECT
            player_id,
            player_name,
            best_position,
            overall_rating AS global_note,
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
        FROM "public"."player"
        WHERE player_id = :player_id
        """
    )

    with get_engine().connect() as connection:
        row = connection.execute(query, {"player_id": player_id}).mappings().first()

    if not row:
        raise HTTPException(status_code=404, detail="Player not found")

    return {"player": dict(row)}


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


@app.get("/team/{team_id}/prediction_features")
def get_team_prediction_features(team_id: int):

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
