import os
from pathlib import Path

from sqlalchemy import create_engine, text


BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
SQL_PATH = BASE_DIR / "schema.sql"

TABLES = [
    "team",
    "player",
    "match",
    "match_team",
    "lineup",
    "custom_team",
    "custom_team_player",
    "tournament",
    "tournament_team",
    "custom_match",
    "custom_lineup",
]


def load_env_file(path: Path) -> None:
    if not path.exists():
        return

    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()

        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def load_database_url() -> str:
    # On charge le .env racine, puis celui de l'API si besoin.
    load_env_file(PROJECT_ROOT / ".env")
    load_env_file(PROJECT_ROOT / "api_football_predictor" / ".env")

    database_url = os.getenv("NEON_DATABASE_URL")
    if not database_url:
        raise RuntimeError("NEON_DATABASE_URL est manquant")

    return database_url


def main() -> None:
    sql = SQL_PATH.read_text(encoding="utf-8")
    engine = create_engine(load_database_url(), pool_pre_ping=True)

    with engine.begin() as connection:
        connection.exec_driver_sql(sql)
        rows = connection.execute(
            text(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_name = ANY(:table_names)
                ORDER BY table_name
                """
            ),
            {"table_names": TABLES},
        ).scalars().all()

    print("Tables disponibles dans Neon :")
    for table_name in rows:
        print(f"- {table_name}")


if __name__ == "__main__":
    main()
