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

MIGRATIONS = [
    'ALTER TABLE "public"."team" ADD COLUMN IF NOT EXISTS sofifa_team_id BIGINT',
    'ALTER TABLE "public"."team" ADD COLUMN IF NOT EXISTS club_key TEXT',
    'ALTER TABLE "public"."team" ADD COLUMN IF NOT EXISTS uefa_rank INTEGER',
    'ALTER TABLE "public"."team" ADD COLUMN IF NOT EXISTS club_league_name TEXT',
    'ALTER TABLE "public"."team" ADD COLUMN IF NOT EXISTS overall NUMERIC',
    'ALTER TABLE "public"."team" ADD COLUMN IF NOT EXISTS attack NUMERIC',
    'ALTER TABLE "public"."team" ADD COLUMN IF NOT EXISTS midfield NUMERIC',
    'ALTER TABLE "public"."team" ADD COLUMN IF NOT EXISTS defence NUMERIC',
    'ALTER TABLE "public"."team" ADD COLUMN IF NOT EXISTS build_up_style TEXT',
    'ALTER TABLE "public"."team" ADD COLUMN IF NOT EXISTS defensive_line NUMERIC',
    'ALTER TABLE "public"."team" ADD COLUMN IF NOT EXISTS defensive_approach TEXT',
    'ALTER TABLE "public"."player" ADD COLUMN IF NOT EXISTS current_sofifa_team_id BIGINT',
    'ALTER TABLE "public"."player" ADD COLUMN IF NOT EXISTS current_club_name TEXT',
    'ALTER TABLE "public"."player" ADD COLUMN IF NOT EXISTS sofifa_value_eur BIGINT',
    'ALTER TABLE "public"."custom_team" ADD COLUMN IF NOT EXISTS sofifa_team_id BIGINT',
    'ALTER TABLE "public"."custom_team" ADD COLUMN IF NOT EXISTS club_key TEXT',
    'ALTER TABLE "public"."custom_team" ADD COLUMN IF NOT EXISTS uefa_rank INTEGER',
    'ALTER TABLE "public"."custom_team" ADD COLUMN IF NOT EXISTS club_league_name TEXT',
    'ALTER TABLE "public"."custom_team" ADD COLUMN IF NOT EXISTS overall NUMERIC',
    'ALTER TABLE "public"."custom_team" ADD COLUMN IF NOT EXISTS attack NUMERIC',
    'ALTER TABLE "public"."custom_team" ADD COLUMN IF NOT EXISTS midfield NUMERIC',
    'ALTER TABLE "public"."custom_team" ADD COLUMN IF NOT EXISTS defence NUMERIC',
    'ALTER TABLE "public"."custom_team" ADD COLUMN IF NOT EXISTS build_up_style TEXT',
    'ALTER TABLE "public"."custom_team" ADD COLUMN IF NOT EXISTS defensive_line NUMERIC',
    'ALTER TABLE "public"."custom_team" ADD COLUMN IF NOT EXISTS defensive_approach TEXT',
    'ALTER TABLE "public"."custom_team" ADD COLUMN IF NOT EXISTS reference_formation TEXT',
    'ALTER TABLE "public"."custom_team" ADD COLUMN IF NOT EXISTS budget_eur BIGINT DEFAULT 500000000',
    'ALTER TABLE "public"."tournament_team" ADD COLUMN IF NOT EXISTS slot_index INTEGER',
    'ALTER TABLE "public"."custom_match" ADD COLUMN IF NOT EXISTS winner_team_id TEXT',
    'ALTER TABLE "public"."custom_match" ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW()',
    """
    DO $$
    DECLARE constraint_row record;
    BEGIN
        FOR constraint_row IN
            SELECT conrelid::regclass AS table_name, conname
            FROM pg_constraint
            WHERE contype = 'f'
              AND confrelid = '"public"."custom_team"'::regclass
              AND conrelid IN (
                  '"public"."tournament"'::regclass,
                  '"public"."tournament_team"'::regclass,
                  '"public"."custom_match"'::regclass,
                  '"public"."custom_lineup"'::regclass
              )
        LOOP
            EXECUTE format(
                'ALTER TABLE %%s DROP CONSTRAINT IF EXISTS %%I',
                constraint_row.table_name,
                constraint_row.conname
            );
        END LOOP;
    END $$;
    """,
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

        for migration in MIGRATIONS:
            connection.exec_driver_sql(migration)

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
