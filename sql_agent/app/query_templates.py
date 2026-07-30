from pathlib import Path
import re
import unicodedata


TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "query_templates"


QUERY_TEMPLATES = [
    {
        "id": "team_by_name",
        "file": "team_by_name.sql",
        "level": "simple",
        "description": "Trouver une equipe reelle ou custom par nom, sans tenir compte des majuscules ni des accents.",
        "keywords": ["equipe", "equipes", "team", "teams", "club", "clubs", "nom", "name", "cherche", "trouve", "find", "get", "search"],
        "direct": False,
    },
    {
        "id": "player_data_by_name",
        "file": "player_data_by_name.sql",
        "level": "simple",
        "description": "Trouver les donnees principales d'un joueur par nom, sans tenir compte des majuscules ni des accents.",
        "keywords": ["joueur", "joueurs", "player", "players", "nom", "name", "cherche", "trouve", "find", "get", "search", "infos", "info", "data", "stat"],
        "direct": False,
    },
    {
        "id": "players_of_team_by_name",
        "file": "players_of_team_by_name.sql",
        "level": "simple",
        "description": "Lister les joueurs d'une equipe par nom d'equipe.",
        "keywords": ["joueur", "joueurs", "player", "players", "effectif", "squad", "roster", "equipe", "team", "club", "appartient", "joue"],
        "direct": False,
    },
    {
        "id": "custom_team_players_by_name",
        "file": "custom_team_players_by_name.sql",
        "level": "simple",
        "description": "Lister les joueurs et le budget d'une equipe custom par nom.",
        "keywords": ["custom", "fantasy", "joueurs", "players", "budget", "prix", "price", "valeur", "value", "equipe", "team"],
        "direct": False,
    },
    {
        "id": "custom_team_by_id",
        "file": "custom_team_by_id.sql",
        "level": "simple",
        "description": "Recuperer les infos generales d'une equipe custom par custom_team_id.",
        "keywords": ["custom", "fantasy", "custom_team_id", "identifiant", "equipe", "team", "infos", "info", "data", "budget"],
        "direct": False,
    },
    {
        "id": "custom_team_by_name",
        "file": "custom_team_by_name.sql",
        "level": "simple",
        "description": "Recuperer les infos generales d'une equipe custom par nom.",
        "keywords": ["custom", "fantasy", "nom", "name", "equipe", "team", "infos", "info", "data", "budget"],
        "direct": False,
    },
    {
        "id": "custom_team_players_by_id",
        "file": "custom_team_players_by_id.sql",
        "level": "simple",
        "description": "Lister les joueurs d'une equipe custom par custom_team_id.",
        "keywords": ["custom", "fantasy", "custom_team_id", "identifiant", "joueurs", "players", "effectif", "equipe", "team"],
        "direct": False,
    },
    {
        "id": "latest_starting_xi_by_team_name",
        "file": "latest_starting_xi_by_team_name.sql",
        "level": "simple",
        "description": "Recuperer le dernier onze titulaire connu d'une equipe reelle.",
        "keywords": ["equipe", "team", "club", "dernier", "latest", "last", "lineup", "compo", "composition", "titulaire", "starting", "onze"],
        "direct": False,
    },
    {
        "id": "matches_of_team_by_name",
        "file": "matches_of_team_by_name.sql",
        "level": "simple",
        "description": "Lister les derniers matchs d'une equipe par nom.",
        "keywords": ["match", "matchs", "matches", "calendrier", "resultat", "resultats", "score", "equipe", "team", "club"],
        "direct": False,
    },
    {
        "id": "tournaments_list",
        "file": "tournaments_list.sql",
        "level": "simple",
        "description": "Lister les tournois custom avec statut et vainqueur si connu.",
        "keywords": ["tournoi", "tournois", "tournament", "tournaments", "liste", "list", "status", "statut", "vainqueur", "winner"],
        "direct": False,
    },
    {
        "id": "tournament_by_id",
        "file": "tournament_by_id.sql",
        "level": "simple",
        "description": "Recuperer un tournoi et ses equipes par tournament_id.",
        "keywords": ["tournoi", "tournament", "tournament_id", "identifiant", "equipe", "equipes", "teams", "statut"],
        "direct": False,
    },
    {
        "id": "tournament_by_name",
        "file": "tournament_by_name.sql",
        "level": "simple",
        "description": "Recuperer un tournoi et ses equipes par nom.",
        "keywords": ["tournoi", "tournament", "nom", "name", "equipe", "equipes", "teams", "statut"],
        "direct": False,
    },
    {
        "id": "tournament_winner_by_id",
        "file": "tournament_winner_by_id.sql",
        "level": "simple",
        "description": "Recuperer le vainqueur d'un tournoi par tournament_id.",
        "keywords": ["tournoi", "tournament", "tournament_id", "identifiant", "vainqueur", "winner", "gagnant", "champion"],
        "direct": False,
    },
    {
        "id": "tournament_winner_by_name",
        "file": "tournament_winner_by_name.sql",
        "level": "simple",
        "description": "Recuperer le vainqueur d'un tournoi par nom.",
        "keywords": ["tournoi", "tournament", "nom", "name", "vainqueur", "winner", "gagnant", "champion"],
        "direct": False,
    },
    {
        "id": "best_real_teams_by_uefa_rank",
        "file": "best_real_teams_by_uefa_rank.sql",
        "level": "complex",
        "description": "Meilleures equipes reelles selon le ranking UEFA.",
        "keywords": ["meilleur", "meilleure", "best", "top", "equipe", "team", "club", "ranking", "rank", "uefa"],
        "direct": True,
    },
    {
        "id": "best_real_teams_by_overall",
        "file": "best_real_teams_by_overall.sql",
        "level": "complex",
        "description": "Equipes reelles les mieux notees par overall SoFIFA.",
        "keywords": ["meilleur", "meilleure", "best", "top", "equipe", "team", "club", "note", "rating", "overall", "sofifa"],
        "direct": True,
    },
    {
        "id": "best_custom_teams_by_overall",
        "file": "best_custom_teams_by_overall.sql",
        "level": "complex",
        "description": "Equipes custom les mieux notees.",
        "keywords": ["meilleur", "meilleure", "best", "top", "equipe", "team", "custom", "fantasy", "note", "rating", "overall"],
        "direct": True,
    },
    {
        "id": "best_players_by_overall",
        "file": "best_players_by_overall.sql",
        "level": "complex",
        "description": "Joueurs les mieux notes par overall_rating.",
        "keywords": ["meilleur", "meilleure", "best", "top", "joueur", "joueurs", "player", "players", "note", "rating", "overall", "sofifa"],
        "direct": True,
    },
    {
        "id": "most_expensive_players",
        "file": "most_expensive_players.sql",
        "level": "complex",
        "description": "Joueurs les plus chers selon Transfermarkt puis SoFIFA.",
        "keywords": ["joueur", "joueurs", "player", "players", "cher", "chers", "expensive", "prix", "price", "valeur", "value", "budget"],
        "direct": True,
    },
    {
        "id": "tournament_matches_with_winners",
        "file": "tournament_matches_with_winners.sql",
        "level": "complex",
        "description": "Matchs de tournoi avec scores et vainqueurs.",
        "keywords": ["tournoi", "tournament", "match", "matchs", "matches", "score", "vainqueur", "winner", "phase"],
        "direct": False,
    },
]


