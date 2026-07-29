"""Client API de la page « Équipe custom ».

Ce module ne sert que cette page : les pages équipe, composition, joueur et
prédiction appellent l'API directement depuis app.py.

Il n'y a plus de jeu de données inventé ni d'interrupteur USE_MOCK_API. Chaque
appel part vers l'API dès qu'un endpoint existe, et ce qui reste local est
identifié comme tel, avec sa raison.

Ce qui passe par l'API ( api_football_predictor/app/routes.py ) :

    POST   /custom/team             create_team
    GET    /player/{player_id}      get_player
    POST   /players                 fetch_players
    POST   /custom/tournament       create_tournament
    POST   /custom/tournament/set   set_tournament

Ce qui reste local :

* `get_compos` : les compos de référence sont des constantes d'interface, pas
  une donnée. Elles n'ont rien à faire en base et restent ici ;
* `get_players` : l'API ne sait pas parcourir le catalogue, `POST /players`
  détaille des joueurs dont on connait déjà les identifiants. La sélection
  s'appuie donc sur players_catalogue.json. Ce ne sont pas des données
  inventées mais un extrait de la table `player` ( 240 joueurs ) : chaque
  `note` est la note du modèle et chaque `price` la valeur Transfermarkt,
  identiques à la base. Un `GET /players?line=&search=` le remplacerait tel
  quel ;
* `list_custom_teams` / `delete_custom_team` : ni GET ni DELETE sur
  custom_team. La liste affichée est celle des équipes créées pendant la
  session, alimentée par la réponse du POST. Conséquence à connaitre : une
  équipe retirée ici disparait de l'écran mais reste en base ;
* `get_tournament` / `list_tournaments` : pas de GET sur tournament.

Les endpoints qui lèveraient ces limites sont listés dans front/README.md.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import requests
import streamlit as st

API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")

TIMEOUT_SECONDS = 30

CATALOGUE_PATH = Path(__file__).parent / "players_catalogue.json"

DEFAULT_BUDGET_EUR = 500_000_000

# Compos de référence. Chaque ligne indique combien de joueurs sont attendus,
# gardien inclus : le total fait toujours 11.
COMPOS = {
    "4-4-2": {"GK": 1, "DEF": 4, "MID": 4, "FWD": 2},
    "4-3-3": {"GK": 1, "DEF": 4, "MID": 3, "FWD": 3},
    "4-2-3-1": {"GK": 1, "DEF": 4, "MID": 5, "FWD": 1},
    "3-5-2": {"GK": 1, "DEF": 3, "MID": 5, "FWD": 2},
    "5-3-2": {"GK": 1, "DEF": 5, "MID": 3, "FWD": 2},
    "3-4-3": {"GK": 1, "DEF": 3, "MID": 4, "FWD": 3},
}


class ApiError(RuntimeError):
    """Erreur renvoyée par l'API, ou API injoignable."""


# -----------------------------------------------------------------------------
# Transport
# -----------------------------------------------------------------------------

def _detail_message(payload) -> str:
    """Aplatit le champ `detail` de FastAPI, tantôt une chaine, tantôt un objet
    { message, player_ids }, tantôt une liste d'erreurs de validation."""
    if isinstance(payload, str):
        return payload

    if isinstance(payload, dict):
        message = payload.get("message") or payload.get("msg")
        extras = [
            ", ".join(str(item) for item in value)
            for key, value in payload.items()
            if key not in ("message", "msg") and isinstance(value, list)
        ]

        if message and extras:
            return f"{message} ({'; '.join(extras)})"

        return message or str(payload)

    if isinstance(payload, list):
        return " ; ".join(_detail_message(item) for item in payload)

    return str(payload)


def _request(method: str, path: str, **kwargs):
    try:
        response = requests.request(
            method, f"{API_BASE_URL}{path}", timeout=TIMEOUT_SECONDS, **kwargs
        )
    except requests.RequestException as error:
        raise ApiError(f"API injoignable : {error}") from error

    # 400/404/409/422 portent une règle métier : on les remonte telles quelles
    # pour que la page les affiche.
    if response.status_code in (400, 404, 409, 422):
        try:
            detail = response.json().get("detail", response.text)
        except ValueError:
            detail = response.text
        raise ApiError(_detail_message(detail))

    # Une 500 est une panne côté API : la trace brute n'aide pas l'utilisateur.
    if response.status_code >= 500:
        raise ApiError(
            f"Erreur interne de l'API ({response.status_code}) sur {method} {path}"
        )

    response.raise_for_status()
    return response.json()


# -----------------------------------------------------------------------------
# Compos - local, constantes d'interface
# -----------------------------------------------------------------------------

def get_compos() -> list[dict]:
    return [{"compo_ref": name, "lines": lines} for name, lines in COMPOS.items()]


# -----------------------------------------------------------------------------
# Catalogue joueurs - local, en attente d'un GET /players
# -----------------------------------------------------------------------------

@st.cache_data(show_spinner=False)
def _load_catalogue() -> list[dict]:
    return json.loads(CATALOGUE_PATH.read_text(encoding="utf-8"))


def get_players(line: str | None = None, search: str | None = None) -> list[dict]:
    players = _load_catalogue()

    if line:
        players = [player for player in players if player["line"] == line]

    if search and search.strip():
        needle = search.strip().lower()
        players = [
            player for player in players if needle in player["player_name"].lower()
        ]

    return sorted(players, key=lambda player: -player["price"])


def get_catalogue_player(player_id: int) -> dict | None:
    return next(
        (player for player in _load_catalogue() if player["player_id"] == player_id),
        None,
    )


# -----------------------------------------------------------------------------
# Équipes réelles - API, utilisées comme modèle de départ
# -----------------------------------------------------------------------------

