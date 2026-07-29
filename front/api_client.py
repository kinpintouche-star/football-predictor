"""Client API des pages Fantasy.

Ce module sert la création d'équipe custom et les pages tournoi.

Il n'y a plus de jeu de données inventé ni d'interrupteur USE_MOCK_API. Chaque
appel part vers l'API dès qu'un endpoint existe, et ce qui reste local est
identifié comme tel, avec sa raison.

Ce qui passe par l'API ( api_football_predictor/app/routes.py ) :

    POST   /custom/team             create_team
    GET    /player/{player_id}      get_player
    POST   /players                 fetch_players
    POST   /teams                   search teams réelles + custom
    GET    /team/{team_id}/prediction_features
    POST   /custom/tournament       create_tournament
    POST   /custom/tournament/set   set_tournament

Ce qui reste local :

* `get_compos` : les compos de référence sont des constantes d'interface, pas
  une donnée. Elles n'ont rien à faire en base et restent ici ;
* `list_custom_teams` / `delete_custom_team` : ni GET ni DELETE sur
  custom_team. La liste affichée est celle des équipes créées pendant la
  session, alimentée par la réponse du POST. Conséquence à connaitre : une
  équipe retirée ici disparait de l'écran mais reste en base ;
* `get_tournament` / `list_tournaments` : pas de GET sur tournament.

Les endpoints qui lèveraient ces limites sont listés dans front/README.md.
"""

from __future__ import annotations

import os
import unicodedata

import requests
import streamlit as st

API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
PREDICT_API_BASE_URL = os.getenv("PREDICT_API_BASE_URL", "http://127.0.0.1:4000").rstrip("/")

TIMEOUT_SECONDS = 30

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

    # Une 500 est une panne côté API, mais si l'API fournit un détail propre
    # on l'affiche : c'est utile pour les soucis de schéma Neon.
    if response.status_code >= 500:
        try:
            detail = response.json().get("detail", response.text)
        except ValueError:
            detail = response.text

        raise ApiError(_detail_message(detail))

    response.raise_for_status()
    return response.json()


# -----------------------------------------------------------------------------
# Compos - local, constantes d'interface
# -----------------------------------------------------------------------------

def get_compos() -> list[dict]:
    return [{"compo_ref": name, "lines": lines} for name, lines in COMPOS.items()]


# -----------------------------------------------------------------------------
# Catalogue joueurs - API
# -----------------------------------------------------------------------------

@st.cache_data(show_spinner=False)
def get_players(line: str | None = None, search: str | None = None) -> list[dict]:
    params = {"limit": 500}

    if line:
        params["line"] = line

    if search and search.strip():
        params["search"] = search.strip()

    return _request("GET", "/players", params=params)["players"]


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
    """
    return _request("GET", f"/team/{team_id}")["players"]


# -----------------------------------------------------------------------------
# Joueurs - API
# -----------------------------------------------------------------------------

def get_player(player_id: int) -> dict:
    """Fiche détaillée d'un joueur, statistiques SoFIFA comprises."""
    return _request("GET", f"/player/{player_id}")["player"]


def fetch_players(player_ids: list[int]) -> list[dict]:
    """Détail de joueurs déjà identifiés."""
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

    players = []
    for player in response.get("players", []):
        players.append(
            {
                "player_id": player["player_id"],
                "player_name": player["player_name"],
                "best_position": player.get("position"),
                "note": player.get("overall_rating"),
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


def get_prediction_features(team_id: str) -> dict:
    return _request("GET", f"/team/{team_id}/prediction_features")


def predict_match(team_id_1: str, team_id_2: str) -> int:
    """Prédit le résultat du point de vue de l'équipe 1."""
    team_1 = get_prediction_features(team_id_1)
    team_2 = get_prediction_features(team_id_2)
    payload = {}

    for team_number, notes in [(1, team_1["notes"]), (2, team_2["notes"])]:
        for player_number, note in enumerate(notes, start=1):
            payload[f"team_{team_number}_player_{player_number}_note"] = note

    try:
        response = requests.post(
            f"{PREDICT_API_BASE_URL}/predict",
            json=payload,
            timeout=60,
        )
    except requests.RequestException as error:
        raise ApiError(f"API prediction injoignable : {error}") from error

    if response.status_code >= 400:
        raise ApiError(response.text)

    return response.json()["match_score_predict"]


def normalize_text(value: str) -> str:
    value = unicodedata.normalize("NFKD", value)
    value = value.encode("ascii", "ignore").decode("ascii")
    return value.lower()


@st.cache_data(show_spinner=False, ttl=120)
def list_tournament_candidate_teams() -> list[dict]:
    """Équipes utilisables en tournoi.

    L'API fait le filtrage en SQL pour éviter de tester les équipes une par une.
    """
    response = _request(
        "POST",
        "/teams",
        json={"search": "", "custom": True, "prediction_ready": True, "limit": 1000},
    )

    return [
        {
            "team_id": str(team["team_id"]),
            "team_name": team["team_name"],
            "team_type": team.get("team_type"),
            "overall": team.get("overall"),
            "attack": team.get("attack"),
            "midfield": team.get("midfield"),
            "defence": team.get("defence"),
        }
        for team in response["teams"]
    ]


def search_tournament_candidate_teams(search: str) -> list[tuple[str, dict]]:
    if not search or len(search) < 3:
        return []

    search_value = normalize_text(search)
    teams = [
        team
        for team in list_tournament_candidate_teams()
        if search_value in normalize_text(team["team_name"])
    ][:20]

    return [(team["team_name"], team) for team in teams]


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
