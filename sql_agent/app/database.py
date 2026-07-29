import os
from datetime import date, datetime
from decimal import Decimal

from dotenv import load_dotenv
from sqlalchemy import create_engine, text


load_dotenv()


def get_engine():
    database_url = os.getenv("NEON_DATABASE_URL")

    if not database_url:
        raise RuntimeError("NEON_DATABASE_URL est manquant")

    return create_engine(database_url, pool_pre_ping=True)


def serialize_value(value):
    if isinstance(value, Decimal):
        return float(value)

    if isinstance(value, (date, datetime)):
        return value.isoformat()

    return value


def serialize_rows(rows):
    return [
        {key: serialize_value(value) for key, value in dict(row).items()}
        for row in rows
    ]


def run_readonly_query(sql: str, max_rows: int = 30):
    limited_sql = f"SELECT * FROM ({sql.rstrip(';')}) AS agent_query LIMIT :max_rows"

    with get_engine().begin() as connection:
        # Double securite : meme si un SQL non voulu passe, PostgreSQL refuse l'ecriture.
        connection.execute(text("SET TRANSACTION READ ONLY"))
        connection.execute(text("SET LOCAL statement_timeout = '8000ms'"))
        rows = connection.execute(text(limited_sql), {"max_rows": max_rows}).mappings().all()

    return serialize_rows(rows)
