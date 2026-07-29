-- Schema Neon cible pour l'API data.
-- Ce fichier prepare la structure, mais rien ne l'execute automatiquement.

CREATE TABLE IF NOT EXISTS "team" (
    team_id BIGINT PRIMARY KEY,
    team_name TEXT NOT NULL,
    sofifa_team_id BIGINT,
    club_key TEXT,
    uefa_rank INTEGER,
    club_league_name TEXT,
    overall NUMERIC,
    attack NUMERIC,
    midfield NUMERIC,
    defence NUMERIC,
    build_up_style TEXT,
    defensive_line NUMERIC,
    defensive_approach TEXT
);

CREATE TABLE IF NOT EXISTS "player" (
    player_id BIGINT PRIMARY KEY,
    player_name TEXT NOT NULL,
    full_name TEXT,
    date_of_birth DATE,
    nationality TEXT,
    height_cm INTEGER,
    weight_kg INTEGER,
    best_position TEXT,
    positions TEXT,
    overall_rating NUMERIC,
    potential NUMERIC,
    preferred_foot TEXT,
    weak_foot NUMERIC,
    skill_moves NUMERIC,
    current_sofifa_team_id BIGINT,
    current_club_name TEXT,
    sofifa_value_eur BIGINT,
    transfermarkt_market_value_eur BIGINT,
    has_sofifa_profile INTEGER DEFAULT 1,
    crossing NUMERIC,
    finishing NUMERIC,
    heading_accuracy NUMERIC,
    short_passing NUMERIC,
    volleys NUMERIC,
    dribbling NUMERIC,
    curve NUMERIC,
    fk_accuracy NUMERIC,
    long_passing NUMERIC,
    ball_control NUMERIC,
    acceleration NUMERIC,
    sprint_speed NUMERIC,
    agility NUMERIC,
    reactions NUMERIC,
    balance NUMERIC,
    shot_power NUMERIC,
    jumping NUMERIC,
    stamina NUMERIC,
    strength NUMERIC,
    long_shots NUMERIC,
    aggression NUMERIC,
    interceptions NUMERIC,
    attack_position NUMERIC,
    vision NUMERIC,
    penalties NUMERIC,
    composure NUMERIC,
    defensive_awareness NUMERIC,
    standing_tackle NUMERIC,
    sliding_tackle NUMERIC,
    gk_diving NUMERIC,
    gk_handling NUMERIC,
    gk_kicking NUMERIC,
    gk_positioning NUMERIC,
    gk_reflexes NUMERIC
);

CREATE TABLE IF NOT EXISTS "match" (
    match_id BIGINT PRIMARY KEY,
    match_date DATE,
    home_score INTEGER,
    away_score INTEGER,
    result TEXT
);

CREATE TABLE IF NOT EXISTS "match_team" (
    match_id BIGINT REFERENCES "match"(match_id),
    team_id BIGINT REFERENCES "team"(team_id),
    side TEXT NOT NULL,
    score INTEGER,
    formation TEXT,
    coach_name TEXT,
    sofifa_team_id BIGINT,
    overall NUMERIC,
    attack NUMERIC,
    midfield NUMERIC,
    defence NUMERIC,
    build_up_style TEXT,
    defensive_line NUMERIC,
    defensive_approach TEXT,
    PRIMARY KEY (match_id, team_id)
);

CREATE TABLE IF NOT EXISTS "lineup" (
    match_id BIGINT REFERENCES "match"(match_id),
    team_id BIGINT REFERENCES "team"(team_id),
    player_id BIGINT REFERENCES "player"(player_id),
    position_player TEXT,
    is_starting_match INTEGER,
    minute_start INTEGER,
    minute_end INTEGER,
    minutes_played INTEGER,
    PRIMARY KEY (match_id, team_id, player_id)
);

CREATE TABLE IF NOT EXISTS "custom_team" (
    custom_team_id TEXT PRIMARY KEY CHECK (LEFT(custom_team_id, 1) = 'c'),
    team_name TEXT NOT NULL,
    sofifa_team_id BIGINT,
    club_key TEXT,
    uefa_rank INTEGER,
    club_league_name TEXT,
    overall NUMERIC,
    attack NUMERIC,
    midfield NUMERIC,
    defence NUMERIC,
    build_up_style TEXT,
    defensive_line NUMERIC,
    defensive_approach TEXT,
    reference_formation TEXT,
    budget_eur BIGINT DEFAULT 500000000
);

CREATE TABLE IF NOT EXISTS "custom_team_player" (
    custom_team_id TEXT REFERENCES "custom_team"(custom_team_id),
    player_id BIGINT REFERENCES "player"(player_id),
    PRIMARY KEY (custom_team_id, player_id)
);

CREATE TABLE IF NOT EXISTS "tournament" (
    tournament_id TEXT PRIMARY KEY,
    tournament_name TEXT,
    nb_teams INTEGER NOT NULL,
    winner_team_id TEXT
);

ALTER TABLE "tournament"
ADD COLUMN IF NOT EXISTS tournament_name TEXT;

CREATE TABLE IF NOT EXISTS "tournament_team" (
    tournament_id TEXT REFERENCES "tournament"(tournament_id),
    custom_team_id TEXT,
    slot_index INTEGER,
    nb_wins INTEGER NOT NULL DEFAULT 0,
    nb_loss INTEGER NOT NULL DEFAULT 0,
    nb_equal INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (tournament_id, custom_team_id)
);

CREATE TABLE IF NOT EXISTS "custom_match" (
    custom_match_id TEXT PRIMARY KEY CHECK (LEFT(custom_match_id, 1) = 'c'),
    home_custom_team_id TEXT,
    away_custom_team_id TEXT,
    home_score INTEGER,
    away_score INTEGER,
    result TEXT,
    tournament_phase TEXT,
    tournament_id TEXT REFERENCES "tournament"(tournament_id)
);

ALTER TABLE "custom_match"
ADD COLUMN IF NOT EXISTS home_score INTEGER;

ALTER TABLE "custom_match"
ADD COLUMN IF NOT EXISTS away_score INTEGER;

ALTER TABLE "custom_match"
ADD COLUMN IF NOT EXISTS result TEXT;

CREATE TABLE IF NOT EXISTS "custom_lineup" (
    custom_match_id TEXT REFERENCES "custom_match"(custom_match_id),
    custom_team_id TEXT,
    player_id BIGINT REFERENCES "player"(player_id),
    is_starting_match INTEGER DEFAULT 1,
    PRIMARY KEY (custom_match_id, custom_team_id, player_id)
);

CREATE INDEX IF NOT EXISTS idx_lineup_team_match ON "lineup"(team_id, match_id);
CREATE INDEX IF NOT EXISTS idx_match_team_team ON "match_team"(team_id);
CREATE INDEX IF NOT EXISTS idx_match_date ON "match"(match_date);
CREATE INDEX IF NOT EXISTS idx_custom_team_player_player ON "custom_team_player"(player_id);
CREATE INDEX IF NOT EXISTS idx_tournament_team_team ON "tournament_team"(custom_team_id);
CREATE INDEX IF NOT EXISTS idx_custom_match_tournament ON "custom_match"(tournament_id);
CREATE INDEX IF NOT EXISTS idx_custom_lineup_team ON "custom_lineup"(custom_team_id);
