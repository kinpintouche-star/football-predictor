"""Pages Tournoi.

Les tournois acceptent les équipes réelles et les équipes custom, tant que
l'API sait produire leurs features de prédiction.
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


def same_team(team_1: dict | None, team_2: dict | None) -> bool:
    return bool(team_1 and team_2 and get_team_id(team_1) == get_team_id(team_2))


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
    selected_name = format_team_name(selected_team) if selected_team else ""
    selected_id = get_team_id(selected_team) if selected_team else "empty"
    columns = st.columns([2, 5, 2])

    columns[0].write(f"Équipe {slot_index + 1}")

    with columns[1]:
        choice = st_searchbox(
            search_function=api_client.search_tournament_candidate_teams,
            placeholder="Rechercher une équipe",
            key=f"tournament_team_search_{slot_index}_{selected_id}",
            label=f"Équipe {slot_index + 1}",
            default=selected_team,
            default_searchterm=selected_name,
            default_options=[(selected_name, selected_team)] if selected_team else None,
            edit_after_submit="current",
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
    saved_match_count = len(record.get("matches", []))

    if (
        tournament_id not in brackets
        or saved_match_count > len(brackets[tournament_id]["matches"])
    ):
        brackets[tournament_id] = build_bracket_state(record)

    return brackets[tournament_id]


def get_saved_match_winner_id(match: dict) -> str | None:
    if match.get("winner_team_id"):
        return str(match["winner_team_id"])

    score_1 = match.get("score_team_1")
    score_2 = match.get("score_team_2")
    if score_1 is None or score_2 is None or score_1 == score_2:
        return None

    return str(match["team_id_1"] if score_1 > score_2 else match["team_id_2"])


def find_saved_match_slot(
    rounds: list[list[dict | None]],
    team_id_1: str,
    team_id_2: str,
) -> tuple[int, int] | None:
    expected_ids = {str(team_id_1), str(team_id_2)}

    for round_index in range(len(rounds) - 1):
        round_teams = rounds[round_index]

        for slot_index in range(0, len(round_teams), 2):
            team_1 = round_teams[slot_index]
            team_2 = round_teams[slot_index + 1]

            if not team_1 or not team_2:
                continue

            if {get_team_id(team_1), get_team_id(team_2)} == expected_ids:
                return round_index, slot_index

    return None


def saved_match_to_history(match: dict) -> dict:
    return {
        "custom_match_id": match.get("custom_match_id"),
        "phase": match.get("phase"),
        "team_1_name": match.get("team_1_name"),
        "team_2_name": match.get("team_2_name"),
        "score_team_1": match.get("score_team_1"),
        "score_team_2": match.get("score_team_2"),
        "winner_name": match.get("winner_name") or match.get("winner_team_id") or "-",
    }


def build_bracket_state(record: dict) -> dict:
    teams = sorted(
        record.get("teams", []),
        key=lambda team: (
            team.get("slot_index") is None,
            team.get("slot_index") or 0,
            format_team_name(team),
        ),
    )
    rounds = build_initial_rounds(teams)
    teams_by_id = {get_team_id(team): normalize_team(team) for team in teams}
    history = []

    for match in record.get("matches", []):
        history.append(saved_match_to_history(match))
        winner_id = get_saved_match_winner_id(match)
        slot = find_saved_match_slot(
            rounds,
            str(match["team_id_1"]),
            str(match["team_id_2"]),
        )

        if not winner_id or not slot:
            continue

        round_index, slot_index = slot
        current_pair = rounds[round_index][slot_index:slot_index + 2]
        winner = next(
            (team for team in current_pair if team and get_team_id(team) == winner_id),
            teams_by_id.get(winner_id),
        )

        if winner:
            rounds[round_index + 1][slot_index // 2] = winner

    return {"rounds": rounds, "matches": history}


def render_tournament_state(bracket: dict, bracket_placeholder, history_placeholder):
    with bracket_placeholder.container():
        show_bracket(bracket["rounds"])

    with history_placeholder.container():
        show_match_history(bracket["matches"])


def show_bracket(rounds: list[list[dict | None]]):
    """Affiche le tableau actuel avec les liens entre tours."""
    if not rounds:
        return

    teams = rounds[0]
    if not teams:
        return

    slot_width = 240
    slot_height = 58
    horizontal_gap = 76
    row_gap = 24
    padding = 12
    step = slot_height + row_gap
    width = padding * 2 + len(rounds) * slot_width + (len(rounds) - 1) * horizontal_gap
    height = padding * 2 + len(teams) * slot_height + (len(teams) - 1) * row_gap

    def slot_position(round_index: int, slot_index: int) -> tuple[float, float]:
        group_size = 2 ** round_index
        center_y = padding + slot_height / 2 + (
            slot_index * group_size + (group_size - 1) / 2
        ) * step
        x = padding + round_index * (slot_width + horizontal_gap)
        y = center_y - slot_height / 2
        return x, y

    def slot_status(round_index: int, slot_index: int, team: dict | None) -> str:
        if not team:
            return "pending"

        if round_index == len(rounds) - 1:
            return "winner"

        next_team = rounds[round_index + 1][slot_index // 2]
        if not next_team:
            return "pending"

        return "winner" if same_team(team, next_team) else "loser"

    def connector_color(round_index: int, slot_index: int) -> str:
        team = rounds[round_index][slot_index]
        next_team = rounds[round_index + 1][slot_index // 2]

        if not next_team or not team:
            return "#2563eb"

        return "#16a34a" if same_team(team, next_team) else "#dc2626"

    paths = []
    for round_index in range(len(rounds) - 1):
        for pair_start in range(0, len(rounds[round_index]), 2):
            indexes = [pair_start, pair_start + 1]
            next_team = rounds[round_index + 1][pair_start // 2]

            if next_team:
                indexes.sort(key=lambda index: same_team(rounds[round_index][index], next_team))

            for slot_index in indexes:
                x1, y1 = slot_position(round_index, slot_index)
                x2, y2 = slot_position(round_index + 1, slot_index // 2)
                start_x = x1 + slot_width
                start_y = y1 + slot_height / 2
                end_x = x2
                end_y = y2 + slot_height / 2
                mid_x = start_x + horizontal_gap / 2
                color = connector_color(round_index, slot_index)

                paths.append(
                    f'<path d="M {start_x} {start_y} H {mid_x} V {end_y} H {end_x}" '
                    f'stroke="{color}" stroke-width="3" fill="none" '
                    f'stroke-linecap="round" stroke-linejoin="round" />'
                )

    slots = []
    for round_index, round_teams in enumerate(rounds):
        for slot_index, team in enumerate(round_teams):
            x, y = slot_position(round_index, slot_index)
            status = slot_status(round_index, slot_index, team)
            slots.append(
                f'<div class="tournament-slot tournament-slot-{status}" '
                f'style="left:{x}px; top:{y}px;">'
                f'{escape(format_team_name(team))}'
                f'</div>'
            )

    html = f"""
    <style>
        .tournament-bracket-scroll {{
            overflow-x: auto;
            padding: 18px 0 28px;
        }}
        .tournament-bracket {{
            position: relative;
            width: {width}px;
            height: {height}px;
        }}
        .tournament-lines {{
            position: absolute;
            inset: 0;
            z-index: 1;
        }}
        .tournament-slot {{
            position: absolute;
            z-index: 2;
            width: {slot_width}px;
            height: {slot_height}px;
            display: flex;
            align-items: center;
            border: 2px solid #2563eb;
            border-radius: 8px;
            padding: 0 16px;
            background: #111827;
            color: #f9fafb;
            font-size: 15px;
            font-weight: 700;
            overflow: hidden;
            white-space: nowrap;
            text-overflow: ellipsis;
            box-shadow: 0 1px 2px rgba(15, 23, 42, 0.18);
        }}
        .tournament-slot-winner {{
            border-color: #16a34a;
            background: #052e16;
        }}
        .tournament-slot-loser {{
            border-color: #dc2626;
            background: #3f0b0b;
            color: #fecaca;
        }}
        .tournament-slot-pending {{
            border-color: #2563eb;
        }}
    </style>
    <div class="tournament-bracket-scroll">
        <div class="tournament-bracket">
            <svg class="tournament-lines" width="{width}" height="{height}">
                {''.join(paths)}
            </svg>
            {''.join(slots)}
        </div>
    </div>
    """
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


def show_action_loader(placeholder, message: str):
    """Petit loader local, plus discret que le flou global Streamlit."""
    placeholder.markdown(
        f"""
        <style>
            .tournament-action-loader {{
                display: flex;
                justify-content: flex-end;
                align-items: center;
                gap: 0.5rem;
                margin-top: 0.75rem;
                color: #2563eb;
                font-size: 0.9rem;
                font-weight: 700;
            }}
            .tournament-action-spinner {{
                width: 16px;
                height: 16px;
                border: 2px solid rgba(37, 99, 235, 0.25);
                border-top-color: #2563eb;
                border-radius: 50%;
                animation: tournament-spin 0.8s linear infinite;
            }}
            @keyframes tournament-spin {{
                to {{ transform: rotate(360deg); }}
            }}
        </style>
        <div class="tournament-action-loader">
            <span>{escape(message)}</span>
            <span class="tournament-action-spinner"></span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def play_next_match(record: dict, bracket: dict, feature_cache: dict[str, dict]) -> bool:
    rounds = bracket["rounds"]
    next_match = find_next_match(rounds)

    if not next_match:
        return False

    round_index, slot_index = next_match
    team_1 = rounds[round_index][slot_index]
    team_2 = rounds[round_index][slot_index + 1]
    phase = round_label(len(rounds[round_index]))

    prediction = api_client.predict_match_from_notes(
        feature_cache[get_team_id(team_1)]["notes"],
        feature_cache[get_team_id(team_2)]["notes"],
    )
    winner, score_1, score_2, message = prediction_to_winner(prediction, team_1, team_2)

    saved_match = api_client.set_tournament(
        record["tournament"]["tournament_id"],
        get_team_id(team_1),
        get_team_id(team_2),
        score_1,
        score_2,
        phase,
        get_team_id(winner),
    )
    custom_match_id = saved_match.get("match", {}).get("custom_match_id")

    if not custom_match_id:
        raise api_client.ApiError("Match prédit mais non confirmé dans custom_match")

    rounds[round_index + 1][slot_index // 2] = winner
    bracket["matches"].append(
        {
            "custom_match_id": custom_match_id,
            "phase": phase,
            "team_1_name": format_team_name(team_1),
            "team_2_name": format_team_name(team_2),
            "score_team_1": score_1,
            "score_team_2": score_2,
            "winner_name": format_team_name(winner),
            "message": message,
        }
    )

    return True


def run_remaining_predictions(
    record: dict,
    bracket: dict,
    bracket_placeholder,
    history_placeholder,
    progress_placeholder,
):
    show_action_loader(progress_placeholder, "Préparation des équipes")
    team_ids = {
        get_team_id(team)
        for round_teams in bracket["rounds"]
        for team in round_teams
        if team
    }
    feature_cache = api_client.get_many_prediction_features(sorted(team_ids))
    played = 0

    while play_next_match(record, bracket, feature_cache):
        played += 1
        show_action_loader(progress_placeholder, f"{played} match(s) joué(s)")
        render_tournament_state(bracket, bracket_placeholder, history_placeholder)

    winner = bracket["rounds"][-1][0] if bracket["rounds"] and bracket["rounds"][-1] else None
    if winner:
        record["tournament"]["winner_team_id"] = get_team_id(winner)
        record["tournament"]["winner_team_name"] = format_team_name(winner)

    return played, winner


def show_tournament_action(record: dict, bracket: dict, bracket_placeholder, history_placeholder):
    rounds = bracket["rounds"]
    next_match = find_next_match(rounds)

    if not next_match:
        winner = rounds[-1][0] if rounds and rounds[-1] else None

        if winner:
            record["tournament"]["winner_team_id"] = get_team_id(winner)
            record["tournament"]["winner_team_name"] = format_team_name(winner)
            st.success(f"Vainqueur : {format_team_name(winner)}")

        return

    button_label = "Poursuivre tournoi" if bracket["matches"] else "Lancer tournoi"

    if not st.button(button_label, type="primary", use_container_width=True):
        return

    progress_placeholder = st.empty()

    try:
        played, winner = run_remaining_predictions(
            record,
            bracket,
            bracket_placeholder,
            history_placeholder,
            progress_placeholder,
        )
    except api_client.ApiError as error:
        progress_placeholder.empty()
        st.error(f"Prédiction impossible : {error}")
        return

    progress_placeholder.empty()
    if winner:
        st.success(f"{played} match(s) prédit(s). Vainqueur : {format_team_name(winner)}")
    else:
        st.success(f"{played} match(s) prédit(s).")


def show_tournament_page(create_page: str, detail_page: str):
    st.title("Tournois")

    if st.button("Créer tournoi", type="primary"):
        go_to_page(create_page)

    try:
        tournaments = api_client.list_tournaments()
    except api_client.ApiError as error:
        st.error(f"Liste des tournois indisponible : {error}")
        return

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

    try:
        record = api_client.get_tournament(selected_id)
    except api_client.ApiError as error:
        st.error(f"Tournoi indisponible : {error}")
        return

    tournament = record["tournament"]
    winner = tournament.get("winner_team_name") or tournament.get("winner_team_id")
    status = "Terminé" if winner else "En cours"

    st.title(tournament["tournament_name"])

    info_columns = st.columns(3)
    info_columns[0].metric("Équipes", tournament["nb_teams"])
    info_columns[1].metric("Statut", status)
    info_columns[2].metric("Vainqueur", winner or "-")

    bracket = get_bracket_state(record)
    title_column, action_column = st.columns([3, 1])
    title_column.subheader("Tableau")
    bracket_placeholder = st.empty()
    history_placeholder = st.empty()

    render_tournament_state(bracket, bracket_placeholder, history_placeholder)

    with action_column:
        show_tournament_action(record, bracket, bracket_placeholder, history_placeholder)


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
