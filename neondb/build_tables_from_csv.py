from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
BUILD_DIR = BASE_DIR / "build"

PLAYER_SOURCE = DATA_DIR / "player-data-full-2025-june.csv"
TEAM_MAP_SOURCE = DATA_DIR / "sofifa_team_map.csv"
TEAM_PROFILE_SOURCE = DATA_DIR / "sofifa_team_profiles_enriched.csv"
MATCH_SOURCE = DATA_DIR / "match_outcome_team_ratings.csv"

STAT_COLUMNS = [
    "crossing",
    "finishing",
    "heading_accuracy",
    "short_passing",
    "volleys",
    "dribbling",
    "curve",
    "fk_accuracy",
    "long_passing",
    "ball_control",
    "acceleration",
    "sprint_speed",
    "agility",
    "reactions",
    "balance",
    "shot_power",
    "jumping",
    "stamina",
    "strength",
    "long_shots",
    "aggression",
    "interceptions",
    "attack_position",
    "vision",
    "penalties",
    "composure",
    "defensive_awareness",
    "standing_tackle",
    "sliding_tackle",
    "gk_diving",
    "gk_handling",
    "gk_kicking",
    "gk_positioning",
    "gk_reflexes",
]

PLAYER_NUMERIC_COLUMNS = [
    "player_id",
    "height_cm",
    "weight_kg",
    "overall_rating",
    "potential",
    "weak_foot",
    "skill_moves",
    "current_sofifa_team_id",
    "sofifa_value_eur",
    "transfermarkt_market_value_eur",
    "has_sofifa_profile",
] + STAT_COLUMNS