def normalize_text(value: str) -> str:
    value = unicodedata.normalize("NFKD", value)
    value = value.encode("ascii", "ignore").decode("ascii")
    return value.lower()


def load_template(template: dict) -> str:
    return (TEMPLATE_DIR / template["file"]).read_text(encoding="utf-8").strip()


def score_template(question: str, template: dict) -> int:
    question_text = normalize_text(question)
    words = set(re.findall(r"\b\w+\b", question_text))
    has_custom_id = bool(re.search(r"\bc[a-z0-9]{6,}\b", question_text))
    score = sum(1 for keyword in template["keywords"] if keyword in question_text)
    template_id = template["id"]

    if template_id == "players_of_team_by_name" and any(
        phrase in question_text
        for phrase in ("players of", "joueurs de", "joueurs du", "effectif de", "squad of")
    ):
        score += 4

    if template_id == "players_of_team_by_name" and (
        "custom_team_id" in question_text or has_custom_id or ("custom" in question_text and "id" in words)
    ):
        score -= 5

    if template_id == "player_data_by_name" and any(
        phrase in question_text
        for phrase in ("player data", "infos de", "info de", "fiche joueur")
    ):
        score += 3

    if template_id == "team_by_name" and any(
        phrase in question_text
        for phrase in ("best team", "best teams", "meilleure equipe", "meilleur club")
    ):
        score -= 3

    asks_custom = "custom" in question_text or "fantasy" in question_text
    asks_players = any(word in question_text for word in ("joueur", "joueurs", "player", "players", "effectif", "squad"))

    if template_id == "custom_team_by_name" and asks_custom and not asks_players:
        score += 4

    if template_id == "custom_team_players_by_id" and asks_custom and asks_players:
        score += 5

    if template_id == "custom_team_players_by_id" and has_custom_id and asks_players:
        score += 4

    if template_id == "custom_team_players_by_name" and asks_custom and not asks_players:
        score -= 2

    if template_id in ("tournament_winner_by_id", "tournament_winner_by_name") and any(
        word in question_text
        for word in ("vainqueur", "winner", "gagnant", "champion")
    ):
        score += 5

    if template_id.endswith("_by_id") and (
        "id" in words or "identifiant" in question_text or "tournament_id" in question_text or "custom_team_id" in question_text
    ):
        score += 3

    if template_id.endswith("_by_name") and (
        "nom" in words or "name" in words or "appele" in words or "s'appelle" in question_text
    ):
        score += 2

    if template_id == "tournaments_list" and any(
        word in question_text
        for word in ("liste", "list", "tous les tournois", "all tournaments")
    ):
        score += 4

    return score


