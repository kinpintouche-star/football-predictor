"""Pages Tournoi.

Pour l'instant les tournois sont construits avec des équipes custom, car les
tables Neon de tournoi référencent custom_team.
"""

from __future__ import annotations

from html import escape
import random

import streamlit as st
from streamlit_searchbox import st_searchbox

import api_client


TOURNAMENT_SIZES = [2, 4, 8, 16]
DETAIL_PAGE = "tournament_detail"


def go_to_page(page_name: str):
    st.session_state["page"] = page_name
    st.rerun()


def get_team_id(team: dict) -> str:
    return str(team.get("team_id") or team.get("custom_team_id"))


def normalize_team(team: dict) -> dict:
    team = dict(team)
    team["team_id"] = get_team_id(team)
    return team


def get_creation_slots(nb_teams: int) -> list[dict | None]:
    slots = st.session_state.setdefault("new_tournament_teams", [])

    while len(slots) < nb_teams:
        slots.append(None)

    del slots[nb_teams:]
    return slots


def selected_team_ids(teams: list[dict | None], current_index: int | None = None) -> set[str]:
    return {
        get_team_id(team)
        for index, team in enumerate(teams)
        if team and index != current_index
    }


def format_team_name(team: dict | None) -> str:
    if not team:
        return "À définir"

    return team.get("team_name") or team.get("name") or str(team.get("team_id", "À définir"))


def build_initial_rounds(teams: list[dict | None]) -> list[list[dict | None]]:
    first_round = [
        normalize_team(team) if team else None
        for team in teams[:16]
    ]
    rounds = [first_round]
    next_round_size = len(first_round) // 2

    while next_round_size:
        rounds.append([None for _ in range(next_round_size)])
        next_round_size //= 2

    return rounds


def fill_empty_creation_slots(selected_teams: list[dict | None], nb_teams: int):
    candidates = api_client.list_tournament_candidate_teams()
    taken_ids = selected_team_ids(selected_teams)
    available = [team for team in candidates if get_team_id(team) not in taken_ids]

    if len(available) < selected_teams.count(None):
        st.warning(f"{len(available)} équipe(s) disponible(s) pour les slots vides.")
        return

    random.shuffle(available)

    for index in range(nb_teams):
        if selected_teams[index] is None:
            selected_teams[index] = available.pop()


def show_team_slot(slot_index: int, selected_teams: list[dict | None]):
    selected_team = selected_teams[slot_index]
    columns = st.columns([2, 5, 2])

    columns[0].write(f"Équipe {slot_index + 1}")

    with columns[1]:
        choice = st_searchbox(
            search_function=api_client.search_tournament_candidate_teams,
            placeholder="Rechercher une équipe custom",
            key=f"tournament_team_search_{slot_index}",
            label=f"Équipe {slot_index + 1}",
            default=selected_team,
            label_visibility="collapsed",
        )

    if choice:
        if get_team_id(choice) in selected_team_ids(selected_teams, slot_index):
            columns[2].warning("Déjà prise")
        else:
            selected_teams[slot_index] = choice
            selected_team = choice

    columns[2].success("Rempli") if selected_team else columns[2].error("Vide")


def get_bracket_state(record: dict) -> dict:
    tournament_id = record["tournament"]["tournament_id"]
    brackets = st.session_state.setdefault("tournament_brackets", {})

    if tournament_id not in brackets:
        brackets[tournament_id] = {
            "rounds": build_initial_rounds(record.get("teams", [])),
            "matches": [],
        }

    return brackets[tournament_id]


def show_bracket(rounds: list[list[dict | None]]):
    """Affiche le tableau actuel."""
    if not rounds:
        return

    teams = rounds[0]
    if not teams:
        return

    html = """
    <style>
        .tournament-bracket {
            display: flex;
            gap: 28px;
            align-items: center;
            overflow-x: auto;
            padding: 18px 0;
        }
        .tournament-round {
            display: flex;
            flex-direction: column;
            gap: 12px;
            min-width: 190px;
        }
        .tournament-slot {
            border: 1px solid #4b5563;
            border-radius: 8px;
            padding: 10px 12px;
            min-height: 42px;
            background: #111827;
            color: #f9fafb;
            font-size: 14px;
        }
    </style>
    <div class="tournament-bracket">
    """

    for round_index, round_teams in enumerate(rounds, start=1):
        html += f'<div class="tournament-round" aria-label="Tour {round_index}">'
        for team in round_teams:
            html += f'<div class="tournament-slot">{escape(format_team_name(team))}</div>'
        html += "</div>"

    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)


def find_next_match(rounds: list[list[dict | None]]) -> tuple[int, int] | None:
    for round_index in range(len(rounds) - 1):
        current_round = rounds[round_index]
        next_round = rounds[round_index + 1]

        for slot_index in range(0, len(current_round), 2):
            next_slot_index = slot_index // 2
            has_both_teams = current_round[slot_index] and current_round[slot_index + 1]

            if has_both_teams and not next_round[next_slot_index]:
                return round_index, slot_index

    return None


def round_label(round_size: int) -> str:
    if round_size == 2:
        return "Finale"

    if round_size == 4:
        return "Demi-finale"

    if round_size == 8:
        return "Quart de finale"

    return "Premier tour"


def prediction_to_winner(prediction: int, team_1: dict, team_2: dict) -> tuple[dict, int, int, str]:
    if prediction == 1:
        return team_1, 1, 0, f"Victoire prédite : {format_team_name(team_1)}"

    if prediction == -1:
        return team_2, 0, 1, f"Victoire prédite : {format_team_name(team_2)}"

    winner = random.choice([team_1, team_2])
    return winner, 1, 1, f"Nul prédit, {format_team_name(winner)} passe aux tirs au but"