def clean_numeric_columns(dataframe: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    for column in columns:
        if column in dataframe.columns:
            dataframe[column] = pd.to_numeric(dataframe[column], errors="coerce")

    return dataframe


def euro_to_number(value):
    # Convertit "€115.5M", "€440K" ou vide en nombre brut.
    if pd.isna(value):
        return pd.NA

    text = str(value).replace("€", "").strip()
    if not text:
        return pd.NA

    multiplier = 1
    if text.endswith("M"):
        multiplier = 1_000_000
        text = text[:-1]
    elif text.endswith("K"):
        multiplier = 1_000
        text = text[:-1]

    try:
        return int(float(text) * multiplier)
    except ValueError:
        return pd.NA


def first_position(positions):
    if pd.isna(positions):
        return pd.NA
    return str(positions).split(",")[0].strip()


def build_player_table() -> pd.DataFrame:
    players = pd.read_csv(PLAYER_SOURCE, dtype=str)

    # Le CSV SoFIFA appelle cette colonne "positioning".
    players = players.rename(
        columns={
            "name": "player_name",
            "dob": "date_of_birth",
            "country_name": "nationality",
            "club_id": "current_sofifa_team_id",
            "club_name": "current_club_name",
            "positioning": "attack_position",
        }
    )

    players["best_position"] = players["positions"].apply(first_position)
    players["sofifa_value_eur"] = players["value"].apply(euro_to_number)
    players["transfermarkt_market_value_eur"] = pd.NA
    players["has_sofifa_profile"] = 1

    base_columns = [
        "player_id",
        "player_name",
        "full_name",
        "date_of_birth",
        "nationality",
        "height_cm",
        "weight_kg",
        "best_position",
        "positions",
        "overall_rating",
        "potential",
        "preferred_foot",
        "weak_foot",
        "skill_moves",
        "current_sofifa_team_id",
        "current_club_name",
        "sofifa_value_eur",
        "transfermarkt_market_value_eur",
        "has_sofifa_profile",
    ]

    players = clean_numeric_columns(players, PLAYER_NUMERIC_COLUMNS)

    return players[base_columns + STAT_COLUMNS]


def build_team_table() -> pd.DataFrame:
    matches = pd.read_csv(MATCH_SOURCE)
    profiles = pd.read_csv(TEAM_PROFILE_SOURCE)
    team_map = pd.read_csv(TEAM_MAP_SOURCE)

    home = matches[
        ["home_team_id", "home_sofifa_id", "home_sofifa_team_name"]
    ].rename(
        columns={
            "home_team_id": "team_id",
            "home_sofifa_id": "sofifa_team_id",
            "home_sofifa_team_name": "team_name",
        }
    )
    away = matches[
        ["away_team_id", "away_sofifa_id", "away_sofifa_team_name"]
    ].rename(
        columns={
            "away_team_id": "team_id",
            "away_sofifa_id": "sofifa_team_id",
            "away_sofifa_team_name": "team_name",
        }
    )

    teams = pd.concat([home, away], ignore_index=True).drop_duplicates("team_id")

    profile_columns = [
        "sofifa_team_id",
        "club_league_name",
        "overall",
        "attack",
        "midfield",
        "defence",
        "build_up_style",
        "defensive_line",
        "defensive_approach",
    ]
    rank_columns = ["sofifa_team_id", "club_key", "rank"]

    teams = teams.merge(profiles[profile_columns], on="sofifa_team_id", how="left")
    teams = teams.merge(team_map[rank_columns], on="sofifa_team_id", how="left")
    teams = teams.rename(columns={"rank": "uefa_rank"})
    teams = clean_numeric_columns(
        teams,
        [
            "team_id",
            "sofifa_team_id",
            "uefa_rank",
            "overall",
            "attack",
            "midfield",
            "defence",
            "defensive_line",
        ],
    )

    return teams[
        [
            "team_id",
            "team_name",
            "sofifa_team_id",
            "club_key",
            "uefa_rank",
            "club_league_name",
            "overall",
            "attack",
            "midfield",
            "defence",
            "build_up_style",
            "defensive_line",
            "defensive_approach",
        ]
    ]


def build_match_table() -> pd.DataFrame:
    matches = pd.read_csv(MATCH_SOURCE)
    matches = clean_numeric_columns(
        matches,
        ["match_id", "home_score", "away_score"],
    )

    return matches[
        ["match_id", "match_date", "home_score", "away_score", "result"]
    ].drop_duplicates("match_id")


def build_match_team_table() -> pd.DataFrame:
    matches = pd.read_csv(MATCH_SOURCE)
    matches = clean_numeric_columns(
        matches,
        [
            "match_id",
            "home_team_id",
            "away_team_id",
            "home_score",
            "away_score",
            "home_sofifa_id",
            "away_sofifa_id",
            "home_overall",
            "away_overall",
            "home_attack",
            "away_attack",
            "home_midfield",
            "away_midfield",
            "home_defence",
            "away_defence",
            "home_defensive_line",
            "away_defensive_line",
        ],
    )

    home = pd.DataFrame(
        {
            "match_id": matches["match_id"],
            "team_id": matches["home_team_id"],
            "side": "home",
            "score": matches["home_score"],
            "formation": pd.NA,
            "coach_name": pd.NA,
            "sofifa_team_id": matches["home_sofifa_id"],
            "overall": matches["home_overall"],
            "attack": matches["home_attack"],
            "midfield": matches["home_midfield"],
            "defence": matches["home_defence"],
            "build_up_style": matches["home_build_up_style"],
            "defensive_line": matches["home_defensive_line"],
            "defensive_approach": matches["home_defensive_approach"],
        }
    )

    away = pd.DataFrame(
        {
            "match_id": matches["match_id"],
            "team_id": matches["away_team_id"],
            "side": "away",
            "score": matches["away_score"],
            "formation": pd.NA,
            "coach_name": pd.NA,
            "sofifa_team_id": matches["away_sofifa_id"],
            "overall": matches["away_overall"],
            "attack": matches["away_attack"],
            "midfield": matches["away_midfield"],
            "defence": matches["away_defence"],
            "build_up_style": matches["away_build_up_style"],
            "defensive_line": matches["away_defensive_line"],
            "defensive_approach": matches["away_defensive_approach"],
        }
    )

    return pd.concat([home, away], ignore_index=True)


def build_empty_lineup_table() -> pd.DataFrame:
    # Aucun CSV de compositions n'est present dans ce dossier pour le moment.
    # On cree seulement le fichier vide avec les bonnes colonnes.
    return pd.DataFrame(
        columns=[
            "match_id",
            "team_id",
            "player_id",
            "position_player",
            "is_starting_match",
            "minute_start",
            "minute_end",
            "minutes_played",
        ]
    )


def build_empty_custom_team_table() -> pd.DataFrame:
    # Les ids custom commencent par "c" pour les distinguer des ids source.
    return pd.DataFrame(
        columns=[
            "custom_team_id",
            "team_name",
            "sofifa_team_id",
            "club_key",
            "uefa_rank",
            "club_league_name",
            "overall",
            "attack",
            "midfield",
            "defence",
            "build_up_style",
            "defensive_line",
            "defensive_approach",
            "reference_formation",
            "budget_eur",
        ]
    )


def build_empty_tournament_table() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "tournament_id",
            "nb_teams",
            "winner_team_id",
        ]
    )


def build_empty_custom_team_player_table() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "custom_team_id",
            "player_id",
        ]
    )


def build_empty_custom_match_table() -> pd.DataFrame:
    # Les ids de match custom commencent aussi par "c".
    return pd.DataFrame(
        columns=[
            "custom_match_id",
            "home_custom_team_id",
            "away_custom_team_id",
            "tournament_phase",
            "tournament_id",
        ]
    )


def save_table(name: str, dataframe: pd.DataFrame) -> None:
    output_path = BUILD_DIR / f"{name}.csv"
    dataframe.to_csv(output_path, index=False)
    print(f"{name}: {len(dataframe)} lignes -> {output_path}")


def main() -> None:
    BUILD_DIR.mkdir(exist_ok=True)

    save_table("player", build_player_table())
    save_table("team", build_team_table())
    save_table("match", build_match_table())
    save_table("match_team", build_match_team_table())
    save_table("lineup", build_empty_lineup_table())
    save_table("custom_team", build_empty_custom_team_table())
    save_table("custom_team_player", build_empty_custom_team_player_table())
    save_table("tournament", build_empty_tournament_table())
    save_table("custom_match", build_empty_custom_match_table())


if __name__ == "__main__":
    main()
