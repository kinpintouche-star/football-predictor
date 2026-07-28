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

API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
PREDICT_API_BASE_URL = os.getenv("PREDICT_API_BASE_URL", "http://127.0.0.1:4000").rstrip("/")
SQL_AGENT_API_URL = os.getenv(
    "SQL_AGENT_API_URL",
    "https://8100-01kyne3htfkyrjy07tgdspdwhp.cloudspaces.litng.ai",
).rstrip("/")

PAGE_TEAM = "team"
PAGE_LINEUP = "lineup"
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


def get_team_lineup(team_id: int):
    response = requests.get(f"{API_BASE_URL}/team/{team_id}/lineup")
    response.raise_for_status()
    return response.json()


def get_team_movements(team_id: int):
    response = requests.get(f"{API_BASE_URL}/team/{team_id}/movements")
    response.raise_for_status()
    return response.json()


def get_prediction_features(team_id: int):
    response = requests.get(f"{API_BASE_URL}/team/{team_id}/prediction_features")

    if response.status_code == 422:
        raise ValueError(response.json()["detail"])

    response.raise_for_status()
    return response.json()


# Le modèle attend 22 notes nommées team_1_player_N_note / team_2_player_N_note,
# team 1 = domicile et team 2 = extérieur, comme à l'entrainement.
def predict_match(home_notes: list[float], away_notes: list[float]):
    payload = {}

    for team_number, notes in [(1, home_notes), (2, away_notes)]:
        for player_number, note in enumerate(notes, start=1):
            payload[f"team_{team_number}_player_{player_number}_note"] = note

    response = requests.post(f"{PREDICT_API_BASE_URL}/predict", json=payload, timeout=60)
    response.raise_for_status()

    return response.json()["match_score_predict"]


def get_player(player_id: int):
    response = requests.get(f"{API_BASE_URL}/player/{player_id}")
    response.raise_for_status()
    return response.json()


def ask_sql_agent(message: str):
    payload = {"message": message, "max_rows": 10}
    response = requests.post(f"{SQL_AGENT_API_URL}/chat", json=payload, timeout=120)
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
    st.session_state["player_origin"] = st.session_state.get("page", PAGE_TEAM)
    set_page(PAGE_PLAYER)


# -----------------------------------------------------------------------------
# Composants d'affichage
# -----------------------------------------------------------------------------

