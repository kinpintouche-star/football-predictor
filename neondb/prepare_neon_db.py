from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
SCHEMA_PATH = BASE_DIR / "schema.sql"


def main() -> None:
    # Dry-run volontaire : on prepare le SQL, mais on ne se connecte jamais a Neon.
    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")

    print("Dry-run Neon DB")
    print("----------------")
    print("Aucune connexion ouverte.")
    print("SQL qui serait execute :")
    print()
    print(schema_sql)


if __name__ == "__main__":
    main()
