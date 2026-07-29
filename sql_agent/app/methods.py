import json
import re

from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError

from app.database import run_readonly_query
from app.llm import ask_llm
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


def build_sql_prompt(error_context: str = "") -> str:
    return f"""
Tu es un assistant SQL PostgreSQL pour une base de football.
Tu dois produire une seule requete SQL de lecture.
Tu n'as pas le droit d'ecrire, modifier, creer ou supprimer des donnees.
Tu dois utiliser uniquement les tables ci-dessous.
Reponds uniquement avec la requete SQL, sans markdown, sans explication.
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

{SCHEMA_CONTEXT}

{error_context}
"""


def build_sql(question: str) -> str:
    error_context = ""

    for _ in range(2):
        llm_response = ask_llm(build_sql_prompt(error_context), question)
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


def classify_message(message: str) -> str:
    # Petit routeur : on ne lance du SQL que si la question demande les donnees.
    system_prompt = """
Tu classes une question utilisateur pour un assistant football.
Reponds uniquement avec DATA ou CHAT.

DATA = la question demande de lire, comparer, compter, classer ou retrouver des donnees
dans la base football.
CHAT = la question est une discussion simple, une demande d'explication generale,
une demande de formulation ou une question sur le fonctionnement.
"""

    try:
        response = ask_llm(system_prompt, message, max_tokens=20).strip().upper()
    except Exception:
        return "DATA"

    if "CHAT" in response and "DATA" not in response:
        return "CHAT"

    return "DATA"


def answer_simple_chat(message: str) -> str:
    system_prompt = """
Tu es l'assistant conversationnel du projet Football Predictor.
Reponds en francais, simplement et clairement.
Tu peux expliquer le projet, aider a formuler une question data,
ou discuter normalement.
Si l'utilisateur demande une donnee precise de la base, dis-lui que tu vas
interroger la base plutot que d'inventer.
"""

    return ask_llm(system_prompt, message)


def answer_data_failure(message: str, error_detail) -> str:
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


def repair_sql(question: str, sql: str, error: Exception) -> str:
    repair_prompt = f"""
La requete SQL ci-dessous a echoue dans PostgreSQL.
Corrige-la en conservant l'intention de la question.
Reponds uniquement avec une requete SQL SELECT complete, sans markdown.

Question:
{question}

SQL invalide:
{sql}

Erreur PostgreSQL:
{error}

{SCHEMA_CONTEXT}
"""

    llm_response = ask_llm(repair_prompt, "Corrige la requete SQL.")
    repaired_sql = extract_sql_from_llm_response(llm_response)
    return validate_sql(repaired_sql)


def summarize_answer(question: str, sql: str, rows: list[dict]) -> str:
    if not rows:
        return "Je n'ai trouve aucune ligne correspondant a la question."

    system_prompt = """
Tu es un assistant data football.
Reponds en francais, simplement, a partir des lignes SQL fournies.
Si l'utilisateur demande une liste ou un top, cite toutes les lignes recues.
Si la reponse contient beaucoup de lignes, structure en liste claire.
Ne mentionne pas de donnees absentes sauf si cela aide a comprendre une limite.
"""

    user_prompt = json.dumps(
        {
            "question": question,
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

    if classify_message(message) == "CHAT":
        return {
            "answer": answer_simple_chat(message),
            "mode": "chat",
            "sql": None,
            "rows": [],
            "row_count": 0,
        }

    try:
        sql = build_sql(message)
    except HTTPException as error:
        return {
            "answer": answer_data_failure(message, error.detail),
            "mode": "data_error",
            "sql": None,
            "rows": [],
            "row_count": 0,
        }

    try:
        rows = run_readonly_query(sql, max_rows=max_rows)
    except SQLAlchemyError as error:
        try:
            sql = repair_sql(message, sql, error)
            rows = run_readonly_query(sql, max_rows=max_rows)
        except Exception as final_error:
            return {
                "answer": answer_data_failure(message, final_error),
                "mode": "data_error",
                "sql": sql,
                "rows": [],
                "row_count": 0,
            }

    answer = summarize_answer(message, sql, rows)

    return {
        "answer": answer,
        "mode": "data",
        "sql": sql,
        "rows": rows,
        "row_count": len(rows),
    }
