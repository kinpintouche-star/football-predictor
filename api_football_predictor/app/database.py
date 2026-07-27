import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

load_dotenv()


def get_database_url() -> str:
    database_url = os.getenv("NEON_DATABASE_URL")

    if not database_url:
        raise RuntimeError("NEON_DATABASE_URL is missing in environment variables")

    return database_url


def get_engine() -> Engine:
    database_url = get_database_url()

    engine = create_engine(
        database_url,
        pool_pre_ping=True,
    )

    return engine


def check_database_connection() -> bool:
    engine = get_engine()

    with engine.connect() as connection:
        result = connection.execute(text("SELECT 1"))

    return result.scalar() == 1