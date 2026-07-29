"""Pages Tournoi.

Pour l'instant les tournois sont construits avec des équipes custom, car les
tables Neon de tournoi référencent custom_team.
"""

from __future__ import annotations

import random

import streamlit as st

import api_client


TOURNAMENT_SIZES = [2, 4, 8, 16]


def go_to_page(page_name: str):
    st.session_state["page"] = page_name
    st.rerun()


def format_team_name(team: dict | None) -> str:
    if not team:
        return "À définir"

    return team.get("team_name") or team.get("name") or str(team.get("team_id"))


def show_bracket(teams: list[dict]):
    """Affiche un tableau simple : premier tour rempli, tours suivants vides."""
    if not teams:
        return

    rounds = []
    current_round = teams

    while current_round:
        rounds.append(current_round)
        if len(current_round) == 1:
            break
        current_round = [None for _ in range(len(current_round) // 2)]

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
            html += f'<div class="tournament-slot">{format_team_name(team)}</div>'
        html += "</div>"

    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)


def show_tournament_summary(tournament_record: dict):
    tournament = tournament_record["tournament"]
    winner = tournament.get("winner_team_id")
    status = "Terminé" if winner else "En cours"

    st.subheader(tournament["tournament_name"])
    st.write(f"Nombre d'équipes : {tournament['nb_teams']}")
    st.write(f"Statut : {status}")

    if winner:
        st.write(f"Vainqueur : {winner}")


def show_tournament_page(create_page: str):
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

    selected_id = st.session_state.get("selected_tournament_id")

    with content_column:
        if not selected_id:
            st.info("Sélectionnez un tournoi ou créez-en un nouveau.")
            return

        record = api_client.get_tournament(selected_id)
        if not record:
            st.warning("Tournoi introuvable dans la session.")
            return

        show_tournament_summary(record)
        st.caption("La page détail avec le tableau complet arrive à l'étape suivante.")


def show_tournament_create_page(main_page: str):
    if st.button("Retour"):
        go_to_page(main_page)

    st.title("Créer un tournoi")

    tournament_name = st.text_input("Nom du tournoi", key="new_tournament_name")
    nb_teams = st.selectbox("Nombre d'équipes", TOURNAMENT_SIZES, index=2)

    if st.session_state.get("new_tournament_size") != nb_teams:
        st.session_state["new_tournament_size"] = nb_teams
        st.session_state["new_tournament_teams"] = []

    selected_teams = st.session_state.setdefault("new_tournament_teams", [])

    if st.button("Fill"):
        try:
            candidates = api_client.list_tournament_candidate_teams()
        except api_client.ApiError as error:
            st.error(f"Fill impossible : {error}")
            return

        if len(candidates) < nb_teams:
            st.warning(f"{len(candidates)} équipe(s) custom prédictible(s) disponible(s).")
            return

        selected_teams = random.sample(candidates, nb_teams)
        st.session_state["new_tournament_teams"] = selected_teams

    if selected_teams:
        st.subheader("Tableau initial")
        show_bracket(selected_teams)

    can_create = bool(tournament_name.strip()) and len(selected_teams) == nb_teams

    if st.button("Créer", type="primary", disabled=not can_create):
        try:
            record = api_client.create_tournament(
                tournament_name,
                [team["team_id"] for team in selected_teams],
            )
        except api_client.ApiError as error:
            st.error(f"Création impossible : {error}")
            return

        st.session_state["new_tournament_teams"] = []
        st.session_state["selected_tournament_id"] = record["tournament"]["tournament_id"]
        st.success("Tournoi créé.")
        go_to_page(main_page)
