from pathlib import Path

import pandas as pd
from sqlalchemy import MetaData, Table, create_engine
from sqlalchemy.dialects.postgresql import insert

from create_tables import load_database_url


BASE_DIR = Path(__file__).resolve().parent
BUILD_DIR = BASE_DIR / "build"

TABLE_LOAD_ORDER = [
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

CHUNK_SIZE = 500


def load_table(connection, table_name: str) -> None:
    csv_path = BUILD_DIR / f"{table_name}.csv"
    dataframe = pd.read_csv(csv_path)

    if dataframe.empty:
        print(f"{table_name}: 0 ligne")
        return

    table = Table(table_name, MetaData(), autoload_with=connection)
    table_columns = [column.name for column in table.columns]
    dataframe = dataframe[[column for column in dataframe.columns if column in table_columns]]

    # NaN devient None pour que PostgreSQL recoive de vrais NULL.
    records = dataframe.astype(object).where(pd.notna(dataframe), None).to_dict("records")
    inserted_rows = 0

    for start in range(0, len(records), CHUNK_SIZE):
        chunk = records[start:start + CHUNK_SIZE]
        statement = insert(table).values(chunk).on_conflict_do_nothing()
        result = connection.execute(statement)
        inserted_rows += result.rowcount or 0

    ignored_rows = len(records) - inserted_rows
    print(f"{table_name}: {inserted_rows} inserees, {ignored_rows} deja presentes")


def main() -> None:
    engine = create_engine(load_database_url(), pool_pre_ping=True)

    with engine.begin() as connection:
        for table_name in TABLE_LOAD_ORDER:
            load_table(connection, table_name)


if __name__ == "__main__":
    main()
