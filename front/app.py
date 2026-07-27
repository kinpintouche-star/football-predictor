import os

import plotly.graph_objects as go
import requests
import streamlit as st
from dotenv import load_dotenv
from streamlit_searchbox import st_searchbox

from player_stat_groups import PLAYER_STAT_GROUPS


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


def get_player(player_id: int):
    response = requests.get(f"{API_BASE_URL}/player/{player_id}")
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


def format_note(value):
    if value is None:
        return "-"

    value = float(value)
    if value.is_integer():
        return str(int(value))

    return str(round(value, 1))


def group_average(player: dict, stats: list[tuple[str, str]]):
    values = [
        float(player[column])
        for column, _ in stats
        if player.get(column) is not None
    ]

    if not values:
        return None

    return round(sum(values) / len(values), 1)


def get_group_scores(player: dict):
    scores = []

    for group_name, stats in PLAYER_STAT_GROUPS.items():
        average = group_average(player, stats)

        if average is not None:
            scores.append((group_name, average))

    return scores


def show_player_radar_chart(player: dict):
    st.subheader("Profil")

    scores = get_group_scores(player)
    if len(scores) < 3:
        st.info("Pas assez de statistiques pour afficher le radar.")
        return

    labels = [group_name for group_name, _ in scores]
    values = [score for _, score in scores]

    labels.append(labels[0])
    values.append(values[0])

    figure = go.Figure(
        data=[
            go.Scatterpolar(
                r=values,
                theta=labels,
                fill="toself",
                line_color="#16a34a",
                fillcolor="rgba(22, 163, 74, 0.25)",
            )
        ]
    )

    figure.update_layout(
        height=420,
        margin=dict(l=30, r=30, t=20, b=20),
        showlegend=False,
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 100],
            )
        ),
    )

    st.plotly_chart(figure, use_container_width=True, config={"displayModeBar": False})


def show_player_stat_groups(player: dict):
    st.subheader("Statistiques")

    for group_name, stats in PLAYER_STAT_GROUPS.items():
        available_stats = [
            (column, label)
            for column, label in stats
            if player.get(column) is not None
        ]

        if not available_stats:
            continue

        average = group_average(player, available_stats)

        with st.expander(f"{group_name} - moyenne {format_note(average)}", expanded=True):
            columns = st.columns(2)

            for index, (column, label) in enumerate(available_stats):
                columns[index % 2].write(f"{label} : {format_note(player[column])}")


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
    selected_player = st.session_state["selected_player"]

    if st.button("Retour"):
        set_page(PAGE_TEAM)

    player = get_player(selected_player["player_id"])["player"]

    st.title(player["player_name"])
    st.write(f"Poste : {player['best_position']}")
    st.write(f"Note globale : {player['global_note']}")

    stats_column, radar_column = st.columns([3, 2])

    with stats_column:
        show_player_stat_groups(player)

    with radar_column:
        show_player_radar_chart(player)


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
