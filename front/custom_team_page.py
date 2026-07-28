"""Page « Custom team » : composer un onze, de zéro ou à partir d'une équipe
réelle prise comme modèle.

Deux façons de remplir la compo, qui se combinent :

* poste par poste, en choisissant dans le catalogue ;
* d'un coup, en cherchant une équipe réelle et en cliquant « Fill » : les
  meilleurs joueurs de son effectif sont placés selon la compo choisie, puis
  chaque poste reste modifiable.

La contrainte de budget est désactivée par défaut : le coût de la sélection
est affiché mais n'empêche jamais d'enregistrer. Activée, elle interdit
d'enregistrer une équipe plus chère que le plafond.

L'enregistrement part vers l'API. La liste des équipes affichée en dessous ne
montre en revanche que celles créées pendant la session : il n'existe pas de
GET sur custom_team. Voir api_client pour le détail de ce qui reste local.
"""

from __future__ import annotations

import streamlit as st
from streamlit_searchbox import st_searchbox

import api_client

LINE_LABELS = {
    "GK": "Gardien",
    "DEF": "Défenseurs",
    "MID": "Milieux",
    "FWD": "Attaquants",
}

# Postes de chaque ligne. Le gardien est isolé : un 4-4-2 attend 1 gardien ET
# 4 défenseurs, pas 5 défenseurs.
PLAYER_LINES = {
    "GK": ["GK"],
    "DEF": ["CB", "LB", "RB", "LWB", "RWB"],
    "MID": ["CDM", "CM", "CAM", "LM", "RM"],
    "FWD": ["ST", "CF", "LW", "RW"],
}
LINE_BY_POSITION = {
    position: line
    for line, positions in PLAYER_LINES.items()
    for position in positions
}

FREE_SLOT = ""

FILLED = "🟢"
EMPTY = "🔴"


def format_price(value) -> str:
    if value is None:
        return "-"

    value = float(value)

    # Le budget restant devient négatif dès qu'on dépasse : on met en forme la
    # valeur absolue, sinon aucun seuil ne s'applique et le montant s'affiche
    # en euros bruts.
    sign = "-" if value < 0 else ""
    value = abs(value)

    if value >= 1_000_000:
        millions = f"{value / 1_000_000:.1f}".rstrip("0").rstrip(".")
        return f"{sign}{millions} M€"

    if value >= 1_000:
        return f"{sign}{value / 1_000:.0f} k€"

    return f"{sign}{value:.0f} €"


def go_to_page(page_name: str):
    # app.py importe ce module : on ne peut pas importer son set_page en retour.
    # L'état de navigation est de toute façon porté par la session.
    st.session_state["page"] = page_name
    st.rerun()


# -----------------------------------------------------------------------------
# Sélection courante
# -----------------------------------------------------------------------------

def get_selection() -> dict:
    """Sélection courante : slot -> joueur, un slot valant par exemple ("DEF", 2)."""
    return st.session_state.setdefault("custom_team_selection", {})


def selected_players() -> list[dict]:
    return [player for player in get_selection().values() if player]


def total_spent() -> int:
    return sum(player["price"] or 0 for player in selected_players())


def drop_slots_outside_compo(lines: dict):
    """Changer de compo retire les postes qui n'existent plus."""
    selection = get_selection()

    for slot in list(selection):
        line, slot_index = slot
        if slot_index >= lines.get(line, 0):
            selection.pop(slot)


# -----------------------------------------------------------------------------
# Pré-remplissage depuis une équipe réelle
# -----------------------------------------------------------------------------

def normalize_squad_player(player: dict) -> dict | None:
    """Met un joueur d'effectif réel au format du catalogue.

    Quand le joueur figure au catalogue, c'est cette version qui est retenue :
    sa note est alors celle du modèle, comparable à celle des joueurs choisis à
    la main. Sinon on garde `global_note`, qui vaut overall_rating.

    Les deux échelles n'ont rien à voir — un gardien vaut 89 en overall et 37
    pour le modèle — donc une compo pré-remplie mélange les genres tant que
    l'API n'expose pas la note du modèle par joueur ( voir README ).
    """
    line = LINE_BY_POSITION.get(player.get("position"))

    if not line:
        return None

    catalogue_player = api_client.get_catalogue_player(player["player_id"])

    if catalogue_player:
        return catalogue_player

    return {
        "player_id": player["player_id"],
        "player_name": player["player_name"],
        "best_position": player["position"],
        "note": player.get("global_note"),
        # 18 des 48 joueurs d'un effectif comme le Real n'ont pas de valeur
        # marchande connue. On les compte pour 0 : le total est alors un
        # minimum, ce qui vaut mieux qu'un poste inchiffrable.
        "price": player.get("market_value_eur") or 0,
        "line": line,
    }