def show_team_header(team: dict, subtitle: str = ""):
    subtitle_html = f"<p>{subtitle}</p>" if subtitle else ""

    st.markdown(
        f"""
        <div style="text-align:center; margin: 2rem 0;">
            <h2>{team["team_name"]}</h2>
            {subtitle_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def show_players_block(title: str, players: list[dict], key_prefix: str):
    st.subheader(title)

    if not players:
        st.info("Aucun joueur.")
        return

    # La composition d'un match ne porte ni compteur d'apparitions ni valeur
    # marchande : ces colonnes n'apparaissent que pour l'effectif de la saison.
    show_squad_columns = any("appearances" in player for player in players)
    widths = [4, 2, 2, 2, 3] if show_squad_columns else [4, 3, 2]

    header = st.columns(widths)
    header[0].markdown("**Joueur**")
    header[1].markdown("**Poste**")
    header[2].markdown("**Note**")

    if show_squad_columns:
        header[3].markdown("**Matchs**")
        header[4].markdown("**Valeur**")

    for player in players:
        columns = st.columns(widths)
        button_key = f"{key_prefix}_player_{player['player_id']}"
        if columns[0].button(player["player_name"], key=button_key):
            go_to_player_page(player)
        columns[1].write(player["position"])
        columns[2].write(format_note(player["global_note"]))

        if show_squad_columns:
            columns[3].write(player.get("appearances", "-"))
            columns[4].write(format_market_value(player.get("market_value_eur")))


def show_movements_block(title: str, players: list[dict], date_label: str, key_prefix: str):
    st.subheader(title)

    if not players:
        st.info("Aucun mouvement.")
        return

    header = st.columns([4, 3, 2, 2])
    header[0].markdown("**Joueur**")
    header[1].markdown(f"**{date_label}**")
    header[2].markdown("**Matchs**")
    header[3].markdown("**Note**")

    for player in players:
        columns = st.columns([4, 3, 2, 2])
        button_key = f"{key_prefix}_player_{player['player_id']}"
        if columns[0].button(player["player_name"], key=button_key):
            go_to_player_page(player)
        columns[1].write(player["date"] or "-")
        columns[2].write(player["appearances"])
        columns[3].write(format_note(player["global_note"]))


def show_team_movements(team_id: int):
    movements = get_team_movements(team_id)

    if not movements["team"]["has_previous_season"]:
        st.info(
            "Pas de saison précédente dans les données pour cette équipe : "
            "les mouvements d'effectif ne peuvent pas être calculés."
        )
        return

    st.caption(
        "Mouvements déduits des feuilles de match, faute de source de transferts "
        "couvrant les 99 équipes. Un joueur peut apparaître comme arrivée après "
        "une promotion ou un retour de prêt, et comme départ après une longue "
        "blessure. Le nombre de matchs aide à faire la part des choses."
    )

    arrivals_column, departures_column = st.columns(2)

    with arrivals_column:
        show_movements_block(
            f"Arrivées ({len(movements['arrivals'])})",
            movements["arrivals"],
            "Premier match",
            key_prefix="arrival",
        )

    with departures_column:
        show_movements_block(
            f"Départs ({len(movements['departures'])})",
            movements["departures"],
            "Dernier match",
            key_prefix="departure",
        )


def format_market_value(value):
    if value is None:
        return "-"

    value = float(value)

    if value >= 1_000_000:
        millions = value / 1_000_000
        formatted = f"{millions:.1f}".rstrip("0").rstrip(".")
        return f"{formatted} M€"

    if value >= 1_000:
        return f"{value / 1_000:.0f} k€"

    return f"{value:.0f} €"


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


def show_sql_agent_chat():
    st.sidebar.divider()
    st.sidebar.subheader("Chat data")

    with st.sidebar.form("sql_agent_chat_form"):
        message = st.text_area(
            "Question",
            placeholder="Ex : quels sont les meilleurs attaquants ?",
            height=90,
        )
        submitted = st.form_submit_button("Envoyer")

    if not submitted:
        return

    if not message.strip():
        st.sidebar.warning("Écris une question.")
        return

    try:
        result = ask_sql_agent(message.strip())
    except requests.RequestException as error:
        st.sidebar.error(f"Agent indisponible : {error}")
        return

    st.sidebar.write(result["answer"])


# -----------------------------------------------------------------------------
# Page équipe
# -----------------------------------------------------------------------------

def show_team_page():
    st.title("Football Predictor")

    squad_section, prediction_section = st.tabs(["Équipe", "Prédiction"])

    with squad_section:
        show_team_section()

    with prediction_section:
        show_prediction_section()


def show_team_section():
    selected_team = st_searchbox(
        search_function=search_teams,
        placeholder="Rechercher une équipe",
        key="team_search",
        label="Équipe",
    )

    if selected_team and st.button("Valider"):
        st.session_state["team_id"] = selected_team["id"]
        st.session_state["team_data"] = get_team(selected_team["id"])

    team_data = st.session_state.get("team_data")
    if not team_data:
        return

    team = team_data["team"]
    players = team_data["players"]

    show_team_header(team, f"Effectif de la saison - {len(players)} joueurs")

    if st.button("Voir la dernière composition"):
        set_page(PAGE_LINEUP)

    squad_tab, movements_tab = st.tabs(["Effectif", "Mouvements"])

    with squad_tab:
        show_players_block("Effectif", players, key_prefix="squad")

    with movements_tab:
        show_team_movements(st.session_state["team_id"])


# -----------------------------------------------------------------------------
# Onglet prédiction
# -----------------------------------------------------------------------------

def show_prediction_xi(features: dict, label: str):
    team = features["team"]

    st.markdown(f"**{label} - {team['team_name']}**")

    if team["match_date"]:
        st.caption(f"Onze du dernier match ({team['match_date']})")

    if team["substituted_players"]:
        st.caption(
            f"{team['substituted_players']} joueur(s) sans profil SoFIFA remplacé(s) "
            "par les mieux notés de la saison."
        )

    for player in features["players"]:
        st.write(f"{player['player_name']} ({player['position']}) - {player['global_note']}")


def show_prediction_result(prediction: int, home_name: str, away_name: str):
    if prediction == 1:
        st.success(f"Victoire de {home_name}")
    elif prediction == -1:
        st.success(f"Victoire de {away_name}")
    else:
        st.info("Match nul")


def show_prediction_section():
    st.caption(
        "Le modèle a été entrainé sur les onze titulaires de chaque match, "
        "domicile contre extérieur. L'avantage du terrain fait donc partie de "
        "la prédiction : inverser les deux équipes ne donne pas le résultat inverse."
    )

    home_column, away_column = st.columns(2)

    with home_column:
        home_team = st_searchbox(
            search_function=search_teams,
            placeholder="Équipe à domicile",
            key="home_team_search",
            label="Domicile",
        )

    with away_column:
        away_team = st_searchbox(
            search_function=search_teams,
            placeholder="Équipe à l'extérieur",
            key="away_team_search",
            label="Extérieur",
        )

    if not st.button("Prédire le résultat"):
        return

    if not home_team or not away_team:
        st.warning("Sélectionnez les deux équipes.")
        return

    if home_team["id"] == away_team["id"]:
        st.warning("Sélectionnez deux équipes différentes.")
        return

    try:
        home_features = get_prediction_features(home_team["id"])
        away_features = get_prediction_features(away_team["id"])
    except ValueError as error:
        st.error(f"Prédiction impossible : {error}")
        return

    try:
        prediction = predict_match(home_features["notes"], away_features["notes"])
    except requests.RequestException as error:
        st.error(f"Service de prédiction indisponible : {error}")
        return

    show_prediction_result(
        prediction,
        home_features["team"]["team_name"],
        away_features["team"]["team_name"],
    )

    home_column, away_column = st.columns(2)

    with home_column:
        show_prediction_xi(home_features, "Domicile")

    with away_column:
        show_prediction_xi(away_features, "Extérieur")


# -----------------------------------------------------------------------------
# Page composition du dernier match
# -----------------------------------------------------------------------------

def show_lineup_page():
    if st.button("Retour à l'effectif"):
        set_page(PAGE_TEAM)

    lineup_data = get_team_lineup(st.session_state["team_id"])

    team = lineup_data["team"]
    players = lineup_data["players"]
    starters = [player for player in players if player["is_starting_match"]]
    substitutes = [player for player in players if not player["is_starting_match"]]

    show_team_header(
        team,
        f"Dernier match joué le {team['match_date']} - formation {team['formation']}",
    )
    show_players_block("Titulaires", starters, key_prefix="starter")
    show_players_block("Remplaçants", substitutes, key_prefix="sub")


# -----------------------------------------------------------------------------
# Page joueur
# -----------------------------------------------------------------------------

def show_player_page():
    selected_player = st.session_state["selected_player"]

    if st.button("Retour"):
        set_page(st.session_state.get("player_origin", PAGE_TEAM))

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
    PAGE_LINEUP: show_lineup_page,
    PAGE_PLAYER: show_player_page,
}

show_sql_agent_chat()

current_page = st.session_state.get("page", PAGE_TEAM)
page_function = ROUTES.get(current_page, show_team_page)
page_function()
