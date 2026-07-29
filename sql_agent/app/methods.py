import json
import os
import re

from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError

from app.database import run_readonly_query
from app.llm import ask_llm
from app.query_templates import build_template_context, get_direct_template_sql, normalize_text
from app.schema import ALLOWED_TABLES, SCHEMA_CONTEXT


FORBIDDEN_SQL_WORDS = {
    "insert",
    "update",
    "delete",
    "drop",
    "alter",
    "create",
    "truncate",
    "grant",
    "revoke",
    "copy",
    "call",
}


INCOMPLETE_SQL_PATTERNS = [
    r"\bis\s+not\s*$",
    r"\bis\s*$",
    r"\bwhere\s*$",
    r"\border\s+by\s*$",
    r"\blimit\s*$",
    r"\bjoin\s*$",
    r"\bon\s*$",
]


DATA_KEYWORDS = {
    "meilleur",
    "meilleure",
    "top",
    "classement",
    "joueur",
    "joueurs",
    "player",
    "players",
    "equipe",
    "equipes",
    "team",
    "teams",
    "club",
    "clubs",
    "match",
    "matchs",
    "matches",
    "tournoi",
    "tournament",
    "score",
    "note",
    "rating",
    "overall",
    "prix",
    "price",
    "valeur",
    "value",
    "budget",
    "composition",
    "lineup",
}


def extract_json_from_llm_response(text: str) -> dict:
    json_match = re.search(r"\{.*\}", text, flags=re.DOTALL)

    if not json_match:
        raise ValueError("Le modele n'a pas renvoye de JSON")

    return json.loads(json_match.group(0))


def extract_sql_from_llm_response(text: str) -> str:
    # Le modele peut renvoyer soit {"sql": "..."}, soit du SQL direct.
    json_match = re.search(r"\{.*\}", text, flags=re.DOTALL)

    if json_match:
        data = json.loads(json_match.group(0))
        return data["sql"]

    sql_match = re.search(r"\b(with|select)\b[\s\S]*", text, flags=re.IGNORECASE)

    if sql_match:
        return sql_match.group(0).strip().strip("`").rstrip(";")

    raise HTTPException(status_code=422, detail="Le modele n'a pas renvoye de SQL")


def validate_sql(sql: str) -> str:
    sql = sql.strip().rstrip(";")
    lowered_sql = sql.lower()

    if not lowered_sql.startswith(("select", "with")):
        raise HTTPException(status_code=422, detail="Seules les requetes SELECT sont autorisees")

    if any(re.search(pattern, lowered_sql) for pattern in INCOMPLETE_SQL_PATTERNS):
        raise HTTPException(status_code=422, detail="SQL incomplet")

    if ";" in sql:
        raise HTTPException(status_code=422, detail="Une seule requete SQL est autorisee")

    used_forbidden_words = [
        word for word in FORBIDDEN_SQL_WORDS
        if re.search(rf"\b{word}\b", lowered_sql)
    ]

    if used_forbidden_words:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "Mot SQL interdit",
                "words": used_forbidden_words,
            },
        )

    cte_names = set(
        match.group(1)
        for match in re.finditer(r"(?:with|,)\s+([a-zA-Z_][a-zA-Z0-9_]*)\s+as\s*\(", lowered_sql)
    )
    table_names = re.findall(
        r'\b(?:from|join)\s+(?:"public"\.)?"?([a-zA-Z_][a-zA-Z0-9_]*)"?',
        lowered_sql,
    )
    unknown_tables = [
        table_name for table_name in table_names
        if table_name not in ALLOWED_TABLES and table_name not in cte_names
    ]

    if unknown_tables:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "Table non autorisee",
                "tables": unknown_tables,
            },
        )

    return sql


def fallback_intent(message: str) -> dict:
    message_text = normalize_text(message)
    mode = "DATA" if any(keyword in message_text for keyword in DATA_KEYWORDS) else "CHAT"

    return {
        "mode": mode,
        "need": message,
        "entity_name": "",
        "data_domain": "unknown",
        "metric": "",
        "answer_style": "short",
    }