def show_match_history(matches: list[dict]):
    if not matches:
        return

    st.subheader("Matchs joués")

    for match in matches:
        st.write(
            f"{match['phase']} - {match['team_1_name']} {match['score_team_1']}"
            f" / {match['score_team_2']} {match['team_2_name']} - "
            f"{match['winner_name']} qualifié"
        )


def show_next_prediction(record: dict, bracket: dict):
    rounds = bracket["rounds"]
    next_match = find_next_match(rounds)

    if not next_match:
        winner = rounds[-1][0] if rounds and rounds[-1] else None

        if winner:
            record["tournament"]["winner_team_id"] = get_team_id(winner)
            record["tournament"]["winner_team_name"] = format_team_name(winner)
            st.success(f"Vainqueur : {format_team_name(winner)}")

        return

    round_index, slot_index = next_match
    team_1 = rounds[round_index][slot_index]
    team_2 = rounds[round_index][slot_index + 1]
    phase = round_label(len(rounds[round_index]))
    button_label = "Poursuivre tournoi" if bracket["matches"] else "Lancer tournoi"

    st.subheader("Prochain match")
    st.write(f"{phase} : {format_team_name(team_1)} vs {format_team_name(team_2)}")

    if not st.button(button_label, type="primary"):
        return

    try:
        prediction = api_client.predict_match(get_team_id(team_1), get_team_id(team_2))
        winner, score_1, score_2, message = prediction_to_winner(prediction, team_1, team_2)
        api_client.set_tournament(
            record["tournament"]["tournament_id"],
            get_team_id(team_1),
            get_team_id(team_2),
            score_1,
            score_2,
            phase,
        )
    except api_client.ApiError as error:
        st.error(f"Prédiction impossible : {error}")
        return

    rounds[round_index + 1][slot_index // 2] = winner
    bracket["matches"].append(
        {
            "phase": phase,
            "team_1_name": format_team_name(team_1),
            "team_2_name": format_team_name(team_2),
            "score_team_1": score_1,
            "score_team_2": score_2,
            "winner_name": format_team_name(winner),
            "message": message,
        }
    )

    st.success(message)
    st.rerun()


def show_tournament_page(create_page: str, detail_page: str):
    st.title("Tournois")

    if st.button("Créer tournoi", type="primary"):
        go_to_page(create_page)

    tournaments = api_client.list_tournaments()
    list_column, content_column = st.columns([1, 3])

    with list_column:
        st.subheader("Liste")

        if not tournaments:
            st.info("Aucun tournoi.")
        else:
            for record in tournaments:
                tournament = record["tournament"]
                status = "Terminé" if tournament.get("winner_team_id") else "En cours"
                label = f"{tournament['tournament_name']} - {status}"

                if st.button(label, key=f"tournament_{tournament['tournament_id']}"):
                    st.session_state["selected_tournament_id"] = tournament["tournament_id"]
                    go_to_page(detail_page)

    with content_column:
        st.info("Sélectionnez un tournoi dans la liste ou créez-en un nouveau.")


def show_tournament_detail_page(main_page: str):
    if st.button("Retour"):
        go_to_page(main_page)

    selected_id = st.session_state.get("selected_tournament_id")
    if not selected_id:
        st.warning("Aucun tournoi sélectionné.")
        return

    record = api_client.get_tournament(selected_id)
    if not record:
        st.warning("Tournoi introuvable dans la session.")
        return

    tournament = record["tournament"]
    winner = tournament.get("winner_team_name") or tournament.get("winner_team_id")
    status = "Terminé" if winner else "En cours"

    st.title(tournament["tournament_name"])

    info_columns = st.columns(3)
    info_columns[0].metric("Équipes", tournament["nb_teams"])
    info_columns[1].metric("Statut", status)
    info_columns[2].metric("Vainqueur", winner or "-")

    st.subheader("Tableau")
    bracket = get_bracket_state(record)
    show_bracket(bracket["rounds"])
    show_next_prediction(record, bracket)
    show_match_history(bracket["matches"])


def show_tournament_create_page(main_page: str, detail_page: str = DETAIL_PAGE):
    if st.button("Retour"):
        go_to_page(main_page)

    st.title("Créer un tournoi")

    tournament_name = st.text_input("Nom du tournoi", key="new_tournament_name")
    nb_teams = st.selectbox("Nombre d'équipes", TOURNAMENT_SIZES, index=2)

    if st.session_state.get("new_tournament_size") != nb_teams:
        st.session_state["new_tournament_size"] = nb_teams
        st.session_state["new_tournament_teams"] = [None for _ in range(nb_teams)]

    selected_teams = get_creation_slots(nb_teams)

    if st.button("Fill"):
        try:
            fill_empty_creation_slots(selected_teams, nb_teams)
        except api_client.ApiError as error:
            st.error(f"Fill impossible : {error}")
            return

    st.subheader("Équipes")
    for slot_index in range(nb_teams):
        show_team_slot(slot_index, selected_teams)

    if any(selected_teams):
        st.subheader("Tableau initial")
        show_bracket(build_initial_rounds(selected_teams))

    selected_complete_teams = [team for team in selected_teams if team]
    can_create = bool(tournament_name.strip()) and len(selected_complete_teams) == nb_teams

    if st.button("Créer", type="primary", disabled=not can_create):
        try:
            record = api_client.create_tournament(
                tournament_name,
                [get_team_id(team) for team in selected_complete_teams],
            )
        except api_client.ApiError as error:
            st.error(f"Création impossible : {error}")
            return

        st.session_state["new_tournament_teams"] = [None for _ in range(nb_teams)]
        st.session_state["selected_tournament_id"] = record["tournament"]["tournament_id"]
        st.success("Tournoi créé.")
        go_to_page(detail_page)