def fill_from_team(team_id: int, lines: dict):
    """Place les meilleurs joueurs de l'effectif dans les postes de la compo.

    L'effectif arrive déjà trié par note décroissante : pour chaque ligne on
    prend les premiers, dans l'ordre.
    """
    squad = api_client.get_team_squad(team_id)

    by_line: dict[str, list[dict]] = {line: [] for line in PLAYER_LINES}

    for player in squad:
        normalized = normalize_squad_player(player)
        if normalized:
            by_line[normalized["line"]].append(normalized)

    selection = get_selection()
    selection.clear()

    missing = []

    for line, count in lines.items():
        available = by_line[line]

        for slot_index in range(count):
            if slot_index < len(available):
                selection[(line, slot_index)] = available[slot_index]
            else:
                missing.append(f"{LINE_LABELS[line]} {slot_index + 1}")

    return missing


# -----------------------------------------------------------------------------
# En-tête, budget, modèle
# -----------------------------------------------------------------------------

def show_header():
    columns = st.columns([1, 4])

    if columns[0].button("Go back"):
        go_to_page("team")

    columns[1].subheader("Custom team")


def show_identity_controls() -> tuple[str, int | None, str]:
    """Nom, budget et compo. Le budget vaut None quand la limite est désactivée."""
    name = st.text_input("Team name", key="custom_team_name", placeholder="FC JEDHA OLYMPICO")

    # `bottom` : sans cela le toggle se cale en haut de sa colonne, alors que le
    # champ voisin est décalé vers le bas par son propre libellé.
    budget_columns = st.columns([3, 1], vertical_alignment="bottom")

    budget_millions = budget_columns[0].number_input(
        "Total budget (M€)",
        min_value=50,
        max_value=3000,
        value=api_client.DEFAULT_BUDGET_EUR // 1_000_000,
        step=50,
        key="custom_team_budget",
    )

    # Décochée par défaut : on compose librement, et la limite ne s'applique
    # que si elle est demandée.
    limited = budget_columns[1].toggle(
        "Limiter",
        value=False,
        key="custom_team_budget_limited",
        help="Désactivé, le coût reste affiché mais n'empêche pas d'enregistrer.",
    )

    compos = api_client.get_compos()
    compo_ref = st.selectbox(
        "Compo style",
        [compo["compo_ref"] for compo in compos],
        key="custom_team_compo",
    )

    budget = int(budget_millions) * 1_000_000 if limited else None

    return name, budget, compo_ref


def show_template_controls(lines: dict):
    """« Search team » + « Fill » : partir d'une équipe réelle."""
    # Le libellé est sorti de la colonne et posé au-dessus de la ligne entière.
    # st_searchbox est un composant iframe dont les marges ne sont pas celles
    # d'un widget natif : tant qu'il portait son propre libellé, aucun réglage
    # d'alignement ne mettait le bouton à la même hauteur. Sans libellé, les
    # deux colonnes ne contiennent plus qu'un contrôle nu, et se centrent.
    st.markdown("Partir d'une équipe réelle")

    columns = st.columns([4, 1], vertical_alignment="center")

    with columns[0]:
        try:
            team = st_searchbox(
                search_function=api_client.search_teams,
                placeholder="Search team",
                key="custom_team_template_search",
            )
        except api_client.ApiError as error:
            st.error(f"Recherche indisponible : {error}")
            return

    # `Fill` remplace toute la sélection : on ne l'active qu'une fois une
    # équipe choisie, pour éviter d'effacer une compo par un clic isolé.
    with columns[1]:
        fill = st.button("Fill", disabled=not team, use_container_width=True)

    if not fill:
        return

    try:
        missing = fill_from_team(team["id"], lines)
    except api_client.ApiError as error:
        st.error(f"Pré-remplissage impossible : {error}")
        return

    if missing:
        st.warning(
            f"{team['name']} n'a pas assez de joueurs pour cette compo. "
            f"Postes laissés libres : {', '.join(missing)}."
        )
    else:
        st.success(f"Compo remplie avec les meilleurs joueurs de {team['name']}.")

    st.rerun()


# -----------------------------------------------------------------------------
# Tableau de la compo
# -----------------------------------------------------------------------------

def show_slot_row(line: str, slot_index: int, catalogue: list[dict]):
    selection = get_selection()
    slot = (line, slot_index)
    current = selection.get(slot)

    # Un joueur déjà retenu ailleurs ne doit pas pouvoir être repris.
    taken = {
        player["player_id"]
        for other_slot, player in selection.items()
        if player and other_slot != slot
    }
    candidates = [player for player in catalogue if player["player_id"] not in taken]

    # Un joueur placé par « Fill » vient de l'effectif d'une équipe réelle, pas
    # du catalogue : sans cet ajout il ne figurerait pas dans ses propres
    # options et le poste se viderait au premier affichage.
    if current and all(player["player_id"] != current["player_id"] for player in candidates):
        candidates = [current] + candidates

    labels = [FREE_SLOT] + [
        f"{player['player_name']} · {player['best_position']} · note {player['note']}"
        for player in candidates
    ]

    index = 0
    if current:
        for position, player in enumerate(candidates, start=1):
            if player["player_id"] == current["player_id"]:
                index = position
                break

    columns = st.columns([2, 5, 2, 1])

    columns[0].write(f"{line} {slot_index + 1}" if line != "GK" else "GK")

    # La clé porte le joueur courant : « Fill » change la sélection sans passer
    # par le widget, et une clé figée ferait réafficher l'ancien choix.
    choice = columns[1].selectbox(
        f"{LINE_LABELS[line]} {slot_index + 1}",
        labels,
        index=index,
        key=f"custom_slot_{line}_{slot_index}_{current['player_id'] if current else 'free'}",
        label_visibility="collapsed",
    )

    if choice == FREE_SLOT:
        selection.pop(slot, None)
    else:
        selection[slot] = candidates[labels.index(choice) - 1]

    player = selection.get(slot)
    columns[2].write(format_price(player["price"]) if player else "-")
    columns[3].write(FILLED if player else EMPTY)