def understand_user_need(message: str) -> dict:
    """Agent 1 : comprendre le besoin, sans toucher au SQL."""
    system_prompt = """
Tu es l'agent de comprehension du projet Football Predictor.
Ton role est de comprendre la demande utilisateur avant toute requete SQL.
Tu ne dois pas repondre a la question, ni inventer de donnees.

Reponds uniquement en JSON avec ces champs:
{
  "mode": "DATA" ou "CHAT",
  "need": "reformulation courte du besoin",
  "entity_name": "nom explicite d'equipe, joueur ou tournoi si present, sinon chaine vide",
  "data_domain": "team|player|match|lineup|custom_team|tournament|unknown",
  "metric": "uefa_rank|overall|price|score|budget|lineup|none",
  "answer_style": "short|list|explain"
}

Regles:
- "meilleure equipe" sans precision = DATA, team, uefa_rank.
- "equipe la mieux notee" = DATA, team, overall.
- "meilleurs joueurs" = DATA, player, overall.
- "joueurs les plus chers" = DATA, player, price.
- "composition", "onze", "lineup" = DATA, lineup, lineup.
- "tournoi", "vainqueur", "score" = DATA, tournament ou match.
- Si c'est une discussion generale sans donnee de base, mode CHAT.
"""

    try:
        response = ask_llm(system_prompt, message, max_tokens=400)
        intent = extract_json_from_llm_response(response)
    except Exception:
        return fallback_intent(message)

    intent["mode"] = str(intent.get("mode", "DATA")).upper()
    intent["need"] = str(intent.get("need") or message)
    intent["entity_name"] = str(intent.get("entity_name") or "")
    intent["data_domain"] = str(intent.get("data_domain") or "unknown")
    intent["metric"] = str(intent.get("metric") or "")
    intent["answer_style"] = str(intent.get("answer_style") or "short")

    if intent["mode"] not in ("DATA", "CHAT"):
        intent["mode"] = fallback_intent(message)["mode"]

    return intent


def intent_to_template_text(message: str, intent: dict) -> str:
    return " ".join(
        [
            message,
            intent.get("need", ""),
            intent.get("entity_name", ""),
            intent.get("data_domain", ""),
            intent.get("metric", ""),
        ]
    )


def build_sql_prompt(message: str, intent: dict, error_context: str = "") -> str:
    template_context = build_template_context(intent_to_template_text(message, intent))

    return f"""
Tu es l'agent SQL PostgreSQL du projet Football Predictor.
Tu dois produire une seule requete SQL de lecture.
Tu n'as pas le droit d'ecrire, modifier, creer ou supprimer des donnees.
Tu ne discutes pas avec l'utilisateur.
Tu dois utiliser uniquement les tables ci-dessous.
Reponds uniquement avec la requete SQL, sans markdown, sans explication.
Ta priorite est d'economiser les tokens: utilise les templates fournis quand ils couvrent le besoin.
Si un template contient une valeur exemple comme '%barcelona%' ou '%jedha%',
remplace-la par `entity_name` quand il est present dans l'intention.
Pour les recherches par nom, conserve la logique LOWER(TRANSLATE(...)) afin de gerer minuscules et accents.
Quand une question demande les meilleurs, plus grands, plus chers ou un classement:
- identifie d'abord la metrique la plus proche dans le schema;
- si elle n'existe pas directement dans la table evidente, cherche si elle peut etre
  calculee par jointure avec les autres tables autorisees;
- privilegie une requete simple et explicable;
- exclus les valeurs NULL pertinentes avec WHERE colonne IS NOT NULL;
- utilise NULLS LAST dans les ORDER BY.

Si la question demande une information qui n'est pas directement stockee,
tu peux construire une approximation raisonnable seulement si le schema permet
clairement de la calculer.
Exemple:
SELECT player_name, overall_rating
FROM player
WHERE overall_rating IS NOT NULL
ORDER BY overall_rating DESC NULLS LAST
LIMIT 10

Intention comprise par l'agent 1:
{json.dumps(intent, ensure_ascii=False)}

{template_context}

{SCHEMA_CONTEXT}

{error_context}
"""


def build_sql(message: str, intent: dict) -> str:
    direct_sql = get_direct_template_sql(intent_to_template_text(message, intent))
    if direct_sql:
        return validate_sql(direct_sql)

    error_context = ""
    sql_model = os.getenv("LLM_SQL_MODEL")

    for _ in range(2):
        llm_response = ask_llm(
            build_sql_prompt(message, intent, error_context),
            intent.get("need", message),
            max_tokens=1100,
            model=sql_model,
        )
        sql = extract_sql_from_llm_response(llm_response)

        try:
            return validate_sql(sql)
        except HTTPException as error:
            error_context = f"""
La requete precedente etait invalide:
{sql}

Erreur:
{error.detail}

Regenere une requete SQL complete et valide.
"""

    raise HTTPException(status_code=422, detail="Impossible de generer un SQL valide")


