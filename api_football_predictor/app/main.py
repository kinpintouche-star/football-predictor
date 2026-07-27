import unicodedata

from fastapi import FastAPI, HTTPException
from sqlalchemy import text

from app.database import get_engine

app = FastAPI()


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
# On renvoie le nom de l'équipe, compo (4 4 2...) d'après le dernier match joué ( match, et lineups du match)
# et les joueurs
# Pour chaque joueur ( lineup + player ):
# Son nom, sa note globale, son id, son poste
@app.get("/team/{team_id}")
def get_team(team_id: int):

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
        raise HTTPException(status_code=404, detail="Team not found")

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