def select_templates(question: str, limit: int = 3) -> list[dict]:
    scored_templates = [
        (score_template(question, template), index, template)
        for index, template in enumerate(QUERY_TEMPLATES)
    ]
    scored_templates = [
        (score, index, template)
        for score, index, template in scored_templates
        if score > 0
    ]
    scored_templates.sort(key=lambda item: (-item[0], item[1]))
    return [template for _, _, template in scored_templates[:limit]]


def get_direct_template_sql(question: str) -> str | None:
    question_text = normalize_text(question)
    selected = select_templates(question, limit=5)

    if not selected:
        return None

    asks_best = any(word in question_text for word in ("meilleur", "meilleure", "mieux", "best", "top"))
    asks_player = "joueur" in question_text or "player" in question_text
    asks_team = "equipe" in question_text or "team" in question_text or "club" in question_text
    asks_price = any(word in question_text for word in ("cher", "chers", "expensive", "prix", "price", "valeur", "value", "budget"))
    asks_rating = any(word in question_text for word in ("note", "rating", "overall", "sofifa"))

    for template in selected:
        if not template["direct"]:
            continue

        if asks_player and (asks_best or asks_price or asks_rating):
            return load_template(template)

        if asks_team and (asks_best or asks_rating):
            return load_template(template)

    return None


def build_template_context(question: str) -> str:
    templates = select_templates(question)

    if not templates:
        return ""

    simple_templates = [template for template in templates if template["level"] == "simple"]
    complex_templates = [template for template in templates if template["level"] == "complex"]

    def format_blocks(title: str, templates_to_format: list[dict]) -> str:
        if not templates_to_format:
            return ""

        blocks = [title]
        for template in templates_to_format:
            blocks.append(
                f"""
Template: {template["id"]}
Usage: {template["description"]}
SQL:
{load_template(template)}
"""
            )

        return "\n".join(blocks)

    return "\n\n".join(
        block
        for block in [
            format_blocks("Templates simples a utiliser comme briques de base:", simple_templates),
            format_blocks("Templates complexes a adapter apres les briques simples:", complex_templates),
        ]
        if block
    )