def answer_simple_chat(message: str, intent: dict) -> str:
    system_prompt = """
Tu es l'assistant conversationnel du projet Football Predictor.
Reponds en francais, simplement et clairement.
Tu peux expliquer le projet, aider a formuler une question data,
ou discuter normalement.
Si l'utilisateur demande une donnee precise de la base, dis-lui que tu vas
interroger la base plutot que d'inventer.
"""

    user_prompt = json.dumps(
        {
            "question": message,
            "intention": intent,
        },
        ensure_ascii=False,
    )

    return ask_llm(system_prompt, user_prompt)


def answer_data_failure(message: str, intent: dict, error_detail) -> str:
    system_prompt = f"""
Tu es l'assistant data du projet Football Predictor.
La question utilisateur semble demander des donnees, mais la requete SQL n'a pas pu etre construite ou executee.
Reponds en francais, simplement, sans inventer de chiffres.
Explique ce qui bloque.
Si la question est trop large ou demande une jointure complexe, dis que cela demande une recherche plus precise dans la base,
puis propose 2 ou 3 formulations de questions plus faciles a requeter.

Schema disponible:
{SCHEMA_CONTEXT}
"""

    user_prompt = json.dumps(
        {
            "question": message,
            "intention": intent,
            "erreur": str(error_detail),
        },
        ensure_ascii=False,
    )

    try:
        return ask_llm(system_prompt, user_prompt)
    except Exception:
        return (
            "Je n'arrive pas a construire une requete fiable pour cette question. "
            "Essaie de preciser la table ou la metrique attendue."
        )


def repair_sql(message: str, intent: dict, sql: str, error: Exception) -> str:
    repair_prompt = f"""
La requete SQL ci-dessous a echoue dans PostgreSQL.
Corrige-la en conservant l'intention de la question.
Reponds uniquement avec une requete SQL SELECT complete, sans markdown.

Question:
{message}

Intention:
{json.dumps(intent, ensure_ascii=False)}

SQL invalide:
{sql}

Erreur PostgreSQL:
{error}

{SCHEMA_CONTEXT}
"""

    llm_response = ask_llm(
        repair_prompt,
        "Corrige la requete SQL.",
        max_tokens=1100,
        model=os.getenv("LLM_SQL_MODEL"),
    )
    repaired_sql = extract_sql_from_llm_response(llm_response)
    return validate_sql(repaired_sql)


def summarize_answer(message: str, intent: dict, sql: str, rows: list[dict]) -> str:
    if not rows:
        return "Je n'ai trouve aucune ligne correspondant a la question."

    system_prompt = """
Tu es l'agent de reponse du projet Football Predictor.
Reponds en francais, simplement, a partir des lignes SQL fournies.
Tu recois l'intention comprise avant la requete, la requete SQL et les lignes retournees.
Si l'utilisateur demande une liste ou un top, cite toutes les lignes recues.
Si la reponse contient beaucoup de lignes, structure en liste claire.
Ne mentionne pas de donnees absentes sauf si cela aide a comprendre une limite.
"""

    user_prompt = json.dumps(
        {
            "question": message,
            "intention": intent,
            "sql": sql,
            "rows": rows[:50],
        },
        ensure_ascii=False,
    )

    try:
        return ask_llm(system_prompt, user_prompt, max_tokens=2200)
    except Exception:
        return f"J'ai trouve {len(rows)} ligne(s). Les resultats sont disponibles dans le tableau."


def chat_with_database(message: str, max_rows: int = 30):
    if not message.strip():
        raise HTTPException(status_code=422, detail="message est obligatoire")

    max_rows = min(max(max_rows, 1), 100)
    intent = understand_user_need(message)

    if intent["mode"] == "CHAT":
        return {
            "answer": answer_simple_chat(message, intent),
            "mode": "chat",
            "intent": intent,
            "sql": None,
            "rows": [],
            "row_count": 0,
        }

    try:
        sql = build_sql(message, intent)
    except HTTPException as error:
        return {
            "answer": answer_data_failure(message, intent, error.detail),
            "mode": "data_error",
            "intent": intent,
            "sql": None,
            "rows": [],
            "row_count": 0,
        }

    try:
        rows = run_readonly_query(sql, max_rows=max_rows)
    except SQLAlchemyError as error:
        try:
            sql = repair_sql(message, intent, sql, error)
            rows = run_readonly_query(sql, max_rows=max_rows)
        except Exception as final_error:
            return {
                "answer": answer_data_failure(message, intent, final_error),
                "mode": "data_error",
                "intent": intent,
                "sql": sql,
                "rows": [],
                "row_count": 0,
            }

    answer = summarize_answer(message, intent, sql, rows)

    return {
        "answer": answer,
        "mode": "data",
        "intent": intent,
        "sql": sql,
        "rows": rows,
        "row_count": len(rows),
    }
