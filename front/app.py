import os

import requests
import streamlit as st
from dotenv import load_dotenv
from streamlit_searchbox import st_searchbox


# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------

load_dotenv()

API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")

PAGE_TEAM = "team"
PAGE_PLAYER = "player"


# -----------------------------------------------------------------------------
# Appels API
# -----------------------------------------------------------------------------

def search_teams(search: str):
    if not search or len(search) < 3:
        return []

    response = requests.get(f"{API_BASE_URL}/teams/{search}")
    response.raise_for_status()

    return [
        {"id": team["team_id"], "name": team["team_name"]}
        for team in response.json()["teams"]
    ]


def get_team(team_id: int):
    response = requests.get(f"{API_BASE_URL}/team/{team_id}")
    response.raise_for_status()
    return response.json()


# -----------------------------------------------------------------------------
# Navigation
# -----------------------------------------------------------------------------

def set_page(page_name: str):
    st.session_state["page"] = page_name
    st.rerun()


def go_to_player_page(player: dict):
    st.session_state["selected_player"] = player
    set_page(PAGE_PLAYER)


# -----------------------------------------------------------------------------
# Composants d'affichage
# -----------------------------------------------------------------------------

def show_team_header(team: dict):
    st.markdown(
        f"""
        <div style="text-align:center; margin: 2rem 0;">
            <h2>{team["team_name"]}</h2>
            <p>Formation : {team["formation"]}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def show_players_block(title: str, players: list[dict]):
    st.subheader(title)

    if not players:
        st.info("Aucun joueur.")
        return

    header = st.columns([4, 3, 2])
    header[0].markdown("**Joueur**")
    header[1].markdown("**Poste**")
    header[2].markdown("**Note**")

    for player in players:
        columns = st.columns([4, 3, 2])
        if columns[0].button(player["player_name"], key=f"player_{player['player_id']}"):
            go_to_player_page(player)
        columns[1].write(player["position"])
        columns[2].write(player["global_note"])


# -----------------------------------------------------------------------------
# Page équipe
# -----------------------------------------------------------------------------

def show_team_page():
    st.title("Football Predictor")

    selected_team = st_searchbox(
        search_function=search_teams,
        placeholder="Rechercher une équipe",
        key="team_search",
        label="Équipe",
    )

    if selected_team and st.button("Valider"):
        st.session_state["team_data"] = get_team(selected_team["id"])

    team_data = st.session_state.get("team_data")
    if not team_data:
        return

    team = team_data["team"]
    players = team_data["players"]
    starters = [player for player in players if player["is_starting_match"]]
    substitutes = [player for player in players if not player["is_starting_match"]]

    show_team_header(team)
    show_players_block("Titulaires", starters)
    show_players_block("Remplaçants", substitutes)


# -----------------------------------------------------------------------------
# Page joueur
# -----------------------------------------------------------------------------

def show_player_page():
    player = st.session_state["selected_player"]

    if st.button("Retour"):
        set_page(PAGE_TEAM)

    st.title(player["player_name"])
    st.write(f"Poste : {player['position']}")
    st.write(f"Note globale : {player['global_note']}")
    st.write(f"ID joueur : {player['player_id']}")


# -----------------------------------------------------------------------------
# Router
# -----------------------------------------------------------------------------

ROUTES = {
    PAGE_TEAM: show_team_page,
    PAGE_PLAYER: show_player_page,
}

current_page = st.session_state.get("page", PAGE_TEAM)
page_function = ROUTES.get(current_page, show_team_page)
page_function()