def search_teams(search: str) -> list[tuple[str, dict]]:
    """Recherche d'équipe pour le bouton « Fill ».

    Le résultat est une liste de couples ( libellé, valeur ) : st_searchbox
    affiche `str()` de chaque élément reçu, donc une liste de dictionnaires
    ferait apparaitre « {'id': 418, 'name': 'Real Madrid'} » dans la liste
    déroulante. Le couple lui donne le nom à afficher et nous rend le
    dictionnaire.

    À basculer sur `POST /teams` quand il existera, voir README.
    """
    if not search or len(search) < 3:
        return []

    teams = _request("GET", f"/teams/{search}")["teams"]

    return [
        (team["team_name"], {"id": team["team_id"], "name": team["team_name"]})
        for team in teams
    ]


def get_team_squad(team_id: int) -> list[dict]:
    """Effectif de la saison d'une équipe réelle, trié par note décroissante.

    C'est la seule source qui porte à la fois une note et une valeur marchande
    par joueur, donc la seule utilisable pour pré-remplir une compo avec son
    budget. `GET /team/{id}/lineup` donnerait le vrai onze du dernier match,
    mais sans aucun prix.

    Attention : `global_note` est ici overall_rating, alors que la note du
    catalogue est celle du modèle ( moyenne des groupes de statistiques de
    champ ). Les deux ne sont pas comparables, voir normalize_squad_player
    dans custom_team_page.
    """
    return _request("GET", f"/team/{team_id}")["players"]


# -----------------------------------------------------------------------------
# Joueurs - API
# -----------------------------------------------------------------------------

def get_player(player_id: int) -> dict:
    """Fiche détaillée d'un joueur, statistiques SoFIFA comprises."""
    return _request("GET", f"/player/{player_id}")["player"]


def fetch_players(player_ids: list[int]) -> list[dict]:
    """Détail de joueurs déjà identifiés. Ne sert pas à parcourir le catalogue."""
    if not player_ids:
        return []

    return _request("POST", "/players", json={"player_ids": player_ids})["players"]


# -----------------------------------------------------------------------------
# Équipes custom - création par l'API, relecture en session
# -----------------------------------------------------------------------------

def _created_teams() -> dict:
    """Équipes créées pendant la session. Ce n'est pas un cache de la base :
    sans GET /custom/teams, c'est la seule façon de réafficher une équipe
    après l'avoir enregistrée."""
    return st.session_state.setdefault("created_custom_teams", {})


def create_team(
    name: str,
    compo_ref: str,
    player_ids: list[int],
    budget: int | None = DEFAULT_BUDGET_EUR,
) -> dict:
    is_budget_limited = budget is not None

    payload = {
        "team_name": name,
        "reference_formation": compo_ref,
        "isBudget": is_budget_limited,
        "players": [int(player_id) for player_id in player_ids],
    }

    if is_budget_limited:
        payload["budget"] = int(budget)

    response = _request("POST", "/custom/team", json=payload)
    team = response["team"]

    # L'API renvoie les joueurs sans note ni ligne : on complète depuis le
    # catalogue pour que la liste affiche les mêmes colonnes que le sélecteur.
    players = []
    for player in response.get("players", []):
        catalogue_player = get_catalogue_player(player["player_id"])
        players.append(
            {
                "player_id": player["player_id"],
                "player_name": player["player_name"],
                "best_position": player.get("position"),
                "note": catalogue_player["note"] if catalogue_player else None,
                "price": player.get("market_value_eur") or 0,
            }
        )

    record = {
        "custom_team_id": team["custom_team_id"],
        "team_name": team["team_name"],
        "reference_formation": team["reference_formation"],
        "budget_eur": team.get("budget_eur"),
        "spent_eur": team.get("total_cost_eur", 0),
        "overall": team.get("overall"),
        "attack": team.get("attack"),
        "midfield": team.get("midfield"),
        "defence": team.get("defence"),
        "players": players,
    }

    _created_teams()[record["custom_team_id"]] = record
    return record


def list_custom_teams() -> list[dict]:
    return list(_created_teams().values())


def delete_custom_team(custom_team_id: str) -> None:
    """Retire l'équipe de l'affichage. Il n'y a pas de DELETE côté API : la
    ligne reste en base, la page le signale à l'utilisateur."""
    _created_teams().pop(custom_team_id, None)


# -----------------------------------------------------------------------------
# Tournois - création par l'API, relecture en session
# -----------------------------------------------------------------------------

def _created_tournaments() -> dict:
    return st.session_state.setdefault("created_tournaments", {})


def create_tournament(name: str, team_ids: list[str]) -> dict:
    response = _request(
        "POST",
        "/custom/tournament",
        json={
            "tournament_name": name,
            "nb_teams": len(team_ids),
            "teams": team_ids,
        },
    )

    tournament_id = response["tournament"]["tournament_id"]
    _created_tournaments()[tournament_id] = response
    return response


def list_tournaments() -> list[dict]:
    return list(_created_tournaments().values())


def get_tournament(tournament_id: str) -> dict | None:
    return _created_tournaments().get(tournament_id)


def set_tournament(
    tournament_id: str,
    team_id_1: str,
    team_id_2: str,
    score_team_1: int,
    score_team_2: int,
    phase: str,
) -> dict:
    """Enregistre le résultat d'un match de tournoi.

    L'API raisonne en scores, pas en vainqueur : elle en déduit le résultat,
    écrit le match et les compos, et met à jour les compteurs du tournoi.
    """
    return _request(
        "POST",
        "/custom/tournament/set",
        json={
            "tournament_id": tournament_id,
            "team_id_1": team_id_1,
            "team_id_2": team_id_2,
            "score_team_1": score_team_1,
            "score_team_2": score_team_2,
            "phase": phase,
        },
    )