def show_compo_table(lines: dict):
    st.markdown("**Player compo**")

    header = st.columns([2, 5, 2, 1])
    header[0].markdown("**Postes**")
    header[1].markdown("**Joueurs**")
    header[2].markdown("**Budget**")

    for line, count in lines.items():
        catalogue = api_client.get_players(line=line)

        for slot_index in range(count):
            show_slot_row(line, slot_index, catalogue)


def show_cost_summary(budget: int | None):
    spent = total_spent()

    if budget is None:
        st.metric("Coût de la sélection", format_price(spent))
        return None

    remaining = budget - spent

    columns = st.columns(3)
    columns[0].metric("Budget", format_price(budget))
    columns[1].metric("Dépensé", format_price(spent))
    columns[2].metric("Restant", format_price(remaining))

    # st.progress refuse une valeur > 1 : on borne, le dépassement est signalé
    # par le message d'erreur juste en dessous.
    st.progress(min(spent / budget, 1.0) if budget else 0.0)

    if remaining < 0:
        st.error(f"Budget dépassé de {format_price(-remaining)}.")

    return remaining


# -----------------------------------------------------------------------------
# Enregistrement
# -----------------------------------------------------------------------------

def show_create_button(name: str, compo_ref: str, budget: int | None, remaining, lines: dict):
    players = selected_players()
    # Les postes vides sont absents de la sélection : le total vient de la
    # compo, pas du nombre de joueurs retenus.
    total_slots = sum(lines.values())
    complete = len(players) == total_slots
    over_budget = remaining is not None and remaining < 0

    if not complete:
        st.caption(f"{len(players)}/{total_slots} postes pourvus.")

    if not st.button(
        "CREATE",
        type="primary",
        disabled=not (complete and name and not over_budget),
    ):
        return

    try:
        api_client.create_team(
            name=name,
            compo_ref=compo_ref,
            player_ids=[player["player_id"] for player in players],
            budget=budget,
        )
    except api_client.ApiError as error:
        st.error(f"Enregistrement impossible : {error}")
        return

    st.session_state["custom_team_selection"] = {}
    st.success(f"Équipe « {name} » enregistrée.")
    st.rerun()


def show_custom_teams_list():
    st.subheader("Équipes enregistrées")

    teams = api_client.list_custom_teams()

    if not teams:
        st.info("Aucune équipe créée pendant cette session.")
        return

    st.caption(
        "Seules les équipes créées depuis l'ouverture de la page sont listées : "
        "l'API n'expose pas de lecture des équipes custom."
    )

    for team in teams:
        title = (
            f"{team['team_name']} · {team['reference_formation']} · "
            f"{format_price(team['spent_eur'])}"
        )

        with st.expander(title):
            if team["overall"] is not None:
                st.caption(
                    f"Note globale {team['overall']} · attaque {team['attack']} · "
                    f"milieu {team['midfield']} · défense {team['defence']}"
                )

            for player in team["players"]:
                columns = st.columns([4, 2, 2, 2])
                columns[0].write(player["player_name"])
                columns[1].write(player["best_position"] or "-")
                columns[2].write(player["note"] if player["note"] is not None else "-")
                columns[3].write(format_price(player["price"]))

            if st.button("Retirer", key=f"delete_custom_team_{team['custom_team_id']}"):
                api_client.delete_custom_team(team["custom_team_id"])
                st.toast("Retirée de la liste. L'équipe reste enregistrée en base.")
                st.rerun()


# -----------------------------------------------------------------------------
# Page
# -----------------------------------------------------------------------------

def show_custom_team_page():
    show_header()

    name, budget, compo_ref = show_identity_controls()

    compos = api_client.get_compos()
    lines = next(compo["lines"] for compo in compos if compo["compo_ref"] == compo_ref)
    drop_slots_outside_compo(lines)

    st.divider()
    show_template_controls(lines)

    st.divider()
    show_compo_table(lines)

    st.divider()
    remaining = show_cost_summary(budget)
    show_create_button(name, compo_ref, budget, remaining, lines)

    st.divider()
    show_custom_teams_list()
